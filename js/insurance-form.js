(() => {
  const form = document.getElementById('insurance-form');
  if (!form) return;
  const button = form.querySelector('button[type=submit]');
  const status = document.getElementById('insurance-status');
  const date = form.elements.dateOfBirth;
  const today = new Date();
  date.max = [today.getFullYear(),String(today.getMonth()+1).padStart(2,'0'),String(today.getDate()).padStart(2,'0')].join('-');
  const endpoint = form.dataset.endpoint;
  const ready = /^https:\/\/script\.google\.com\/macros\/s\/[A-Za-z0-9_-]+\/exec$/.test(endpoint);
  let busy = false, sent = false, requestId = '', signature = '';
  if (ready) { button.disabled = false; status.textContent = ''; }
  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (!ready || busy || sent) return;
    for (const input of form.querySelectorAll('input[required]')) {
      input.value = input.value.trim();
      input.setCustomValidity(input.value ? '' : 'Compila questo campo. / Complete this field.');
      input.addEventListener('input', () => input.setCustomValidity(''), {once:true});
    }
    if (!form.reportValidity()) return;
    const data = new URLSearchParams(new FormData(form));
    const nextSignature = data.toString();
    if (signature !== nextSignature) { requestId = crypto.randomUUID(); signature = nextSignature; }
    data.set('submissionId',requestId);
    busy = true; button.disabled = true; form.setAttribute('aria-busy','true');
    status.dataset.state = 'pending'; status.textContent = 'Invio in corso… / Sending…';
    button.textContent = 'Invio… / Sending…';
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(),30000);
    try {
      const response = await fetch(endpoint,{method:'POST',body:data,mode:'cors',credentials:'omit',redirect:'follow',referrerPolicy:'no-referrer',signal:controller.signal});
      const result = await response.json();
      if (!response.ok || result.ok !== true || result.submissionId !== requestId) throw new Error('Unconfirmed submission');
      sent = true;
      form.reset();
      for (const input of form.querySelectorAll('input,select')) input.disabled = true;
      status.dataset.state = 'success';
      status.textContent = 'Dati ricevuti. Grazie! / Your details have been received. Thank you!';
      button.textContent = 'Inviato / Submitted';
    } catch (_) {
      status.dataset.state = 'error';
      status.textContent = 'Invio non confermato. Riprova: i dati sono ancora nel modulo. / Submission not confirmed. Please try again. Your details are still in the form.';
      button.textContent = 'Riprova / Try again';
    } finally {
      clearTimeout(timeout); busy = false; button.disabled = sent; form.removeAttribute('aria-busy');
    }
  });
})();
