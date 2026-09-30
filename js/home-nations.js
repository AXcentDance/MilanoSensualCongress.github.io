/* A progressively enhanced, self-hosted flag atlas. No tracking or map service. */
(() => {
  'use strict';
  const section = document.getElementById('home-nations');
  if (!section) return;
  const selectedFlag = section.querySelector('.nations-selected-flag img');
  const loadFlag = flag => {
    flag.src = flag.dataset.nationsFlagSrc;
  };
  // Both the current country and scrollable picker load flags when in view.
  const flags = section.querySelectorAll('[data-nations-flag-src]');
  if ('IntersectionObserver' in window) {
    const flagObserver = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        loadFlag(entry.target);
        flagObserver.unobserve(entry.target);
      });
    }, { rootMargin: '0px' });
    flags.forEach(flag => flagObserver.observe(flag));
  } else flags.forEach(loadFlag);
  const atlases = [...section.querySelectorAll('img[data-nations-map-src]')];
  const loadAtlas = atlas => { atlas.src = atlas.dataset.nationsMapSrc; };
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (!entry.isIntersecting || !entry.boundingClientRect.width || !entry.boundingClientRect.height) return;
        loadAtlas(entry.target);
        observer.unobserve(entry.target);
      });
    }, { rootMargin: '0px' });
    // Keep the atlas out of the opening film's network budget even when a
    // compact country panel brings the map close to the tablet viewport. The
    // hidden phone/desktop counterpart never receives an image source.
    atlases.forEach(atlas => observer.observe(atlas));
  } else {
    const pendingAtlases = new Set(atlases);
    const loadVisibleAtlases = () => {
      pendingAtlases.forEach(atlas => {
        const rect = atlas.getBoundingClientRect();
        if (!rect.width || !rect.height || rect.bottom <= 0 || rect.top >= innerHeight) return;
        loadAtlas(atlas);
        pendingAtlases.delete(atlas);
      });
      if (!pendingAtlases.size) {
        window.removeEventListener('scroll', loadVisibleAtlases);
        window.removeEventListener('resize', loadVisibleAtlases);
      }
    };
    window.addEventListener('scroll', loadVisibleAtlases, { passive: true });
    window.addEventListener('resize', loadVisibleAtlases);
    loadVisibleAtlases();
  }
  const list = section.querySelector('.nations-list');
  const buttons = Array.from(list.querySelectorAll('[data-country]'));
  const tools = section.querySelector('.nations-tools');
  const search = section.querySelector('input[type="search"]');
  const results = section.querySelector('.nations-result');
  const empty = section.querySelector('.nations-empty');
  const passport = section.querySelector('.nations-passport');
  const route = section.querySelector('.nations-route-active');
  const origin = section.querySelector('.nations-origin');
  const destination = section.querySelector('.nations-milano');
  const dancersStat = section.querySelector('[data-nations-stat="dancers"]');
  const artistsStat = section.querySelector('[data-nations-stat="artists"]');
  const numberFormat = new Intl.NumberFormat(document.documentElement.lang || 'en', {
    maximumSignificantDigits: 15, useGrouping: false,
  });
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const normalize = value => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase().trim();
  const terms = new Map(buttons.map(button => [button, normalize(button.dataset.search)]));
  let selected = null;
  let animationFrame = null;
  let currentRoute = null;
  let targetRoute = null;

  function renderRoute(geometry) {
    currentRoute = geometry;
    const { x, y, controlX, controlY, mx, my } = geometry;
    route.setAttribute('d', `M${x},${y} Q${controlX},${controlY} ${mx},${my}`);
    origin.setAttribute('cx', String(x));
    origin.setAttribute('cy', String(y));
  }

  function cancelRouteAnimation() {
    if (animationFrame !== null) cancelAnimationFrame(animationFrame);
    animationFrame = null;
  }

  function moveRoute(geometry, animate) {
    cancelRouteAnimation();
    targetRoute = geometry;
    if (!currentRoute || !animate || reduceMotion.matches) {
      renderRoute(geometry);
      return;
    }
    // Restart from the visible curve when another flag is selected mid-flight.
    // Interpolate its origin and bend together, keeping Milano anchored.
    const previous = currentRoute;
    const startedAt = performance.now();
    const frame = timestamp => {
      const progress = Math.max(0, Math.min(1, (timestamp - startedAt) / 650));
      if (progress >= 1) {
        animationFrame = null;
        renderRoute(geometry);
        return;
      }
      const eased = 1 - Math.pow(1 - progress, 3);
      const next = { ...geometry };
      for (const key of ['x', 'y', 'controlX', 'controlY']) {
        next[key] = previous[key] + (geometry[key] - previous[key]) * eased;
      }
      renderRoute(next);
      animationFrame = requestAnimationFrame(frame);
    };
    animationFrame = requestAnimationFrame(frame);
  }

  function formatStatistic(raw, percent) {
    const value = raw === undefined || raw.trim() === '' ? null : Number(raw);
    const known = value !== null && Number.isFinite(value) && value >= 0 &&
      (percent ? value <= 100 : Number.isInteger(value));
    return known
      ? numberFormat.format(value) + (percent ? '%' : '')
      : null;
  }

  function showStatistic(element, raw, percent) {
    const text = formatStatistic(raw, percent);
    element.dataset.pending = String(text === null);
    element.textContent = text ?? section.dataset.statPending;
  }

  function preparePocketMap() {
    const pocket = section.querySelector('.nations-mobile');
    if (!pocket) return;
    const phone = matchMedia('(max-width: 600px)');
    let initialized = false;
    let observer = null;
    const stopWatching = () => {
      observer?.disconnect();
      window.removeEventListener('scroll', checkPosition);
      window.removeEventListener('resize', checkPosition);
    };
    const initialize = () => {
      if (initialized || !phone.matches) return;
      initialized = true;
      stopWatching();
      phone.removeEventListener('change', watch);
      enhancePocketMap();
    };
    const checkPosition = () => {
      if (!phone.matches) return;
      const rect = pocket.getBoundingClientRect();
      if (rect.width && rect.height && rect.bottom > -120 && rect.top < innerHeight + 120) initialize();
    };
    const watch = () => {
      stopWatching();
      if (initialized || !phone.matches) return;
      if ('IntersectionObserver' in window) {
        observer ??= new IntersectionObserver(entries => {
          if (entries.some(entry => entry.isIntersecting)) initialize();
        }, { rootMargin: '120px 0px' });
        observer.observe(pocket);
      } else {
        window.addEventListener('scroll', checkPosition, { passive: true });
        window.addEventListener('resize', checkPosition);
        checkPosition();
      }
    };
    // Keep the static pins until the phone map approaches view. Building its
    // collision layout and observing its size should not compete with the hero.
    phone.addEventListener('change', watch);
    watch();
  }

  function enhancePocketMap() {
    const pocket = section.querySelector('.nations-mobile');
    if (!pocket) return;
    const view = pocket.querySelector('.nations-pocket-view');
    const base = pocket.querySelector('.nations-pocket-base');
    const leaders = pocket.querySelector('.nations-pocket-leaders');
    const pocketRoute = pocket.querySelector('.nations-pocket-route');
    const milano = pocket.querySelector('.nations-pocket-destination');
    const picker = pocket.querySelector('.nations-pocket-select');
    const status = pocket.querySelector('.nations-pocket-status');
    const pins = [...pocket.querySelectorAll('[data-mobile-country]')];
    const countries = new Map(buttons.map(button => [button.dataset.country, button]));
    const leaderGroups = new Map([...leaders.querySelectorAll('[data-mobile-leader]')]
      .map(group => [group.dataset.mobileLeader, group]));
    const phone = matchMedia('(max-width: 600px)');
    const initialCrop = { x: 125, y: 165, width: 395, height: 365 };
    const featured = ['IT', 'CH', 'DE', 'FR', 'ES', 'GB', 'PL', 'RO', 'SE', 'PT'];
    const anchors = { PT: [164, 361], ES: [212, 427], FR: [260, 326], GB: [250, 259],
      CH: [288, 388], DE: [378, 293], PL: [450, 297], RO: [473, 390], SE: [392, 210], IT: [374, 468] };
    const destinationPoint = { x: Number(destination.getAttribute('cx')), y: Number(destination.getAttribute('cy')) };
    const clamp = (value, min, max) => Math.max(min, Math.min(max, value));
    const contains = (crop, point) => point && point.x >= crop.x && point.x <= crop.x + crop.width &&
      point.y >= crop.y && point.y <= crop.y + crop.height;
    const mapPoint = button => {
      if (!button || button.dataset.mapApproximate === 'true' ||
        !button.dataset.mapX?.trim() || !button.dataset.mapY?.trim()) return null;
      const x = Number(button.dataset.mapX);
      const y = Number(button.dataset.mapY);
      return Number.isFinite(x) && Number.isFinite(y) && x >= 0 && x <= 800 && y >= 0 && y <= 620
        ? { x, y } : null;
    };
    const svgElement = (name, className) => {
      const element = document.createElementNS('http://www.w3.org/2000/svg', name);
      element.setAttribute('class', className);
      return element;
    };
    let chosen = countries.has('IT') ? 'IT' : buttons[0].dataset.country;
    let crop = { ...initialCrop };
    let pocketFrame = null;

    function drawLeader(code, center, point, scaleX, scaleY) {
      let group = leaderGroups.get(code);
      if (!group) {
        group = svgElement('g', '');
        group.dataset.mobileLeader = code;
        group.append(svgElement('line', 'nations-pocket-leader'), svgElement('circle', 'nations-pocket-dot'));
        leaders.append(group);
        leaderGroups.set(code, group);
      }
      group.removeAttribute('hidden');
      const line = group.querySelector('line');
      const dot = group.querySelector('circle');
      // Connect the label edge to its real representative point, even when the
      // label had to move to avoid a neighbour or the Milano destination.
      const px = (point.x - crop.x) * scaleX;
      const py = (point.y - crop.y) * scaleY;
      line.setAttribute('x1', String(clamp(px, center.x - 26, center.x + 26) / scaleX));
      line.setAttribute('y1', String(clamp(py, center.y - 22, center.y + 22) / scaleY));
      line.setAttribute('x2', String(point.x - crop.x));
      line.setAttribute('y2', String(point.y - crop.y));
      dot.setAttribute('cx', String(point.x - crop.x));
      dot.setAttribute('cy', String(point.y - crop.y));
      dot.setAttribute('r', code === chosen ? '3' : '2.3');
      group.dataset.selected = String(code === chosen);
    }

    function renderPocket() {
      if (!phone.matches) return;
      const width = view.clientWidth;
      const height = view.clientHeight;
      if (!width || !height) return;
      const selectedCountry = countries.get(chosen);
      const point = mapPoint(selectedCountry);
      if (point) {
        crop = contains(initialCrop, point) ? { ...initialCrop } : {
          ...initialCrop,
          x: clamp(point.x - initialCrop.width / 2, 0, 800 - initialCrop.width),
          y: clamp(point.y - initialCrop.height / 2, 0, 620 - initialCrop.height),
        };
      }
      base.style.width = `${800 / crop.width * 100}%`;
      base.style.height = `${620 / crop.height * 100}%`;
      base.style.left = `${-crop.x / crop.width * 100}%`;
      base.style.top = `${-crop.y / crop.height * 100}%`;
      view.dataset.cropX = String(crop.x);
      view.dataset.cropY = String(crop.y);
      const scaleX = width / crop.width;
      const scaleY = height / crop.height;
      const mx = destinationPoint.x - crop.x;
      const my = destinationPoint.y - crop.y;
      milano.setAttribute('transform', `translate(${mx} ${my})`);
      milano.toggleAttribute('hidden', !contains(crop, destinationPoint));
      pocketRoute.toggleAttribute('hidden', !point);
      if (point) {
        const bend = Math.max(28, Math.hypot(destinationPoint.x - point.x, destinationPoint.y - point.y) * .32);
        const controlX = (point.x + destinationPoint.x) / 2 - bend - crop.x;
        const controlY = Math.min(point.y, destinationPoint.y) - bend - crop.y;
        pocketRoute.setAttribute('d', `M${point.x - crop.x},${point.y - crop.y} Q${controlX},${controlY} ${mx},${my}`);
      } else pocketRoute.removeAttribute('d');

      const percentage = formatStatistic(selectedCountry.dataset.dancerPercent, true);
      const name = selectedCountry.dataset.countryName;
      const template = point ? pocket.dataset.mobileStatusTemplate : pocket.dataset.mobileOutsideTemplate;
      status.textContent = (template || '{country}: {percent}')
        .replace('{country}', name).replace('{percent}', percentage ?? section.dataset.statPending);
      picker.value = chosen;
      const pinByCode = new Map(pins.map(pin => [pin.dataset.mobileCountry, pin]));
      const visiblePins = new Set();
      pins.forEach(pin => {
        const country = countries.get(pin.dataset.mobileCountry);
        const text = formatStatistic(country.dataset.dancerPercent, true);
        pin.setAttribute('aria-pressed', String(pin.dataset.mobileCountry === chosen));
        pin.setAttribute('aria-label', (pocket.dataset.mobileStatusTemplate || '{country}: {percent}')
          .replace('{country}', country.dataset.countryName).replace('{percent}', text ?? section.dataset.statPending));
        pin.querySelector('strong').textContent = text ?? '—';
        pin.dataset.pending = String(text === null);
      });
      leaderGroups.forEach(group => group.setAttribute('hidden', ''));
      const nearby = [...countries.keys()].filter(code => contains(crop, mapPoint(countries.get(code))))
        .sort((a, b) => {
          const pa = mapPoint(countries.get(a));
          const pb = mapPoint(countries.get(b));
          const center = point || { x: crop.x + crop.width / 2, y: crop.y + crop.height / 2 };
          return Math.hypot(pa.x - center.x, pa.y - center.y) - Math.hypot(pb.x - center.x, pb.y - center.y);
        });
      const candidates = [...new Set([chosen, ...featured, ...nearby])]
        .filter(code => pinByCode.has(code) && contains(crop, mapPoint(countries.get(code)))).slice(0, 10);
      const occupied = contains(crop, destinationPoint)
        ? [{ left: mx * scaleX - 28, right: mx * scaleX + 28, top: my * scaleY - 30, bottom: my * scaleY + 12 }]
        : [];
      const place = anchor => {
        if (width < 60 || height < 52) return null;
        for (let radius = 0; radius <= Math.max(width, height); radius += 12) {
          const steps = radius ? 16 : 1;
          for (let i = 0; i < steps; i++) {
            const angle = i * Math.PI * 2 / steps;
            const x = clamp(anchor.x + Math.cos(angle) * radius, 30, width - 30);
            const y = clamp(anchor.y + Math.sin(angle) * radius, 26, height - 26);
            const rect = { left: x - 26, right: x + 26, top: y - 22, bottom: y + 22 };
            const overlaps = occupied.some(other => rect.left < other.right + 4 && rect.right > other.left - 4 &&
              rect.top < other.bottom + 4 && rect.bottom > other.top - 4);
            if (!overlaps) { occupied.push(rect); return { x, y }; }
          }
        }
        return null;
      };
      candidates.forEach(code => {
        const countryPoint = mapPoint(countries.get(code));
        const anchor = anchors[code];
        const center = place(anchor
          ? { x: (anchor[0] - crop.x) * scaleX, y: (anchor[1] - crop.y) * scaleY }
          : { x: (countryPoint.x - crop.x) * scaleX, y: (countryPoint.y - crop.y) * scaleY - 34 });
        if (!center) return;
        const pin = pinByCode.get(code);
        pin.style.left = `${center.x / width * 100}%`;
        pin.style.top = `${center.y / height * 100}%`;
        visiblePins.add(pin);
        drawLeader(code, center, countryPoint, scaleX, scaleY);
      });
      // Apply final visibility once so an activated pin never briefly becomes
      // hidden and loses keyboard focus during its own selection update.
      pins.forEach(pin => { pin.hidden = !visiblePins.has(pin); });
    }

    const schedulePocket = () => {
      if (!phone.matches || pocketFrame !== null) return;
      pocketFrame = requestAnimationFrame(() => { pocketFrame = null; renderPocket(); });
    };
    const choose = code => {
      if (!countries.has(code)) return;
      chosen = code;
      renderPocket();
    };
    pocket.addEventListener('click', event => {
      const pin = event.target.closest('[data-mobile-country]');
      if (pin) choose(pin.dataset.mobileCountry);
    });
    picker.addEventListener('change', () => choose(picker.value));
    pins.forEach(pin => { pin.disabled = false; });
    picker.disabled = false;
    const resize = 'ResizeObserver' in window ? new ResizeObserver(schedulePocket) : null;
    const watchPocket = () => {
      if (phone.matches) {
        resize?.observe(view);
        schedulePocket();
      } else {
        resize?.disconnect();
        if (pocketFrame !== null) cancelAnimationFrame(pocketFrame);
        pocketFrame = null;
      }
    };
    phone.addEventListener('change', watchPocket);
    if (!resize) window.addEventListener('resize', schedulePocket);
    watchPocket();
  }

  function filter() {
    const query = normalize(search.value);
    let count = 0;
    buttons.forEach(button => {
      const matches = !query || terms.get(button).includes(query);
      button.parentElement.hidden = !matches;
      if (matches) count += 1;
    });
    empty.hidden = count !== 0;
    results.textContent = query
      ? (count === 1 ? section.dataset.resultSingular : section.dataset.resultTemplate.replace('{n}', String(count)))
      : '';
    list.scrollTop = 0;
  }

  function select(button, animate = true) {
    if (button === selected) return;
    if (selected) selected.setAttribute('aria-pressed', 'false');
    selected = button;
    selected.setAttribute('aria-pressed', 'true');
    section.querySelector('.nations-selected-name').textContent = button.dataset.countryName;
    selectedFlag.dataset.nationsFlagSrc = button.querySelector('img').dataset.nationsFlagSrc;
    showStatistic(dancersStat, button.dataset.dancerPercent, true);
    showStatistic(artistsStat, button.dataset.guestArtists, false);
    const x = Number(button.dataset.mapX);
    const y = Number(button.dataset.mapY);
    const mx = Number(destination.getAttribute('cx'));
    const my = Number(destination.getAttribute('cy'));
    const bend = Math.max(28, Math.hypot(mx - x, my - y) * .32);
    // The start and control points stay inside the original Europe view.
    const controlX = Math.max(24, Math.min(776, (x + mx) / 2 - bend));
    const controlY = Math.max(24, Math.min(596, Math.min(y, my) - bend));
    const approximate = button.dataset.mapApproximate === 'true';
    route.dataset.approximate = String(approximate);
    origin.toggleAttribute('hidden', approximate);
    moveRoute({ x, y, controlX, controlY, mx, my }, animate);
  }

  list.addEventListener('click', event => {
    const button = event.target.closest('[data-country]');
    if (!button) return;
    select(button);
    loadFlag(selectedFlag);
    // Keep the picker available for the next country without moving its scroll.
    button.focus({ preventScroll: true });
  });
  search.addEventListener('input', filter);
  section.querySelector('.nations-clear').addEventListener('click', () => {
    search.value = '';
    filter();
    search.focus({ preventScroll: true });
  });
  reduceMotion.addEventListener('change', () => {
    if (!reduceMotion.matches) return;
    cancelRouteAnimation();
    if (targetRoute) renderRoute(targetRoute);
  });
  buttons.forEach(button => { button.disabled = false; });
  section.classList.add('nations-enhanced');
  passport.hidden = false;
  tools.hidden = false;
  filter();
  select(buttons.find(button => button.dataset.country === 'ES') || buttons[0], false);
  preparePocketMap();
})();
