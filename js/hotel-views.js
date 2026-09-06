/* Progressive enhancement: native radios select the same views without JS. */
(() => {
  const root = document.querySelector('[data-hotel-switcher]');
  if (!root) return;
  const choices = [...root.querySelectorAll('input[name="hotel-view"]')];
  const panels = [...root.querySelectorAll('.hotel-views > .hotel-view')];
  const languageLinks = [...document.querySelectorAll('[data-hotel-language]')];
  const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
  let active = 0;
  let animations = [];
  let generation = 0;

  function show(index, { animate = false, updateURL = false, scroll = false } = {}) {
    if (!choices[index] || !panels[index]) return;
    const previous = active;
    const token = ++generation;
    animations.forEach(animation => animation.cancel());
    animations = [];
    panels.forEach(panel => delete panel.dataset.leaving);
    choices[index].checked = true;
    active = index;
    root.dataset.activeHotel = choices[index].value;

    if (previous !== index && panels[previous].contains(document.activeElement)) {
      choices[index].focus({ preventScroll: true });
    }
    panels.forEach((panel, position) => {
      panel.inert = position !== index;
      panel.setAttribute('aria-hidden', String(position !== index));
    });
    for (const link of languageLinks) {
      link.href = link.dataset.hotelLanguage + (index === 1 ? '#as-hotel-cambiago' : '');
    }
    if (updateURL) {
      history.pushState(null, '', index === 1 ? '#as-hotel-cambiago' : '#event-hotel');
    }
    if (scroll) window.scrollTo({ top: 0, behavior: 'instant' });

    if (animate && previous !== index && !reducedMotion.matches && panels[index].animate) {
      const direction = index > previous ? 1 : -1;
      const outgoing = panels[previous];
      outgoing.dataset.leaving = '';
      const timing = { duration: 360, easing: 'cubic-bezier(.22,.68,0,1)' };
      animations = [
        outgoing.animate([{ transform: 'translateX(0)' }, { transform: `translateX(${-direction * 100}%)` }], timing),
        panels[index].animate([{ transform: `translateX(${direction * 100}%)` }, { transform: 'translateX(0)' }], timing),
      ];
      Promise.all(animations.map(animation => animation.finished.catch(() => {}))).then(() => {
        if (generation !== token) return;
        delete outgoing.dataset.leaving;
        animations = [];
      });
    }
  }

  function fromHash() {
    // View hashes differ from panel IDs so a hotel link opens at the top,
    // without the browser scrolling to an anchor during initial rendering.
    const destination = document.getElementById(location.hash.slice(1));
    const secondHotel = location.hash === '#as-hotel-cambiago' || destination?.closest('.hotel-view') === panels[1];
    const index = secondHotel ? 1 : 0;
    show(index);
  }

  choices.forEach((choice, index) => choice.addEventListener('change', () => {
    if (choice.checked && active !== index) show(index, { animate: true, updateURL: true, scroll: true });
  }));
  window.addEventListener('hashchange', fromHash);
  window.addEventListener('pageshow', fromHash);

  function enableSwipe(surface, onSelector = false) {
    let start = null;
    surface.addEventListener('touchstart', event => {
      start = null;
      if (event.touches.length !== 1) return;
      if (!onSelector && event.target.closest('a, button, input, select, textarea, label, summary, #carousel')) return;
      const touch = event.touches[0];
      // Leave browser edge navigation and normal vertical scrolling alone.
      if (touch.clientX < 24 || touch.clientX > innerWidth - 24) return;
      start = { x: touch.clientX, y: touch.clientY, scrollY: window.scrollY };
    }, { passive: true });
    surface.addEventListener('touchcancel', () => { start = null; }, { passive: true });
    surface.addEventListener('touchend', event => {
      if (!start || event.changedTouches.length !== 1) return;
      const touch = event.changedTouches[0];
      const dx = touch.clientX - start.x, dy = touch.clientY - start.y;
      const scrolled = Math.abs(window.scrollY - start.scrollY);
      start = null;
      if (Math.abs(dx) < 60 || Math.abs(dx) < Math.abs(dy) * 1.5 || scrolled > 24) return;
      const step = onSelector ? (dx > 0 ? 1 : -1) : (dx < 0 ? 1 : -1);
      const next = active + step;
      if (next < 0 || next >= panels.length) return;
      if (onSelector && event.cancelable) event.preventDefault();
      choices[next].focus({ preventScroll: true });
      show(next, { animate: true, updateURL: true, scroll: true });
    }, { passive: !onSelector });
  }
  enableSwipe(root.querySelector('.hotel-views'));
  enableSwipe(root.querySelector('.hotel-switch-track'), true);
  fromHash();
})();
