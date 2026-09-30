/* Progressive enhancement: local cinema hero and click-to-watch artist links. */
(() => {
  const film = document.getElementById('heroVideo');
  const ambient = document.getElementById('heroAmbientVideo');
  const hero = film?.closest('.premiere-hero');
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  let filmVisible = false;
  let introComplete = false;
  let ambientReady = false;
  let ambientFailed = false;
  const pendingPlays = new WeakMap();
  const motionPaused = () => document.body.classList.contains('e27-motion-paused');
  const connectionTooSlow = () => {
    const connection = navigator.connection;
    return connection?.saveData || ['slow-2g', '2g'].includes(connection?.effectiveType) ||
      (connection?.downlink > 0 && connection.downlink < .4);
  };
  const playbackAllowed = () => filmVisible && !document.hidden && !reducedMotion.matches &&
    !connectionTooSlow() && !motionPaused() && !document.getElementById('artist-player')?.open;
  const currentFilm = () => introComplete && ambient ? ambient : film;
  function updateTitle() {
    hero?.classList.toggle('premiere-title-revealed', film.classList.contains('has-played') && film.currentTime >= 5.8);
  }
  function pauseFilms() {
    for (const video of [film, ambient]) {
      if (!video) continue;
      pendingPlays.delete(video);
      video.pause();
    }
  }
  function attachSource(video) {
    if (!video || video.getAttribute('src')) return;
    const connection = navigator.connection;
    const downlink = connection?.downlink;
    // These are progressive MP4s. Select once before fetching, so resizing or
    // a fluctuating connection never restarts the opening or downloads it twice.
    // Safari/Firefox can omit Network Information: use the viewport fallback.
    const economy = connection?.effectiveType === '3g' || (downlink > 0 && downlink < 1.5);
    const compact = matchMedia('(max-width: 1000px)').matches || (downlink > 0 && downlink < 4);
    const source = (economy && video.dataset.srcEconomy) ||
      (compact && video.dataset.srcMobile) || video.dataset.src;
    if (source) video.src = source;
  }
  function prepareAmbient() {
    if (!ambient || ambientFailed || ambient.getAttribute('src') || !playbackAllowed()) return;
    // Warm the second clip during the intro, never before motion is permitted.
    ambient.preload = 'auto';
    attachSource(ambient);
    ambient.load();
  }
  function playFilm() {
    if (!film || !playbackAllowed()) return;
    if (introComplete) {
      if (!ambient || ambientFailed) return;
      prepareAmbient();
      if (!ambientReady) return;
    } else {
      if (film.ended) return;
      if (!film.getAttribute('src')) {
        film.poster = document.querySelector('.premiere-poster-image')?.currentSrc || film.dataset.poster;
        attachSource(film);
      }
    }
    const video = currentFilm();
    if (!video.paused || pendingPlays.has(video)) return;
    const request = {};
    pendingPlays.set(video, request);
    video.play().then(() => {
      // A play promise can resolve after a scroll, preference change or modal.
      if (!playbackAllowed() || video !== currentFilm()) video.pause();
    }).catch(() => {}).finally(() => {
      if (pendingPlays.get(video) === request) pendingPlays.delete(video);
    });
  }
  function syncFilm() {
    if (!film) return;
    if (!playbackAllowed()) pauseFilms();
    else {
      if (!introComplete && film.currentTime >= 3.8) prepareAmbient();
      playFilm();
    }
  }
  if (film) {
    film.addEventListener('playing', () => {
      if (!playbackAllowed() || introComplete) { film.pause(); return; }
      film.classList.add('has-played');
      updateTitle();
    });
    film.addEventListener('timeupdate', () => {
      updateTitle();
      if (film.currentTime >= 3.8) prepareAmbient();
    });
    film.addEventListener('ended', () => {
      introComplete = true;
      updateTitle();
      syncFilm();
    });
    film.addEventListener('error', () => { film.classList.remove('has-played'); updateTitle(); });
    if (ambient) {
      ambient.loop = true;
      ambient.addEventListener('loadedmetadata', () => {
        const offset = Number(ambient.dataset.startTime);
        const start = Number.isFinite(offset) && offset > 0 ? Math.min(offset, Math.max(0, ambient.duration - .05)) : 0;
        const ready = () => { ambientReady = true; if (introComplete) syncFilm(); };
        if (start > 0) {
          ambient.addEventListener('seeked', ready, { once: true });
          ambient.currentTime = start;
        } else ready();
      });
      ambient.addEventListener('playing', () => {
        if (!playbackAllowed() || !introComplete) { ambient.pause(); return; }
        // Keep the finished intro underneath until the matching ambient frame is ready.
        ambient.classList.add('has-played');
      });
      ambient.addEventListener('error', () => {
        ambientFailed = true;
        ambient.classList.remove('has-played');
        ambient.pause();
      });
    }
    updateTitle();
    const startWhenVisible = () => {
      film.poster = document.querySelector('.premiere-poster-image')?.currentSrc || film.dataset.poster;
      if ('IntersectionObserver' in window) {
        const observer = new IntersectionObserver(entries => {
          filmVisible = entries.some(entry => entry.isIntersecting);
          syncFilm();
        }, { threshold: .05 });
        observer.observe(film);
      } else { filmVisible = true; syncFilm(); }
    };
    if (document.readyState === 'complete') startWhenVisible();
    else window.addEventListener('load', startWhenVisible, { once: true });
    reducedMotion.addEventListener('change', syncFilm);
    navigator.connection?.addEventListener?.('change', syncFilm);
    document.addEventListener('visibilitychange', syncFilm);
    window.addEventListener('pagehide', pauseFilms);
    window.addEventListener('pageshow', syncFilm);
    new MutationObserver(syncFilm).observe(document.body, { attributes:true, attributeFilter:['class'] });
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
    pauseFilms();
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
    syncFilm();
  });
})();
