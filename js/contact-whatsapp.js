/* Prepare a message for the official public WhatsApp contact; never send it here. */
(() => {
  const form = document.getElementById('contact-whatsapp-form');
  if (!form) return;
  const message = document.getElementById('contact-message');
  const name = document.getElementById('contact-name');
  const topic = document.getElementById('contact-topic');
  const outgoing = document.createElement('input');
  outgoing.type = 'hidden';
  outgoing.name = 'text';
  form.append(outgoing);
  // Without JavaScript, the native form carries the message field directly.
  message.removeAttribute('name');
  const requestedTopic = new URLSearchParams(window.location.search).get('topic');
  if ([...topic.options].some(option => option.value === requestedTopic)) topic.value = requestedTopic;
  message.addEventListener('input', () => message.setCustomValidity(''));
  form.addEventListener('submit', event => {
    const body = message.value.trim();
    if (!body) {
      event.preventDefault();
      message.setCustomValidity(form.dataset.emptyMessage);
      message.reportValidity();
      return;
    }
    const italian = form.dataset.language === 'it';
    const greeting = italian ? 'Ciao Milano Sensual Congress!' : 'Hello Milano Sensual Congress!';
    const sender = name.value.trim();
    const introduction = sender ? (italian ? `Mi chiamo ${sender}.` : `My name is ${sender}.`) : '';
    const subject = topic.options[topic.selectedIndex].text;
    outgoing.value = [greeting, introduction, `${italian ? 'Argomento' : 'Topic'}: ${subject}`, '', body].filter((line, index) => line || index === 3).join('\n');
  });
})();
