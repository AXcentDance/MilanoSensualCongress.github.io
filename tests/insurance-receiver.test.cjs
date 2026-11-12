const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const code=fs.readFileSync('scripts/insurance-receiver.gs','utf8');
function setup(){
 const rows=[];
 const sheet={getLastRow:()=>rows.length+1,getRange:(r,c)=>({getValue:()=> 'ID invio / Submission ID',setNumberFormat(){return this;},setValues(v){rows.push(v[0]);},createTextFinder(id){return {matchEntireCell(){return this;},findNext:()=>rows.find(row=>row[10]===id)};}})};
 const ctx={Date,Utilities:{formatDate:()=>new Date().toISOString().slice(0,10)},PropertiesService:{getScriptProperties:()=>({getProperty:()=> 'test-sheet'})},SpreadsheetApp:{openById:()=>({getSheetByName:()=>sheet}),flush(){}},LockService:{getScriptLock:()=>({tryLock:()=>true,hasLock:()=>true,releaseLock(){}})},ContentService:{MimeType:{JSON:'json'},createTextOutput:text=>({setMimeType:()=>JSON.parse(text)})}};
 vm.createContext(ctx);vm.runInContext(code,ctx);return {ctx,rows};
}
const valid={lastName:'=IMPORTXML("test")',firstName:'Test',sex:'F',dateOfBirth:'1990-02-15',placeOfBirth:'Italia',address:'Via test 1',postalCode:'00123',municipality:'Milano',email:'test@example.com',submissionId:'12345678-1234-4123-8123-123456789abc',website:''};
test('receiver writes safe text and deduplicates retries',()=>{
 const {ctx,rows}=setup();const event={postData:{length:500},parameter:valid};
 assert.equal(ctx.doPost(event).ok,true);assert.equal(ctx.doPost(event).ok,true);assert.equal(rows.length,1);
 assert.equal(rows[0][0],"'"+valid.lastName);assert.equal(rows[0][6],"'00123");assert.ok(rows[0][3] instanceof Date);
});
test('receiver rejects missing fields, impossible/future dates and honeypot',()=>{
 for(const patch of [{email:''},{dateOfBirth:'2025-02-30'},{dateOfBirth:'2999-01-01'},{website:'spam'},{sex:'invalid'},{submissionId:'invalid'}]){
 const {ctx,rows}=setup();assert.equal(ctx.doPost({postData:{length:500},parameter:{...valid,...patch}}).ok,false);assert.equal(rows.length,0);
 }
});
test('GET never exposes response rows',()=>{const {ctx}=setup();assert.deepEqual(JSON.parse(JSON.stringify(ctx.doGet())),{ok:true,service:'msc-insurance-2026'});});
