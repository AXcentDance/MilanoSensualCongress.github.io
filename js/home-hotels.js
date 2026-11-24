/* Native hotel radios also work without JavaScript. Hashes allow direct view links. */
(() => {
  const choices = [...document.querySelectorAll('.venue-hotel-switch input')];
  if (choices.length !== 2) return;
  function restoreView() {
    const value = location.hash === '#stay-cambiago' ? 'cambiago' : location.hash === '#stay-devero' ? 'devero' : null;
    if (value) choices.find(input => input.value === value).checked = true;
  }
  restoreView();
  addEventListener('hashchange', restoreView);
  addEventListener('pageshow', restoreView);
  choices.forEach(input => input.addEventListener('change', () => {
    if (input.checked) history.replaceState(null, '', `${location.pathname}${location.search}#stay-${input.value}`);
  }));
})();
