// Progressive MP4 quality is chosen once, after the poster and page have loaded.
(function () {
  var video = document.getElementById('heroVideo');
  if (!video) return;
  var motion = window.matchMedia('(prefers-reduced-motion: reduce)');
  var connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
  var loaded = document.readyState === 'complete';
  var bounds = video.getBoundingClientRect();
  var visible = bounds.bottom > 0 && bounds.top < window.innerHeight;

  function slowConnection() {
    return connection && (connection.saveData ||
      /^(slow-2g|2g)$/.test(connection.effectiveType || '') ||
      (connection.downlink > 0 && connection.downlink < 0.4));
  }

  function allowed() {
    return loaded && visible && !document.hidden && !motion.matches && !slowConnection();
  }

  function source() {
    var rate = connection && connection.downlink;
    if (connection && (connection.effectiveType === '3g' || (rate > 0 && rate < 1.5))) {
      return video.getAttribute('data-src-economy');
    }
    if (window.innerWidth <= 1000 || (rate > 0 && rate < 4)) {
      return video.getAttribute('data-src-mobile');
    }
    return video.getAttribute('data-src');
  }

  function update() {
    if (!allowed()) {
      video.pause();
      return;
    }
    // Keep the chosen clip when conditions change: no restart or second download.
    if (!video.getAttribute('src')) video.src = source();
    if (video.paused) {
      var play = video.play();
      if (play && play.catch) play.catch(function () { /* poster remains available */ });
    }
  }

  if ('IntersectionObserver' in window) {
    new IntersectionObserver(function (entries) {
      visible = entries[0].isIntersecting;
      update();
    }).observe(video);
  }
  video.addEventListener('canplay', update);
  document.addEventListener('visibilitychange', update);
  if (motion.addEventListener) motion.addEventListener('change', update);
  else if (motion.addListener) motion.addListener(update);
  if (connection && connection.addEventListener) connection.addEventListener('change', update);
  if (!loaded) window.addEventListener('load', function () { loaded = true; update(); }, { once: true });
  update();
})();
