(() => {
  'use strict';

  document.querySelectorAll('[data-early-bird-countdown]').forEach(root => {
    const units = ['days', 'hours', 'minutes', 'seconds'].map(unit =>
      root.querySelector(`[data-countdown-unit="${unit}"]`));
    if (units.some(unit => !unit)) return;

    root.setAttribute('role', 'timer');
    root.setAttribute('aria-live', 'off');
    const value = root.dataset.deadline || '';
    const format = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?(?:Z|[+-]\d{2}:\d{2})$/;
    const deadline = format.test(value) ? Date.parse(value) : NaN;
    const calendar = format.test(value) ? new Date(`${value.slice(0, 19)}Z`) : null;
    // Require an explicit offset and a real date; Date.parse alone normalizes February 30.
    if (!Number.isFinite(deadline) || !calendar || !Number.isFinite(calendar.getTime()) ||
        calendar.toISOString().slice(0, 19) !== value.slice(0, 19)) {
      units.forEach(unit => { unit.textContent = '--'; });
      return;
    }

    const status = root.parentElement?.querySelector('[data-countdown-status]');
    let interval;
    const stop = () => {
      if (interval !== undefined) clearInterval(interval);
      interval = undefined;
    };
    const update = () => {
      const remaining = Math.max(0, Math.ceil((deadline - Date.now()) / 1000));
      const values = [Math.floor(remaining / 86400), Math.floor(remaining / 3600) % 24,
        Math.floor(remaining / 60) % 60, remaining % 60];
      units.forEach((unit, index) => {
        const text = String(values[index]).padStart(2, '0');
        if (unit.textContent !== text) unit.textContent = text;
      });
      if (!remaining) {
        stop();
        if (status && root.dataset.expiredMessage) status.textContent = root.dataset.expiredMessage;
        [['h2', 'expiredHeading'], ['#early-bird-description', 'expiredDescription']].forEach(([selector, key]) => {
          const element = root.parentElement?.querySelector(selector);
          if (element && root.dataset[key]) element.textContent = root.dataset[key];
        });
      }
      return remaining;
    };
    const refresh = () => {
      stop();
      if (update() && !document.hidden) interval = setInterval(update, 1000);
    };
    document.addEventListener('visibilitychange', refresh);
    refresh();
  });
})();
