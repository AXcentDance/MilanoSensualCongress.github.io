const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { resolve } = require('node:path');
const { test } = require('node:test');
const vm = require('node:vm');

const pages = ['index.html', 'tickets.html', 'it/index.html', 'it/tickets.html'];

function mount(page, { reply = 'success', httpOK = true, networkError = false, analyticsError = false } = {}) {
  const html = readFileSync(resolve(__dirname, '..', page), 'utf8');
  const handler = html.slice(html.indexOf('    // Wait for the Apps Script acknowledgement'))
    .split('</script>')[0];
  const source = /name="source" value="([^"]+)"/.exec(html)[1];
  const action = /id="reminder-form" action="([^"]+)"/.exec(html)[1];
  const button = { innerHTML: 'Submit', disabled: false };
  const container = { innerHTML: 'Original form', setAttribute() {} };
  const status = { hidden: true, style: {}, setAttribute() {} };
  let submit, finishRequest, timer, request;
  const leads = [];
  const form = {
    action,
    querySelector: () => button,
    setAttribute() {}, removeAttribute() {}, after() {},
    addEventListener: (_, listener) => { submit = listener; }
  };
  const context = {
    document: {
      getElementById: id => id === 'reminder-form' ? form : container,
      createElement: () => status
    },
    FormData: class { get(key) { return key === 'email' ? '  test+reminder@example.com  ' : source; } },
    URL, AbortController,
    setTimeout: callback => { timer = callback; return 1; },
    clearTimeout: () => { timer = null; },
    fetch: (url, options) => {
      request = { url, options };
      return new Promise((resolve, reject) => {
        finishRequest = () => networkError ? reject(new Error('Offline'))
          : resolve({ ok: httpOK, text: async () => reply });
        options.signal.addEventListener('abort', () => reject(new Error('Timeout')));
      });
    },
    startMetaPixel: () => { if (analyticsError) throw new Error('Analytics unavailable'); },
    window: { fbq: true },
    fbq: (...args) => leads.push(args)
  };
  vm.runInNewContext(handler, context);
  return {
    html, source, button, container, status, leads,
    submit: () => submit.call(form, { preventDefault() {} }),
    finish: () => finishRequest(),
    timeout: () => timer(),
    request: () => request,
    timer: () => timer
  };
}

for (const page of pages) {
  test(`${page}: CSP permits the request and Google response redirect`, () => {
    const { html } = mount(page);
    for (const directive of ['connect-src', 'form-action']) {
      const policy = new RegExp(`${directive} ([^;]+)`).exec(html)[1].split(' ');
      assert.ok(policy.includes('https://script.google.com'));
      assert.ok(policy.includes('https://script.googleusercontent.com'));
    }
    assert.match(html, /id="reminder-form"[^>]+method="GET"/);
    assert.doesNotMatch(html, /hiddenIframe|formspree\.io/);
  });

  test(`${page}: waits for acknowledgement, encodes fields and prevents duplicate sends`, async () => {
    const app = mount(page);
    const pending = app.submit();
    const request = app.request();
    assert.equal(request.url.searchParams.get('email'), 'test+reminder@example.com');
    assert.equal(request.url.searchParams.get('source'), app.source);
    assert.equal(request.options.mode, 'cors');
    assert.equal(request.options.cache, 'no-store');
    assert.equal(app.button.disabled, true);
    assert.equal(app.container.innerHTML, 'Original form');
    assert.equal(app.leads.length, 0);
    await app.submit();
    assert.equal(app.request(), request);
    app.finish();
    await pending;
    assert.match(app.container.innerHTML, page.startsWith('it/') ? /Grazie!/ : /Thank you!/);
    assert.equal(app.leads.length, 1);
    assert.equal(app.leads[0][2].source, app.source);
    assert.equal(app.timer(), null);
  });

  for (const [reason, options] of Object.entries({
    'server error': { httpOK: false },
    'unacknowledged response': { reply: 'error: spreadsheet unavailable' },
    'login HTML with HTTP 200': { reply: '<html>Sign in</html>' },
    'network failure': { networkError: true }
  })) {
    test(`${page}: ${reason} keeps the form and enables retry`, async () => {
      const app = mount(page, options);
      const pending = app.submit();
      app.finish();
      await pending;
      assert.equal(app.container.innerHTML, 'Original form');
      assert.equal(app.button.disabled, false);
      assert.equal(app.button.innerHTML, 'Submit');
      assert.equal(app.status.hidden, false);
      assert.match(app.status.textContent, page.startsWith('it/') ? /Non è stato possibile/ : /could not confirm/);
      assert.equal(app.leads.length, 0);
      assert.equal(app.timer(), null);
    });
  }

  test(`${page}: timeout cancels waiting and allows a fresh attempt`, async () => {
    const app = mount(page);
    const pending = app.submit();
    app.timeout();
    await pending;
    assert.equal(app.request().options.signal.aborted, true);
    assert.equal(app.status.hidden, false);
    assert.equal(app.button.disabled, false);
    assert.equal(app.leads.length, 0);
    const retry = app.submit();
    assert.equal(app.status.hidden, true);
    app.finish();
    await retry;
    assert.equal(app.leads.length, 1);
  });

  test(`${page}: analytics failure does not undo confirmed success`, async () => {
    const app = mount(page, { analyticsError: true });
    const pending = app.submit();
    app.finish();
    await pending;
    assert.match(app.container.innerHTML, page.startsWith('it/') ? /Grazie!/ : /Thank you!/);
    assert.equal(app.status.hidden, true);
  });
}
