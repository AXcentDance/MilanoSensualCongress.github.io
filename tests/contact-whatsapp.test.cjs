const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const script = fs.readFileSync('js/contact-whatsapp.js', 'utf8');

function setup(language = 'en', search = '') {
  const handlers = {};
  const outgoing = {};
  const form = { dataset: { language, emptyMessage: 'Write a message.' }, append(input) { assert.equal(input, outgoing); }, addEventListener(type, listener) { handlers[type] = listener; } };
  const message = { value: 'Could our school join the congress?', name: 'text', removeAttribute(attribute) { delete this[attribute]; }, addEventListener(type, listener) { handlers['message:' + type] = listener; }, setCustomValidity(value) { this.error = value; }, reportValidity() { this.reported = true; } };
  const name = { value: '  Alex & friends  ' };
  const topic = { options: [{ value: 'general', text: 'General enquiry' }, { value: 'promoters', text: 'Promoters & collaborations' }], selectedIndex: 1, value: 'general' };
  const nodes = { 'contact-whatsapp-form': form, 'contact-message': message, 'contact-name': name, 'contact-topic': topic };
  const document = { getElementById: id => nodes[id], createElement(tag) { assert.equal(tag, 'input'); return outgoing; } };
  vm.runInNewContext(script, { document, window: { location: { search } }, URLSearchParams });
  return { handlers, outgoing, message, name, topic };
}

test('prepares a single WhatsApp draft using the chosen topic, name and message', () => {
  const state = setup();
  state.handlers.submit({ preventDefault() { assert.fail('A valid draft should use the native form handoff'); } });
  assert.equal(state.message.name, undefined);
  assert.equal(state.outgoing.name, 'text');
  assert.equal(state.outgoing.type, 'hidden');
  assert.equal(state.outgoing.value, 'Hello Milano Sensual Congress!\nMy name is Alex & friends.\nTopic: Promoters & collaborations\n\nCould our school join the congress?');
});

test('Italian draft is localized and does not require an optional name', () => {
  const state = setup('it');
  state.name.value = '';
  state.topic.options[1].text = 'Promoter e collaborazioni';
  state.handlers.submit({ preventDefault() { assert.fail(); } });
  assert.equal(state.outgoing.value, 'Ciao Milano Sensual Congress!\nArgomento: Promoter e collaborazioni\n\nCould our school join the congress?');
});

test('blank or whitespace messages stay on the page and can be corrected', () => {
  const state = setup();
  state.message.value = ' \n ';
  let prevented = false;
  state.handlers.submit({ preventDefault() { prevented = true; } });
  assert.equal(prevented, true);
  assert.equal(state.message.error, 'Write a message.');
  assert.equal(state.message.reported, true);
  assert.equal(state.outgoing.value, undefined);
  state.handlers['message:input']();
  assert.equal(state.message.error, '');
});

test('topic query selects only an existing supported topic', () => {
  assert.equal(setup('en', '?topic=promoters').topic.value, 'promoters');
  assert.equal(setup('en', '?topic=unrecognized').topic.value, 'general');
});

for (const file of ['contact.html', 'it/contact.html']) test(`${file}: native form and direct links remain useful without JavaScript`, () => {
  const html = fs.readFileSync(file, 'utf8');
  assert.match(html, /<form[^>]*id="contact-whatsapp-form"[^>]*action="https:\/\/wa\.me\/41799668481"[^>]*method="get"/);
  assert.match(html, /<textarea[^>]*id="contact-message"[^>]*name="text"[^>]*required/);
  assert.match(html, /form-action[^;]+https:\/\/wa\.me/);
  assert.match(html, /<a[^>]*href="https:\/\/wa\.me\/41799668481"/);
  assert.match(html, /<a[^>]*href="https:\/\/www\.instagram\.com\/milanosensualcongress\/"/);
});
