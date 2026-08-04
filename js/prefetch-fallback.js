// Hover-intent prefetch fallback for browsers without the Speculation Rules API.
// Injects <link rel="prefetch"> for same-origin links on first mouseenter, with dedupe.
(function () {
  if (HTMLScriptElement.supports && HTMLScriptElement.supports('speculationrules')) return;
  var seen = {};
  document.addEventListener('mouseenter', function (e) {
    var a = e.target instanceof Element ? e.target.closest('a[href]') : null;
    if (!a) return;
    var url;
    try { url = new URL(a.href, location.href); } catch (err) { return; }
    if (url.origin !== location.origin || seen[url.href]) return;
    if (/\.(webp|avif|jpg|png|mp4|woff2|css|js)(\?|$)/.test(url.pathname)) return;
    seen[url.href] = true;
    var link = document.createElement('link');
    link.rel = 'prefetch';
    link.href = url.href;
    document.head.appendChild(link);
  }, true);
})();
