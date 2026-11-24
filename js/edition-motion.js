/* Optional movement. Content is visible and usable before this script runs. */
(() => {
  const body = document.body;
  const button = document.querySelector('.e27-motion-toggle');
  if (!button) return;
  const preference = matchMedia('(prefers-reduced-motion: reduce)');
  const italian = document.documentElement.lang === 'it';
  let paused = false;
  try { paused = sessionStorage.getItem('msc-motion-paused') === 'true'; } catch (_) { /* Storage is optional. */ }
  let ready = false;
  function update() {
    const active = ready && !preference.matches && !navigator.connection?.saveData;
    body.classList.toggle('e27-motion-on', active);
    body.classList.toggle('e27-motion-paused', paused || document.hidden);
    button.hidden = !active;
    button.textContent = paused ? (italian ? '▶ Animazioni' : '▶ Motion') : (italian ? 'Ⅱ Animazioni' : 'Ⅱ Motion');
    button.setAttribute('aria-label', paused ? (italian ? 'Riprendi animazioni' : 'Resume motion') : (italian ? 'Metti in pausa le animazioni' : 'Pause motion'));
    button.setAttribute('aria-pressed', String(paused));
  }
  button.addEventListener('click', () => {
    paused = !paused;
    try { sessionStorage.setItem('msc-motion-paused', String(paused)); } catch (_) { /* Storage is optional. */ }
    update();
  });
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
    const chapters = [...document.querySelectorAll('main > section')].filter(section => section.querySelector('h2'));
    if (chapters.length > 2) {
      const guide = document.createElement('nav');
      guide.className = 'scene-progress';
      guide.setAttribute('aria-label', italian ? 'Esplora questa pagina' : 'Explore this page');
      const links = new Map();
      chapters.forEach((section, index) => {
        if (!section.id) section.id = 'chapter-' + (index + 1);
        const title = section.dataset.chapter || section.querySelector('h2').innerText.replace(/\s+/g, ' ').trim();
        const link = document.createElement('a');
        link.href = '#' + section.id;
        link.setAttribute('aria-label', title);
        const label = document.createElement('span');
        label.textContent = title;
        link.append(label);
        guide.append(link);
        links.set(section, link);
      });
      body.append(guide);
      const chapterObserver = new IntersectionObserver(entries => {
        for (const entry of entries) {
          if (!entry.isIntersecting) continue;
          links.forEach(link => link.removeAttribute('aria-current'));
          links.get(entry.target).setAttribute('aria-current', 'location');
        }
      }, { rootMargin: '-15% 0px -55% 0px' });
      chapters.forEach(section => chapterObserver.observe(section));
    }
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
