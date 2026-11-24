/* Shared silent previews: picture hover, phone play, or artist-page controls. */
(() => {
  const cards = [...document.querySelectorAll('[data-artist-preview]')];
  if (!cards.length) return;
  const hover = matchMedia('(hover: hover) and (pointer: fine)');
  const phone = matchMedia('(max-width: 600px)');
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const italian = document.documentElement.lang === 'it';
  const codec = 'video/mp4; codecs="avc1.640028"';
  let pending = null;
  let active = null;

  const allowed = (manual = false, card = active?.card) => !document.hidden && !document.body.classList.contains('e27-motion-paused') &&
    (manual ? phone.matches || card?.dataset.previewControls === 'always' : hover.matches && !reduced.matches &&
      !navigator.connection?.saveData && !['slow-2g', '2g'].includes(navigator.connection?.effectiveType));

  function updateButton(card, playing, loading = false) {
    const button = card.querySelector('.e27-artist-play');
    if (!button) return;
    button.setAttribute('aria-pressed', String(playing));
    button.setAttribute('aria-busy', String(loading));
    button.setAttribute('aria-label', playing ? button.dataset.stopLabel : button.dataset.playLabel);
  }

  function stop() {
    clearTimeout(pending);
    pending = null;
    if (!active) return;
    const previous = active;
    active = null;
    clearTimeout(previous.timeout);
    previous.abort.abort();
    previous.card.classList.remove('e27-preview-loading', 'e27-preview-playing');
    updateButton(previous.card, false);
    previous.video.pause();
    previous.video.removeAttribute('src');
    previous.video.load();
    if (previous.objectURL) URL.revokeObjectURL(previous.objectURL);
    previous.video.remove();
  }

  function visible(card) {
    const rect = card.querySelector('.e27-artist-photo').getBoundingClientRect();
    return rect.bottom > 0 && rect.top < innerHeight && rect.right > 0 && rect.left < innerWidth;
  }

  function waitFor(target, event, signal, action) {
    return new Promise((resolve, reject) => {
      const finish = error => {
        target.removeEventListener(event, done);
        target.removeEventListener('error', failed);
        signal.removeEventListener('abort', aborted);
        if (error) reject(error);
        else resolve();
      };
      const done = () => finish();
      const failed = () => finish(new Error('Preview media failed'));
      const aborted = () => finish(new DOMException('Preview stopped', 'AbortError'));
      if (signal.aborted) return aborted();
      target.addEventListener(event, done);
      target.addEventListener('error', failed);
      signal.addEventListener('abort', aborted, { once: true });
      try { action?.(); } catch (error) { finish(error); }
    });
  }

  function localURL(path, base) {
    const url = new URL(path, base);
    if (url.origin !== location.origin) throw new Error('Preview must be local');
    return url.href;
  }

  async function request(session, url) {
    const response = await fetch(url, { signal: session.abort.signal });
    if (!response.ok) throw new Error('Preview unavailable');
    return response;
  }

  async function readMaster(session, url) {
    const text = await (await request(session, url)).text();
    const lines = text.trim().split(/\r?\n/).map(line => line.trim());
    if (lines[0] !== '#EXTM3U') throw new Error('Invalid preview master');
    const levels = [];
    for (let i = 0; i < lines.length - 1; i++) {
      if (!lines[i].startsWith('#EXT-X-STREAM-INF:')) continue;
      const bandwidth = Number(lines[i].match(/(?:[:,])BANDWIDTH=(\d+)/)?.[1]);
      const width = Number(lines[i].match(/RESOLUTION=(\d+)x\d+/)?.[1]);
      if (!bandwidth || !width || !lines[i + 1] || lines[i + 1].startsWith('#')) throw new Error('Invalid preview quality');
      levels.push({ bandwidth, width, url: localURL(lines[++i], url) });
    }
    if (!levels.length) throw new Error('No preview qualities');
    return levels.sort((a, b) => a.width - b.width);
  }

  function chooseLevel(session, levels) {
    const pixels = session.card.querySelector('.e27-artist-photo').getBoundingClientRect().width * Math.min(devicePixelRatio || 1, 2);
    const target = levels.find(level => level.width >= pixels) || levels.at(-1);
    const connection = navigator.connection;
    let budget = Number.isFinite(connection?.downlink) && connection.downlink > 0 ? connection.downlink * 650000 : Infinity;
    if (connection?.saveData || ['slow-2g', '2g'].includes(connection?.effectiveType)) budget = levels[0].bandwidth;
    else if (connection?.effectiveType === '3g') budget = Math.min(budget, 350000);
    if (session.throughput) budget = Math.min(budget, session.throughput * .7);
    return levels.filter(level => level.width <= target.width && level.bandwidth <= budget).at(-1) || levels[0];
  }

  async function streamFragments(session, playlistURL, fail) {
    const { video } = session;
    const signal = session.abort.signal;
    const levels = await readMaster(session, playlistURL);
    const playlists = new Map();
    const readLevel = async level => {
      if (playlists.has(level.url)) return playlists.get(level.url);
      const text = await (await request(session, level.url)).text();
      const lines = text.trim().split(/\r?\n/).map(line => line.trim());
      const init = lines.find(line => line.startsWith('#EXT-X-MAP:'))?.match(/URI="([^"]+)"/)?.[1];
      const segments = lines.filter(line => line && !line.startsWith('#')).map(path => localURL(path, level.url));
      const duration = lines.filter(line => line.startsWith('#EXTINF:')).reduce((total, line) => total + parseFloat(line.slice(8)), 0);
      if (lines[0] !== '#EXTM3U' || !lines.includes('#EXT-X-ENDLIST') || !init || !segments.length ||
          !Number.isFinite(duration) || duration <= 0 || duration > 15.05 || segments.length > 8 ||
          lines.some(line => line.startsWith('#EXT-X-KEY:'))) {
        throw new Error('Invalid preview playlist');
      }
      const result = { init: localURL(init, level.url), segments, duration };
      playlists.set(level.url, result);
      return result;
    };
    const initialPlaylist = await readLevel(chooseLevel(session, levels));
    const segmentCount = initialPlaylist.segments.length;
    const source = new MediaSource();
    session.objectURL = URL.createObjectURL(source);
    await waitFor(source, 'sourceopen', signal, () => {
      video.src = session.objectURL;
      video.load();
    });
    source.duration = initialPlaylist.duration;
    const buffer = source.addSourceBuffer(codec);
    const append = async bytes => waitFor(buffer, 'updateend', signal, () => buffer.appendBuffer(bytes));
    let current = null;
    let next = 0;
    let filling = false;
    const bufferedAhead = () => {
      for (let i = 0; i < video.buffered.length; i++) {
        if (video.buffered.start(i) <= video.currentTime && video.buffered.end(i) > video.currentTime) {
          return video.buffered.end(i) - video.currentTime;
        }
      }
      return 0;
    };
    const fill = async () => {
      if (filling || signal.aborted) return;
      filling = true;
      try {
        // Load independent two-second pieces; keep roughly four seconds ahead.
        // Aligned keyframes let a slow connection switch quality at a boundary.
        while (next < segmentCount && !signal.aborted && bufferedAhead() < 4) {
          const level = chooseLevel(session, levels);
          const playlist = await readLevel(level);
          if (playlist.segments.length !== segmentCount || Math.abs(playlist.duration - initialPlaylist.duration) > .05) {
            throw new Error('Unaligned preview variants');
          }
          if (current !== level) {
            await append(await (await request(session, playlist.init)).arrayBuffer());
            current = level;
          }
          const began = performance.now();
          const bytes = await (await request(session, playlist.segments[next])).arrayBuffer();
          const elapsed = Math.max(performance.now() - began, 1);
          const throughput = bytes.byteLength * 8000 / elapsed;
          session.throughput = session.throughput ? session.throughput * .6 + throughput * .4 : throughput;
          await append(bytes);
          next++;
          if (next === 1) {
            if (video.buffered.length && video.currentTime < video.buffered.start(0)) video.currentTime = video.buffered.start(0);
            video.play().catch(fail);
          }
        }
        if (next === segmentCount && source.readyState === 'open') source.endOfStream();
      } catch (_) { fail(); }
      finally { filling = false; }
    };
    for (const event of ['timeupdate', 'seeking', 'waiting']) video.addEventListener(event, fill, { signal });
    await fill();
  }

  function start(card, manual = false) {
    pending = null;
    const picture = card.querySelector('.e27-artist-photo');
    if (!allowed(manual, card) || (!manual && (!picture.matches(':hover') || !visible(card)))) return;
    stop();
    const video = document.createElement('video');
    video.className = 'e27-artist-preview';
    video.title = `${card.dataset.artistName} — ${italian ? 'anteprima senza audio' : 'muted dance preview'}`;
    video.muted = video.defaultMuted = video.autoplay = video.loop = video.playsInline = true;
    video.setAttribute('playsinline', '');
    video.preload = 'none';
    video.tabIndex = -1;
    video.setAttribute('aria-hidden', 'true');
    const session = { card, video, manual, abort: new AbortController() };
    const signal = session.abort.signal;
    const fail = () => { if (active === session) stop(); };
    active = session;
    card.classList.add('e27-preview-loading');
    updateButton(card, true, true);
    session.timeout = setTimeout(fail, 12000);
    video.addEventListener('error', fail, { signal });
    video.addEventListener('waiting', () => {
      clearTimeout(session.timeout);
      session.timeout = setTimeout(fail, 12000);
    }, { signal });
    video.addEventListener('playing', () => {
      clearTimeout(session.timeout);
      card.classList.remove('e27-preview-loading');
      card.classList.add('e27-preview-playing');
      updateButton(card, true);
    }, { signal });
    picture.append(video);
    try {
      const url = localURL(card.dataset.artistPreview, location.href);
      if (window.MediaSource?.isTypeSupported(codec)) streamFragments(session, url, fail).catch(fail);
      else {
        const nativeHLS = video.canPlayType('application/vnd.apple.mpegurl');
        readMaster(session, url).then(levels => {
          if (signal.aborted) return;
          const level = chooseLevel(session, levels);
          const limited = navigator.connection?.saveData || ['slow-2g', '2g'].includes(navigator.connection?.effectiveType);
          video.src = nativeHLS ? (limited ? level.url : url) : localURL('preview.mp4', level.url);
          video.play().catch(fail);
        }).catch(fail);
      }
    } catch (_) { fail(); }
  }

  cards.forEach(card => {
    const button = card.querySelector('.e27-artist-play');
    if (button) {
      updateButton(card, false);
      button.disabled = false;
      button.hidden = false;
      button.addEventListener('click', () => {
        if (!allowed(true, card)) return;
        if (active?.card === card) stop();
        else start(card, true);
      });
    }
    const picture = card.querySelector('.e27-artist-photo');
    picture.addEventListener('pointerenter', event => {
      if (event.pointerType !== 'mouse' || !allowed() || active?.card === card) return;
      stop();
      pending = setTimeout(() => start(card), 220);
    });
    picture.addEventListener('pointerleave', () => { if (!active?.manual) stop(); });
  });
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver(entries => {
      if (active && entries.some(entry => entry.target === active.card && !entry.isIntersecting)) stop();
    });
    cards.forEach(card => observer.observe(card));
  }
  const stopIfDisabled = () => { if (!allowed(active?.manual)) stop(); };
  reduced.addEventListener('change', stopIfDisabled);
  hover.addEventListener('change', stopIfDisabled);
  phone.addEventListener('change', stop);
  navigator.connection?.addEventListener?.('change', stopIfDisabled);
  document.addEventListener('visibilitychange', stop);
  window.addEventListener('pagehide', stop);
  new MutationObserver(stopIfDisabled).observe(document.body, { attributes: true, attributeFilter: ['class'] });
})();
