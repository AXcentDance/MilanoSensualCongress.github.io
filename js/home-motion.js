/* Brief homepage entrances, respecting saved and system motion preferences. */
(() => {
  const body = document.body;
  if (!body.classList.contains('home-premiere')) return;
  const preference = matchMedia('(prefers-reduced-motion: reduce)');
  let paused = false;
  try { paused = sessionStorage.getItem('msc-motion-paused') === 'true'; } catch (_) { /* Storage is optional. */ }
  let ready = false;
  function update() {
    const active = ready && !preference.matches && !navigator.connection?.saveData;
    body.classList.toggle('e27-motion-on', active);
    body.classList.toggle('e27-motion-paused', paused || document.hidden);
  }
  preference.addEventListener('change', update);
  document.addEventListener('visibilitychange', update);
  window.addEventListener('pageshow', () => {
    // A cached page may return after the preference changed on another page.
    try { paused = sessionStorage.getItem('msc-motion-paused') === 'true'; } catch (_) { /* Storage is optional. */ }
    update();
  });
  const start = () => {
    ready = true;
    update();
    if (!('IntersectionObserver' in window)) return;
    const observer = new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        if (!preference.matches && !paused) entry.target.classList.add('e27-in-view');
        observer.unobserve(entry.target);
      }
    }, { threshold: .12 });
    document.querySelectorAll('[data-motion], .e27-artist, .e27-experience-card, .e27-journal-item, .experience-artist-card, .editorial-story, .visit-help-card').forEach(element => {
      // Initial viewport content is never moved while the page settles.
      if (element.getBoundingClientRect().top > innerHeight) observer.observe(element);
    });
  };
  if (document.readyState === 'complete') start();
  else window.addEventListener('load', start, { once: true });
})();
