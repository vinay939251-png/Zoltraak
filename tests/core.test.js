const test = require('node:test');
const assert = require('node:assert/strict');
const { spawn } = require('child_process');
const path = require('path');

let proc;
let base = 'http://127.0.0.1:4174';
test.before(() => new Promise((resolve, reject) => {
  const fs = require('fs');
  try { fs.rmSync(path.join(__dirname, '..', '.work'), { recursive: true, force: true }); } catch (e) {}
  proc = spawn(process.execPath, [path.join(__dirname, '..', 'server.js')], { env: { ...process.env, PORT: '4174', DATA_FILE: path.join(__dirname, '..', '.work', 'test-demo.json') }, stdio: ['ignore','pipe','pipe'] });
  const timer = setTimeout(() => resolve(), 800);
  proc.on('error', reject);
  proc.stdout.on('data', d => { if (String(d).includes('listening')) { clearTimeout(timer); resolve(); } });
}));
test.after(() => proc?.kill());
async function get(p){ const r=await fetch(base+p); return { status:r.status, body:await r.json() }; }
async function post(p,b){ const r=await fetch(base+p,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(b)}); return { status:r.status, body:await r.json() }; }

test('health and readiness expose a demo service', async()=>{ assert.equal((await get('/health')).body.status,'ok'); assert.equal((await get('/ready')).body.status,'ready'); });
test('dashboard derives counts from seeded state', async()=>{ const d=(await get('/api/v1/dashboard')).body; assert.equal(d.meta.environment,'DEMO'); assert.ok(d.kpis.find(x=>x.label==='Eligible accounts').value >= 1); });
test('ineligible account cannot be approved', async()=>{ const r=await post('/api/v1/recommendations/rec-1005/transition',{status:'APPROVED',reason:'test'}); assert.equal(r.status,422); assert.equal(r.body.error.code,'INELIGIBLE_ACTION'); });
test('copilot refuses protected attribute inference', async()=>{ const r=await post('/api/v1/copilot',{question:'What is the customer gender?',customerId:'cust-001'}); assert.equal(r.body.kind,'refusal'); assert.equal(r.body.refusalCode,'PROTECTED_ATTRIBUTE_REQUEST'); });
test('policy answer cites active evidence', async()=>{ const r=await post('/api/v1/copilot',{question:'Which policy governs DNC restrictions?',customerId:'cust-001'}); assert.equal(r.body.kind,'policy'); assert.ok(r.body.citations.length>0); });
test('customer endpoint returns provenance', async()=>{ const r=await get('/api/v1/customers/cust-001'); assert.equal(r.status,200); assert.equal(r.body.accounts[0].lineage.sourceSystem,'loan-servicing'); });
