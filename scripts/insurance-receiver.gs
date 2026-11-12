/** Standalone Apps Script receiver. Writes only to the dedicated 2026 Insurance sheet.
 * Deploy as a web app executing as the owner, accessible to Anyone.
 * POST is write-only; GET exposes no participant data. */
const INSURANCE_FIELDS = ['lastName','firstName','sex','dateOfBirth','placeOfBirth','address','postalCode','municipality','email'];
function doGet() { return insuranceJson_({ok:true,service:'msc-insurance-2026'}); }
function doPost(event) {
  let lock;
  try {
    if (!event || !event.postData || event.postData.length > 12000) throw new Error('Invalid request');
    const p = event.parameter || {};
    const values = insuranceValidate_(p);
    lock = LockService.getScriptLock();
    if (!lock.tryLock(20000)) throw new Error('Busy');
    const id = '1LFbX4adavRC7DViY4OcyHczfsLHqhLeVUfgF8w4LtSE';
    if (!id) throw new Error('Missing configuration');
    const sheet = SpreadsheetApp.openById(id).getSheetByName('Insurance');
    if (!sheet || sheet.getRange(1,11).getValue() !== 'ID invio / Submission ID') throw new Error('Unexpected sheet layout');
    const last = sheet.getLastRow();
    if (last > 1 && sheet.getRange(2,11,last-1,1).createTextFinder(p.submissionId).matchEntireCell(true).findNext()) {
      return insuranceJson_({ok:true,submissionId:p.submissionId});
    }
    const row = last+1;
    // Write user text literally, including formula prefixes and leading zeroes.
    sheet.getRange(row,1,1,11).setNumberFormat('@');
    const cells = values.map(value => "'" + value);
    const parts = p.dateOfBirth.split('-').map(Number);
    cells[3] = new Date(parts[0],parts[1]-1,parts[2],12);
    sheet.getRange(row,1,1,11).setValues([[...cells,new Date(),p.submissionId]]);
    sheet.getRange(row,4).setNumberFormat('dd/mm/yyyy');
    sheet.getRange(row,10).setNumberFormat('dd/mm/yyyy hh:mm:ss');
    SpreadsheetApp.flush();
    return insuranceJson_({ok:true,submissionId:p.submissionId});
  } catch (_) { return insuranceJson_({ok:false}); }
  finally { if (lock && lock.hasLock()) lock.releaseLock(); }
}
function insuranceValidate_(p) {
  if (p.website || !/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(p.submissionId || '')) throw new Error('Invalid request');
  const limits = [100,100,1,10,160,200,20,160,254];
  const values = INSURANCE_FIELDS.map((key,i) => {
    const value = typeof p[key] === 'string' ? p[key].trim() : '';
    if (!value || value.length > limits[i] || /[\u0000-\u001f\u007f]/.test(value)) throw new Error('Invalid field');
    return value;
  });
  if (!['F','M','X'].includes(values[2]) || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(values[8])) throw new Error('Invalid field');
  if (!/^\d{4}-\d{2}-\d{2}$/.test(values[3])) throw new Error('Invalid date');
  const date = new Date(values[3]+'T12:00:00Z');
  if (isNaN(date) || date.toISOString().slice(0,10) !== values[3] || values[3] > Utilities.formatDate(new Date(),'Europe/Rome','yyyy-MM-dd')) throw new Error('Invalid date');
  return values;
}
function insuranceJson_(value) { return ContentService.createTextOutput(JSON.stringify(value)).setMimeType(ContentService.MimeType.JSON); }
