// Google Apps Script. Set AMBASSADOR_CONFIG = { sheetId, recipient } in a private
// project file, then run enableNotificationRetries once as the project owner.
const APPLICATION_FIELDS = ['name','phone','country','city','role','community','message','language'];
const APPLICATION_HEADERS = ['Full name','Phone / WhatsApp','Country','City','Role','School, community or organisation','More about yourself','Language'];
const APPLICATION_ROLES = {promoter:'Promoter', teacher:'Teacher', school:'Dance school', organiser:'Event organiser', creator:'Content creator', other:'Other'};

function doGet() {
  return json_({service:'msc-ambassadors-2027'});
}

function doPost(event) {
  const p = event && event.parameter || {};
  const lock = LockService.getScriptLock();
  let ok = false;
  try {
    if (!event.postData || event.postData.length > 16000 || p.website) throw Error('Invalid request');
    const values = applicationValues_(p);
    const id = applicationId_(p, values);
    lock.waitLock(15000);
    const sheet = applicationSheet_();
    const last = sheet.getLastRow();
    const match = last > 1 && sheet.getRange(2,10,last-1,1).createTextFinder(id).matchEntireCell(true).findNext();
    const row = match ? match.getRow() : last + 1;
    if (!match) {
      sheet.getRange(row,2,1,9).setNumberFormat('@');
      sheet.getRange(row,1,1,10).setValues([[new Date(), ...values.map(v => v ? "'" + v : ''), id]]);
      sheet.getRange(row,1).setNumberFormat('yyyy-mm-dd hh:mm:ss');
      SpreadsheetApp.flush();
    }
    ok = true; // The application is saved even if the mail service is temporarily unavailable.
    if (!sheet.getRange(row,11).getValue()) notifyApplication_(sheet, row);
  } catch (error) {
    if (ok) console.warn('Ambassador notification pending retry.');
  } finally {
    if (lock.hasLock()) lock.releaseLock();
  }
  if (p.response === 'json') return json_({ok:ok, submissionId:p.submissionId || ''});
  const italian = p.language === 'it';
  const message = ok
    ? (italian ? 'Candidatura ricevuta. Grazie!' : 'Application received. Thank you!')
    : (italian ? 'Invio non confermato. Torna al modulo e riprova.' : 'Submission could not be confirmed. Go back to the form and try again.');
  return ContentService.createTextOutput(message);
}

function applicationValues_(p) {
  const values = APPLICATION_FIELDS.map((key, index) => {
    const value = String(p[key] || '').trim();
    if (index < 4 && !value) throw Error('Missing required field');
    if (value.length > (key === 'message' ? 1200 : 100)) throw Error('Field too long');
    const controls = key === 'message' ? /[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/ : /[\x00-\x1f\x7f]/;
    if (controls.test(value)) throw Error('Invalid text');
    return value;
  });
  if (!['en','it'].includes(values[7])) throw Error('Invalid language');
  if (values[4]) {
    if (!Object.prototype.hasOwnProperty.call(APPLICATION_ROLES, values[4])) throw Error('Invalid role');
    values[4] = APPLICATION_ROLES[values[4]];
  }
  return values;
}

function applicationId_(p, values) {
  if (p.submissionId || p.response === 'json') {
    if (!/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(p.submissionId || '')) throw Error('Invalid submission ID');
    return p.submissionId;
  }
  // Native HTML submissions can be refreshed or retried without JavaScript.
  const body = JSON.stringify([Math.floor(Date.now()/600000), values]);
  return Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, body, Utilities.Charset.UTF_8)
    .map(byte => ('0' + (byte & 255).toString(16)).slice(-2)).join('');
}

function applicationSheet_() {
  const sheet = SpreadsheetApp.openById(AMBASSADOR_CONFIG.sheetId).getSheetByName('Applications');
  if (!sheet || sheet.getRange(1,10).getValue() !== 'Submission ID') throw Error('Unexpected sheet layout');
  return sheet;
}

function notifyApplication_(sheet, row) {
  const entry = sheet.getRange(row,1,1,10).getDisplayValues()[0];
  const lines = APPLICATION_HEADERS.map((label, i) => label + ': ' + (entry[i+1] || 'Not provided'));
  const url = sheet.getParent().getUrl() + '#gid=' + sheet.getSheetId() + '&range=A' + row;
  MailApp.sendEmail(AMBASSADOR_CONFIG.recipient, 'MSC 2027 | New ambassador application',
    ['Received (Milan time): ' + entry[0], ...lines, '', url].join('\n'));
  sheet.getRange(row,11).setValue(new Date()).setNumberFormat('yyyy-mm-dd hh:mm:ss');
  SpreadsheetApp.flush();
}

function retryNotifications() {
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(5000)) return;
  try {
    const sheet = applicationSheet_();
    const last = sheet.getLastRow();
    if (last < 2) return;
    const rows = sheet.getRange(2,10,last-1,2).getValues();
    let remaining = Math.min(25, MailApp.getRemainingDailyQuota());
    for (let i = 0; i < rows.length && remaining > 0; i++) {
      if (!rows[i][0] || rows[i][1]) continue;
      notifyApplication_(sheet, i + 2);
      remaining--;
    }
  } finally { lock.releaseLock(); }
}

function enableNotificationRetries() {
  if (!ScriptApp.getProjectTriggers().some(t => t.getHandlerFunction() === 'retryNotifications')) {
    ScriptApp.newTrigger('retryNotifications').timeBased().everyHours(1).create();
  }
}

function json_(value) {
  return ContentService.createTextOutput(JSON.stringify(value)).setMimeType(ContentService.MimeType.JSON);
}
