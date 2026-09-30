const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const script = fs.readFileSync('js/promoter-form.js', 'utf8');

function setup() {
  const handlers = {};
  const fields = [
    ['name', 'Full name', ' Alex & Dancers ', true],
    ['email', 'Email', 'alex@example.test', true],
    ['phone', 'Phone / WhatsApp', '', false],
    ['country', 'Country', 'Switzerland', true],
    ['city', 'City', 'Zürich', true],
    ['role', 'Your role', 'teacher', false],
    ['message', 'Introduction and proposal', 'Bachata classes & events.\nA group from our school.', true],
  ].map(([id, label, value, required]) => ({
    id, dataset: { applicationLabel: label }, value, required, tagName: id === 'role' ? 'SELECT' : 'INPUT',
    name: id === 'message' ? 'text' : undefined,
    options: [{ text: 'Teacher' }], selectedIndex: 0,
    addEventListener(type, fn) { handlers[id + ':' + type] = fn; },
    setCustomValidity(error) { this.error = error; },
    reportValidity() { this.reported = true; },
    removeAttribute(name) { delete this[name]; },
  }));
  const outgoing = {};
  const form = {
    dataset: { applicationTitle: 'Ambassador application — Milano Sensual Congress 2027', emptyMessage: 'Please complete this field.' },
    querySelectorAll() { return fields; },
    append(input) { assert.equal(input, outgoing); },
    addEventListener(type, fn) { handlers[type] = fn; },
  };
  vm.runInNewContext(script, { document: {
    getElementById(id) { return id === 'promoter-application-form' ? form : fields.at(-1); },
    createElement(tag) { assert.equal(tag, 'input'); return outgoing; },
  } });
  return { fields, outgoing, handlers, form };
}

test('ambassador draft includes labelled fields, readable role and multiline proposal', () => {
  const app = setup();
  app.handlers.submit({ preventDefault() { assert.fail(); } });
  assert.equal(app.outgoing.name, 'text');
  assert.equal(app.outgoing.type, 'hidden');
  assert.equal(app.fields.at(-1).name, undefined);
  assert.equal(app.outgoing.value, 'Ambassador application — Milano Sensual Congress 2027\n\nFull name: Alex & Dancers\nEmail: alex@example.test\nCountry: Switzerland\nCity: Zürich\nYour role: Teacher\nIntroduction and proposal: Bachata classes & events.\nA group from our school.');
});

test('required whitespace is rejected and corrected input clears validation', () => {
  const app = setup();
  app.fields[0].value = '  \n ';
  let prevented = false;
  app.handlers.submit({ preventDefault() { prevented = true; } });
  assert.equal(prevented, true);
  assert.equal(app.fields[0].error, 'Please complete this field.');
  assert.equal(app.fields[0].reported, true);
  assert.equal(app.outgoing.value, undefined);
  app.fields[0].value = 'Alex';
  app.handlers['name:input']();
  assert.equal(app.fields[0].error, '');
  app.handlers.submit({ preventDefault() { assert.fail(); } });
  assert.match(app.outgoing.value, /Full name: Alex/);
});

test('optional omissions are excluded and localization is read from page labels', () => {
  const app = setup();
  app.form.dataset.applicationTitle = 'Candidatura Ambassador — Milano Sensual Congress 2027';
  app.fields[0].dataset.applicationLabel = 'Nome e cognome';
  app.fields[5].value = '';
  app.handlers.submit({ preventDefault() { assert.fail(); } });
  assert.match(app.outgoing.value, /^Candidatura Ambassador/);
  assert.match(app.outgoing.value, /Nome e cognome: Alex & Dancers/);
  assert.doesNotMatch(app.outgoing.value, /Your role|Phone/);
});
