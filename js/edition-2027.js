/* Progressive enhancement: the artist cards remain direct video links without JS. */
(() => {
  const film = document.getElementById('heroVideo');
  const filmToggle = document.querySelector('.e27-video-toggle');
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  let manuallyPaused = false;
  function updateFilmControl() {
    if (!filmToggle || !film) return;
    filmToggle.textContent = film.paused ? filmToggle.dataset.play : filmToggle.dataset.pause;
  }
  function playFilm() {
    if (!film || document.getElementById('artist-player')?.open) return;
    if (!film.poster) film.poster = film.dataset.poster;
    if (!film.getAttribute('src')) film.src = film.dataset.src;
    film.play().catch(updateFilmControl);
  }
  if (film) {
    film.addEventListener('play', () => {
      if (document.getElementById('artist-player')?.open) film.pause();
      updateFilmControl();
    });
    film.addEventListener('pause', updateFilmControl);
    updateFilmControl();
    const startWhenVisible = () => {
      const observer = new IntersectionObserver(entries => {
        if (entries.some(entry => entry.isIntersecting)) {
          film.poster = film.dataset.poster;
          if (!manuallyPaused && !reducedMotion.matches && !navigator.connection?.saveData) playFilm();
          observer.disconnect();
        }
      }, { rootMargin: '100px' });
      observer.observe(film);
    };
    if (document.readyState === 'complete') startWhenVisible();
    else window.addEventListener('load', startWhenVisible, { once: true });
    filmToggle?.addEventListener('click', () => {
      manuallyPaused = !film.paused;
      if (film.paused) playFilm();
      else film.pause();
    });
    reducedMotion.addEventListener('change', event => { if (event.matches) film.pause(); });
  }

  const dialog = document.getElementById('artist-player');
  if (!dialog || typeof dialog.showModal !== 'function') return;
  const cards = [...document.querySelectorAll('[data-artist-video]')];
  const holder = document.getElementById('artist-video-frame');
  const heading = document.getElementById('artist-player-title');
  const external = document.getElementById('artist-youtube-link');
  const counter = document.getElementById('artist-player-count');
  const close = dialog.querySelector('.e27-player-close');
  let selected = 0;
  let opener = null;
  let resumeFilm = false;
  function showArtist(index) {
    selected = (index + cards.length) % cards.length;
    const card = cards[selected];
    const id = card.dataset.artistVideo;
    if (!/^[a-zA-Z0-9_-]{11}$/.test(id)) return;
    heading.textContent = card.dataset.artistName;
    external.href = card.href;
    counter.textContent = `${String(selected + 1).padStart(2, '0')} / ${String(cards.length).padStart(2, '0')}`;
    const iframe = document.createElement('iframe');
    iframe.src = `https://www.youtube-nocookie.com/embed/${id}?autoplay=1&rel=0&playsinline=1`;
    iframe.title = `${card.dataset.artistName} — Bachata`;
    iframe.allow = 'autoplay; encrypted-media; picture-in-picture; fullscreen';
    iframe.allowFullscreen = true;
    iframe.referrerPolicy = 'strict-origin-when-cross-origin';
    holder.replaceChildren(iframe);
  }
  cards.forEach((card, index) => card.addEventListener('click', event => {
    if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    opener = card;
    resumeFilm = !!film && !film.paused;
    film?.pause();
    showArtist(index);
    dialog.showModal();
    document.body.classList.add('e27-dialog-open');
    close.focus();
  }));
  close.addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', event => {
    if (event.target !== dialog) return;
    const rect = dialog.getBoundingClientRect();
    if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) dialog.close();
  });
  dialog.querySelectorAll('[data-artist-step]').forEach(button => {
    button.addEventListener('click', () => showArtist(selected + Number(button.dataset.artistStep)));
  });
  dialog.addEventListener('close', () => {
    holder.replaceChildren(); // Removing the frame stops playback and network activity.
    document.body.classList.remove('e27-dialog-open');
    opener?.focus({ preventScroll: true });
    if (resumeFilm && !manuallyPaused && !reducedMotion.matches) playFilm();
  });
})();
