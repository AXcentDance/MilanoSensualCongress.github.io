/* Homepage interactions respect motion and visibility preferences. */
(() => {
  const body = document.body;
  if (!body.classList.contains('home-premiere')) return;
  const preference = matchMedia('(prefers-reduced-motion: reduce)');
  let paused = false;
  try { paused = sessionStorage.getItem('msc-motion-paused') === 'true'; } catch (_) { /* Storage is optional. */ }
  let ready = false;
  let bellAnimation = null;
  const canMove = () => ready && !preference.matches && !paused && !document.hidden && !navigator.connection?.saveData;
  function resetActions() {
    bellAnimation?.cancel();
    bellAnimation = null;
  }
  function update() {
    const active = ready && !preference.matches && !navigator.connection?.saveData;
    body.classList.toggle('e27-motion-on', active);
    body.classList.toggle('e27-motion-paused', paused || document.hidden);
    if (!canMove()) resetActions();
  }
  const preferencesChanged = update;
  preference.addEventListener('change', preferencesChanged);
  navigator.connection?.addEventListener?.('change', preferencesChanged);
  document.addEventListener('visibilitychange', update);
  window.addEventListener('pageshow', () => {
    // A cached page may return after the preference changed on another page.
    resetActions();
    try { paused = sessionStorage.getItem('msc-motion-paused') === 'true'; } catch (_) { /* Storage is optional. */ }
    update();
  });
  update();
  window.addEventListener('blur', resetActions);

  const reminderButton = document.querySelector('.premiere-submit');
  function ringBell(strength = 1) {
    if (!canMove() || reminderButton?.disabled) return;
    const icon = reminderButton?.querySelector('.premiere-submit-icon');
    if (!icon?.animate) return;
    bellAnimation?.cancel();
    bellAnimation = icon.animate([0, -24, 22, -18, 15, -10, 7, -3, 0].map(angle => ({
      transform: `rotate(${angle * strength}deg)`
    })), { duration: strength > 1 ? 780 : 650, easing: 'ease-in-out' });
  }
  reminderButton?.addEventListener('pointerenter', event => { if (event.pointerType === 'mouse') ringBell(); });
  reminderButton?.addEventListener('focus', () => { if (reminderButton.matches(':focus-visible')) ringBell(.8); });
  reminderButton?.addEventListener('click', () => ringBell(1.4));
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
    document.querySelectorAll('[data-motion], .e27-experience-card, .e27-journal-item, .experience-artist-card, .editorial-story, .visit-help-card').forEach(element => {
      // Initial viewport content is never moved while the page settles.
      if (element.getBoundingClientRect().top > innerHeight) observer.observe(element);
    });
  };
  if (document.readyState === 'complete') start();
  else window.addEventListener('load', start, { once: true });
})();
