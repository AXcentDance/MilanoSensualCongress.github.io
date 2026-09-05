(() => {
  // Wait for the Apps Script acknowledgement before confirming the reminder.
  const reminderForm = document.getElementById('reminder-form');
  if (reminderForm) {
    const status = document.createElement('p');
    status.setAttribute('role', 'alert');
    status.style.cssText = 'color: #fda4af; font-size: 0.875rem; text-align: center; margin-top: 0.75rem';
    status.hidden = true;
    reminderForm.after(status);

    reminderForm.addEventListener('submit', async function (e) {
      e.preventDefault();
      const form = this;
      const container = document.getElementById('reminder-container');
      const button = form.querySelector('button');
      if (button.disabled) return;
      const originalButtonText = button.innerHTML;
      button.innerHTML = `<i class="fa-solid fa-circle-notch animate-spin"></i> ${form.dataset.processing}`;
      button.disabled = true;
      form.setAttribute('aria-busy', 'true');
      status.hidden = true;

      const data = new FormData(form);
      const submitUrl = new URL(form.action);
      submitUrl.searchParams.set('email', data.get('email').trim());
      submitUrl.searchParams.set('source', data.get('source'));
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 30000);

      try {
        // A simple CORS GET matches the deployed doGet handler. Google redirects
        // the acknowledgement to script.googleusercontent.com (allowed by CSP).
        const response = await fetch(submitUrl, {
          mode: 'cors',
          credentials: 'omit',
          redirect: 'follow',
          cache: 'no-store',
          referrerPolicy: 'no-referrer',
          signal: controller.signal
        });
        if (!response.ok || (await response.text()).trim() !== 'success') {
          throw new Error('Reminder was not acknowledged');
        }
        container.setAttribute('role', 'status');
        container.innerHTML = document.getElementById('reminder-success').innerHTML;

        // Analytics must not prevent saving or turn a saved reminder into an error.
        try {
          if (typeof startMetaPixel === 'function') startMetaPixel();
          if (window.fbq) {
            fbq('track', 'Lead', {
              content_name: 'Price increase reminder',
              content_category: 'Email reminder',
              source: data.get('source')
            });
          }
        } catch (_) { /* The reminder is already confirmed. */ }
      } catch (_) {
        status.textContent = form.dataset.error;
        status.hidden = false;
      } finally {
        clearTimeout(timeout);
        button.innerHTML = originalButtonText;
        button.disabled = false;
        form.removeAttribute('aria-busy');
      }
    });
  }
})();
