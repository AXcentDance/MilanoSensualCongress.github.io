/* A structured application drafted in the existing official WhatsApp chat.
   No application is sent, stored or reported as received by this page. */
(() => {
  const form = document.getElementById('promoter-application-form');
  if (!form) return;
  const fields = [...form.querySelectorAll('[data-application-label]')];
  const message = document.getElementById('promoter-message');
  const outgoing = document.createElement('input');
  outgoing.type = 'hidden';
  outgoing.name = 'text';
  form.append(outgoing);
  message.removeAttribute('name');

  fields.forEach(field => {
    field.addEventListener('input', () => field.setCustomValidity(''));
    field.addEventListener('change', () => field.setCustomValidity(''));
  });
  form.addEventListener('submit', event => {
    const empty = fields.find(field => field.required && !field.value.trim());
    if (empty) {
      event.preventDefault();
      empty.setCustomValidity(form.dataset.emptyMessage);
      empty.reportValidity();
      return;
    }
    const lines = fields.flatMap(field => {
      const value = field.value.trim();
      if (!value) return [];
      const displayValue = field.tagName === 'SELECT'
        ? field.options[field.selectedIndex].text
        : value;
      return [`${field.dataset.applicationLabel}: ${displayValue}`];
    });
    outgoing.value = [form.dataset.applicationTitle, '', ...lines].join('\n');
  });
})();
