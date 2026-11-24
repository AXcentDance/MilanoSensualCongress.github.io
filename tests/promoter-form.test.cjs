const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const code = fs.readFileSync('scripts/ambassador-receiver.gs', 'utf8');
const id = 'c89862a3-99b5-46e0-9dc1-f0a35971f144';
const entry = {name: '=Test', phone: '+00123', country: 'Italy', city: 'Milano', role: 'teacher',
  community: '', message: 'First line\nSecond line', language: 'it', submissionId: id, response: 'json'};

function setup() {
  const rows = [Array(9).fill('').concat('Submission ID','Email sent at')];
  const emails = [];
  const mail = {sendEmail(...args) { emails.push(args); }, getRemainingDailyQuota() { return 10; }};
  const sheet = {
    getLastRow: () => rows.length, getSheetId: () => 42, getParent: () => ({getUrl: () => 'https://example.test/sheet'}),
    getRange(row, column, count = 1, width = 1) {
      const values = () => rows.slice(row-1, row+count-1).map(r => r.slice(column-1, column+width-1));
      return {
        getValue: () => rows[row-1]?.[column-1], getValues: values, setNumberFormat() { return this; },
        getDisplayValues: () => values().map(r => r.map(v => String(v || '').replace(/^'/, ''))),
        setValue(value) { rows[row-1][column-1] = value; return this; },
        setValues([data]) { rows[row-1] ||= []; rows[row-1].splice(column-1, data.length, ...data); },
        createTextFinder(value) {return {matchEntireCell() {return this;}, findNext() {
          const i = rows.findIndex(r => r[column-1] === value);
          return i < 0 ? null : {getRow: () => i+1};
        }};},
      };
    },
  };
  const context = {Date, console:{warn() {}}, AMBASSADOR_CONFIG:{sheetId:'test',recipient:'owner@example.test'},
    LockService:{getScriptLock:()=>({waitLock(){},tryLock:()=>true,hasLock:()=>true,releaseLock(){}})},
    SpreadsheetApp:{openById:()=>({getSheetByName:()=>sheet}),flush(){}}, MailApp:mail,
    ContentService:{MimeType:{JSON:'json'},createTextOutput:text=>({setMimeType:()=>JSON.parse(text)})}};
  vm.runInNewContext(code, context);
  return {context, rows, mail, emails, submit:(p=entry)=>context.doPost({parameter:p,postData:{length:500}})};
}

test('an application is stored literally once and emailed with every field and a link to its row', () => {
  const app = setup();
  assert.equal(app.submit().submissionId, id);
  assert.equal(app.submit().ok, true);
  assert.equal(app.rows.length, 2);
  assert.equal(app.rows[1][1], "'=Test");
  assert.equal(app.rows[1][2], "'+00123");
  assert.equal(app.emails.length, 1);
  const [to, subject, body] = app.emails[0];
  assert.equal(to, 'owner@example.test');
  assert.match(subject, /ambassador application/);
  for (const line of ['Full name: =Test','Phone / WhatsApp: +00123','Country: Italy','City: Milano','Role: Teacher',
    'School, community or organisation: Not provided','More about yourself: First line\nSecond line','Language: it','range=A2'])
    assert.ok(body.includes(line), line);
});

test('mail failures preserve the row and an hourly retry sends the missing notification once', () => {
  const app = setup();
  const send = app.mail.sendEmail;
  app.mail.sendEmail = () => {throw Error('Quota');};
  assert.equal(app.submit().ok, true);
  assert.equal(app.rows.length, 2);
  assert.equal(app.rows[1][10], undefined);
  app.mail.sendEmail = send;
  app.context.retryNotifications();
  app.context.retryNotifications();
  assert.equal(app.emails.length, 1);
  assert.ok(app.rows[1][10] instanceof Date);
});

test('invalid inputs never create a row or send mail, and optional fields can be blank', () => {
  const app = setup();
  for (const invalid of [{phone:'  '},{name:''},{country:''},{city:''},{role:'dancer'},{language:'invalid'},
    {submissionId:'invalid'},{message:'x'.repeat(1201)},{website:'bot'}])
    assert.equal(app.submit({...entry,...invalid}).ok, false);
  assert.equal(app.rows.length,1);
  assert.equal(app.emails.length,0);
  assert.equal(app.submit({...entry,role:'',message:''}).ok,true);
  assert.equal(app.context.doGet().service,'msc-ambassadors-2027');
});
