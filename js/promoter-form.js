(() => {
  const form = document.querySelector('[data-application-form]');
  if (!form || !window.fetch || !window.crypto?.randomUUID) return;
  const status = form.querySelector('[role="status"]');
  const button = form.querySelector('button[type="submit"]');
  let lastPayload = '';
  let submissionId = '';
  let busy = false;
  let submitted = false;

  form.addEventListener('input', event => event.target.setCustomValidity?.(''));
  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (busy || submitted) return;
    for (const field of form.querySelectorAll('[required]')) {
      if (!field.value.trim()) {
        field.setCustomValidity(form.dataset.emptyMessage);
        field.reportValidity();
        return;
      }
    }
    const data = new URLSearchParams(new FormData(form));
    const payload = data.toString();
    if (payload !== lastPayload) {
      submissionId = crypto.randomUUID();
      lastPayload = payload;
    }
    data.set('response', 'json');
    data.set('submissionId', submissionId);
    busy = true;
    button.disabled = true;
    status.textContent = form.dataset.pending;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 30000);
    try {
      const response = await fetch(form.action, {
        method: 'POST', body: data, credentials: 'omit', referrerPolicy: 'no-referrer', signal: controller.signal,
      });
      const receipt = await response.json();
      if (!response.ok || receipt.ok !== true || receipt.submissionId !== submissionId) throw Error('Missing receipt');
      submitted = true;
      form.reset();
      for (const field of form.querySelectorAll('input, select, textarea')) field.disabled = true;
      button.textContent = form.dataset.submitted;
      status.textContent = form.dataset.success;
    } catch {
      status.textContent = form.dataset.error;
    } finally {
      clearTimeout(timeout);
      busy = false;
      button.disabled = submitted;
    }
  });
})();
