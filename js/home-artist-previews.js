/* Homepage-only muted previews: desktop hover and explicit phone play buttons. */
(() => {
  const cards = [...document.querySelectorAll('.home-premiere #artist-showcase [data-artist-video]')];
  if (!cards.length) return;
  const hover = matchMedia('(hover: hover) and (pointer: fine)');
  const phone = matchMedia('(max-width: 600px)');
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const playerOrigin = 'https://www.youtube-nocookie.com';
  const italian = document.documentElement.lang === 'it';
  let pending = null;
  let active = null;

  const allowed = (manual = false) => !document.hidden && !document.body.classList.contains('e27-motion-paused') &&
    (manual ? phone.matches : !phone.matches && hover.matches && !reduced.matches && !navigator.connection?.saveData);

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
    clearInterval(previous.handshake);
    previous.card.classList.remove('e27-preview-loading', 'e27-preview-playing');
    updateButton(previous.card, false);
    if (previous.abort) {
      previous.abort.abort();
      previous.frame.pause();
      previous.frame.removeAttribute('src');
      previous.frame.load();
      if (previous.objectURL) URL.revokeObjectURL(previous.objectURL);
    }
    previous.frame.remove(); // Destroy the player so it cannot keep buffering offscreen.
  }

  function visible(card) {
    const rect = card.querySelector('.e27-artist-photo').getBoundingClientRect();
    return rect.bottom > 0 && rect.top < innerHeight && rect.right > 0 && rect.left < innerWidth;
  }

  function post(payload) {
    active?.frame.contentWindow?.postMessage(JSON.stringify(payload), playerOrigin);
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

  async function streamFragments(video, session, playlistURL, fail) {
    // This adapter reads our small, unencrypted VOD fMP4 playlists. Native HLS
    // handles them on Safari; other browsers need only MediaSource, not a player library.
    const type = 'video/mp4; codecs="avc1.640028"';
    if (!window.MediaSource?.isTypeSupported(type)) throw new Error('Preview format unsupported');
    const signal = session.abort.signal;
    const localURL = path => {
      const url = new URL(path, playlistURL);
      if (url.origin !== location.origin) throw new Error('Preview must be local');
      return url.href;
    };
    const request = async url => {
      const response = await fetch(url, { signal });
      if (!response.ok) throw new Error('Preview unavailable');
      return response;
    };
    const playlist = await (await request(playlistURL)).text();
    const lines = playlist.trim().split(/\r?\n/).map(line => line.trim());
    const init = lines.find(line => line.startsWith('#EXT-X-MAP:'))?.match(/URI="([^"]+)"/)?.[1];
    const segments = lines.filter(line => line && !line.startsWith('#')).map(localURL);
    const duration = lines.filter(line => line.startsWith('#EXTINF:'))
      .reduce((total, line) => total + parseFloat(line.slice(8)), 0);
    if (lines[0] !== '#EXTM3U' || !lines.includes('#EXT-X-ENDLIST') || !init ||
      !segments.length || !Number.isFinite(duration) || duration <= 0) throw new Error('Invalid preview playlist');
    if (signal.aborted) return;

    const source = new MediaSource();
    session.objectURL = URL.createObjectURL(source);
    await waitFor(source, 'sourceopen', signal, () => {
      video.src = session.objectURL;
      video.load();
    });
    source.duration = duration;
    const buffer = source.addSourceBuffer(type);
    const append = async url => {
      const bytes = await (await request(url)).arrayBuffer();
      await waitFor(buffer, 'updateend', signal, () => buffer.appendBuffer(bytes));
    };
    await append(localURL(init));
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
        // Fetch one fragment at a time, only when fewer than four seconds remain.
        // Keep this short clip buffered so looping needs no further requests.
        while (next < segments.length && !signal.aborted && bufferedAhead() < 4) {
          await append(segments[next++]);
          if (next === 1) {
            // H.264 frame reordering can put the first timestamp just above zero.
            if (video.buffered.length && video.currentTime < video.buffered.start(0)) {
              video.currentTime = video.buffered.start(0);
            }
            video.play().catch(fail);
          }
        }
        if (next === segments.length && source.readyState === 'open') source.endOfStream();
      } catch (_) { fail(); }
      finally { filling = false; }
    };
    for (const event of ['timeupdate', 'seeking', 'waiting']) video.addEventListener(event, fill, { signal });
    await fill();
  }

  function startLocal(card, manual) {
    const video = document.createElement('video');
    video.className = 'e27-artist-preview';
    video.title = `${card.dataset.artistName} — ${italian ? 'anteprima senza audio' : 'muted dance preview'}`;
    video.muted = video.defaultMuted = video.autoplay = video.loop = video.playsInline = true;
    video.setAttribute('playsinline', '');
    video.preload = 'none';
    video.tabIndex = -1;
    video.setAttribute('aria-hidden', 'true');
    const session = { card, frame: video, manual, abort: new AbortController() };
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
    card.querySelector('.e27-artist-photo').append(video);
    try {
      const url = new URL(card.dataset.artistPreview, location.href);
      if (url.origin !== location.origin) throw new Error('Preview must be local');
      if (video.canPlayType('application/vnd.apple.mpegurl')) {
        video.src = url.href;
        video.play().catch(fail);
      } else streamFragments(video, session, url.href, fail).catch(fail);
    } catch (_) { fail(); }
  }

  function start(card, manual = false) {
    pending = null;
    if (!allowed(manual) || (!manual && !card.matches(':hover'))) return;
    // An explicit phone press must never reposition the page, even when only
    // the name and play button remain visible below a scrolled-away photo.
    if (!manual && !visible(card)) return;
    if (card.dataset.artistPreview) {
      stop();
      startLocal(card, manual);
      return;
    }
    const id = card.dataset.artistVideo;
    if (!/^[a-zA-Z0-9_-]{11}$/.test(id)) return;
    stop();
    const frame = document.createElement('iframe');
    const params = new URLSearchParams({ autoplay: '1', mute: '1', controls: '0', playsinline: '1',
      rel: '0', loop: '1', playlist: id, disablekb: '1', enablejsapi: '1', origin: location.origin });
    frame.className = 'e27-artist-preview';
    frame.src = `${playerOrigin}/embed/${id}?${params}`;
    frame.title = `${card.dataset.artistName} — ${italian ? 'anteprima senza audio' : 'muted dance preview'}`;
    frame.allow = 'autoplay; encrypted-media';
    frame.tabIndex = -1;
    frame.setAttribute('aria-hidden', 'true');
    frame.referrerPolicy = 'strict-origin-when-cross-origin';
    active = { card, frame, manual, subscribed: false };
    card.classList.add('e27-preview-loading');
    updateButton(card, true, true);
    // The portrait stays visible until the player reports real playback. If an
    // embed is blocked, unavailable or too slow, the artist portrait remains.
    active.timeout = setTimeout(stop, 12000);
    frame.addEventListener('error', () => { if (active?.frame === frame) stop(); }, { once: true });
    frame.addEventListener('load', () => {
      if (active?.frame !== frame) return;
      const listen = () => post({ event: 'listening', id: `artist-preview-${id}` });
      listen();
      active.handshake = setInterval(listen, 250);
    }, { once: true });
    card.querySelector('.e27-artist-photo').append(frame);
  }

  window.addEventListener('message', event => {
    if (!active || event.origin !== playerOrigin || event.source !== active.frame.contentWindow) return;
    let message;
    try { message = typeof event.data === 'string' ? JSON.parse(event.data) : event.data; } catch (_) { return; }
    if (!message || typeof message !== 'object') return;
    if (!active.subscribed && ['onReady', 'initialDelivery', 'infoDelivery'].includes(message.event)) {
      active.subscribed = true;
      for (const name of ['onStateChange', 'onError', 'onAutoplayBlocked']) post({ event: 'command', func: 'addEventListener', args: [name] });
      post({ event: 'command', func: 'mute', args: [] });
      post({ event: 'command', func: 'playVideo', args: [] });
    }
    if (message.event === 'onError' || message.event === 'onAutoplayBlocked') return stop();
    const state = message.event === 'onStateChange' ? message.info : message.info?.playerState;
    if (state === 1) {
      clearTimeout(active.timeout);
      clearInterval(active.handshake);
      active.card.classList.remove('e27-preview-loading');
      active.card.classList.add('e27-preview-playing');
      updateButton(active.card, true);
    }
  });

  cards.forEach(card => {
    const button = card.querySelector('.e27-artist-play');
    if (button) {
      updateButton(card, false);
      button.disabled = false;
      button.hidden = false;
      button.addEventListener('click', () => {
        if (!phone.matches) return;
        if (active?.manual && active.card === card) stop();
        else start(card, true);
      });
    }
    card.addEventListener('pointerenter', event => {
      if (event.pointerType !== 'mouse' || !allowed()) return;
      stop();
      pending = setTimeout(() => start(card), 220);
    });
    card.addEventListener('pointerleave', () => {
      if (!active?.manual) stop();
    });
  });
  const tapHint = document.querySelector('.home-premiere .e27-preview-hint-tap');
  if (tapHint) tapHint.hidden = false;
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
