const http = require('http');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const ROOT = __dirname;
const PORT = Number(process.env.PORT || 4173);
const DATA_FILE = path.resolve(process.env.DATA_FILE || path.join(ROOT, 'data', 'demo.json'));
const SEED_FILE = path.join(ROOT, 'data', 'seed.json');
const PUBLIC = path.join(ROOT, 'public');

function clone(value) { return JSON.parse(JSON.stringify(value)); }
function loadState() {
  if (!fs.existsSync(DATA_FILE)) { fs.mkdirSync(path.dirname(DATA_FILE), { recursive: true }); fs.writeFileSync(DATA_FILE, JSON.stringify(JSON.parse(fs.readFileSync(SEED_FILE)), null, 2)); }
  return JSON.parse(fs.readFileSync(DATA_FILE, 'utf8'));
}
let state = loadState();
function saveState() { const tmp = `${DATA_FILE}.tmp`; fs.writeFileSync(tmp, JSON.stringify(state, null, 2)); fs.renameSync(tmp, DATA_FILE); }
function id(prefix) { return `${prefix}-${crypto.randomUUID().slice(0, 8)}`; }
function now() { return new Date().toISOString(); }
function money(n) { return Number(Number(n).toFixed(2)); }
function user() { const requested = process.env.DEMO_USER_ID || 'agent-001'; return state.users.find(u => u.id === requested) || state.users[0]; }
function accountFor(id) { return state.accounts.find(a => a.id === id); }
function customerFor(id) { return state.customers.find(c => c.id === id); }
function visibleAccount(account, actor = user()) { return actor.role !== 'collections_agent' || actor.assignedAccountIds.includes(account.id); }
function audit(type, entityId, summary, extra = {}) { state.audit.unshift({ id: id('audit'), type, actor: user().id, entityId, timestamp: now(), summary, ...extra }); saveState(); }
function json(res, status, body) { res.writeHead(status, { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' }); res.end(JSON.stringify(body)); }
function ok(body) { return { ...body, meta: { ...state.meta, currentUser: user() } }; }
function readBody(req) { return new Promise((resolve, reject) => { let raw = ''; req.on('data', c => { raw += c; if (raw.length > 200000) reject(new Error('body_too_large')); }); req.on('end', () => { try { resolve(raw ? JSON.parse(raw) : {}); } catch { reject(new Error('invalid_json')); } }); }); }
function sendError(res, status, code, message, details = {}) { json(res, status, { error: { code, message, details }, meta: state.meta }); }
function eligibility(account) {
  const results = [];
  const add = (ruleId, passed, reasonCode, reason) => results.push({ ruleId, passed, reasonCode, reason });
  add('ACCOUNT-001', account.status === 'ACTIVE', account.status === 'ACTIVE' ? 'ACTIVE' : 'ACCOUNT_NOT_ACTIVE', account.status === 'ACTIVE' ? 'Account is active.' : 'Account status is not active.');
  add('DNC-001', !account.dnc, account.dnc ? 'CONTACT_RESTRICTED' : 'CONTACT_ALLOWED', account.dnc ? 'Verified do-not-contact restriction is active.' : 'No do-not-contact restriction is active.');
  add('CAP-001', account.contactCount7d < 4, account.contactCount7d < 4 ? 'CONTACT_CAP_AVAILABLE' : 'CONTACT_CAP_EXCEEDED', `${account.contactCount7d} contacts recorded in the seven-day window.`);
  add('DISPUTE-001', !account.dispute, account.dispute ? 'SPECIALIST_REQUIRED' : 'NO_OPEN_DISPUTE', account.dispute ? 'Open dispute requires specialist review.' : 'No open dispute is recorded.');
  add('HARDSHIP-001', !account.hardship, account.hardship ? 'SPECIALIST_REQUIRED' : 'NO_HARDSHIP_FLAG', account.hardship ? 'Hardship review is required before ordinary collection action.' : 'No hardship flag is recorded.');
  add('DATA-001', Boolean(account.lineage && account.lineage.observedAt), 'DATA_FRESHNESS_CHECK', 'Source lineage is present for the decision facts.');
  const blocked = results.filter(r => !r.passed);
  return { eligible: blocked.length === 0, actionType: blocked.length ? 'specialist_review' : 'outbound_call', ruleVersion: 'demo-policy-v1', ruleResults: results, requiresHumanReview: true, blockingReasons: blocked.map(r => r.reasonCode) };
}
function recommendationView(rec) {
  const account = accountFor(rec.accountId); const customer = customerFor(account.customerId); const rules = eligibility(account);
  return { ...rec, account: { id: account.id, product: account.product, overdueBalance: account.overdueBalance, dpd: account.dpd, status: account.status }, customer: { id: customer.id, name: customer.name }, eligibility: rules, dataFreshness: account.lineage, explanation: rules.eligible ? 'The eligible outbound action is suggested from validated account facts and a development-only demonstration score.' : 'No ordinary collection action is executable because mandatory rule checks failed. The case is routed or blocked.', decisionMemory: { featureSnapshot: account.features, featureVersion: 'demo-features-v1', modelVersion: rec.modelVersion, policyVersion: rules.ruleVersion } };
}
function accountSummary(account) { const customer = customerFor(account.customerId); const rec = state.recommendations.find(r => r.id === account.recommendationId); return { ...account, customer: { id: customer.id, name: customer.name }, eligibility: eligibility(account), recommendation: rec ? recommendationView(rec) : null }; }
function dashboard() { const accounts = state.accounts.filter(a => visibleAccount(a)); const eligible = accounts.filter(a => eligibility(a).eligible); return { kpis: [{ label: 'Eligible accounts', value: eligible.length, definition: 'Active assigned accounts passing all mandatory demo rules.' }, { label: 'Awaiting review', value: state.recommendations.filter(r => ['PENDING_REVIEW','ESCALATED'].includes(r.status)).length, definition: 'Recommendations requiring a human state transition.' }, { label: 'Hardship routing', value: accounts.filter(a => a.hardship).length, definition: 'Accounts with hardship handling required.' }, { label: 'Pending identities', value: state.identityReviews.filter(r => r.status === 'PENDING').length, definition: 'Probabilistic matches awaiting steward review.' }], overdueTotal: money(accounts.reduce((n, a) => n + a.overdueBalance, 0)), ptpDueSoon: accounts.filter(a => a.ptp && a.ptp.status === 'PENDING').length, recentPayments: state.payments.slice(0, 5), pipeline: { raw: 'substitute: fixture records', silver: 'healthy: deterministic normalization', golden: 'healthy: authorized read model', kafka: 'disabled', postgres: 'disabled', redis: 'disabled' }, dataQuality: accounts.filter(a => a.contactCount7d >= 4 || a.dnc || a.dispute).map(a => ({ accountId: a.id, issue: a.dnc ? 'DNC restriction' : a.dispute ? 'Open dispute' : 'Contact cap threshold reached', severity: 'HIGH' })) }; }
function copilot(question, customerId) {
  const q = String(question || '').trim(); const lower = q.toLowerCase();
  if (!q) return { kind: 'ambiguous', answer: 'Please provide a question about an authorized account, policy, or transcript.', evidence: [], uncertainty: 'Question is empty.' };
  if (/gender|marital|citizen|nationality|accent|vulnerab|household|newcomer|accessibility/.test(lower)) { audit('SECURITY_REFUSAL', customerId || 'unknown', 'Protected-attribute inference request refused.'); return { kind: 'refusal', answer: 'I cannot infer or use protected personal attributes for collections decisions.', evidence: [], refusalCode: 'PROTECTED_ATTRIBUTE_REQUEST' }; }
  if (/delete|update|insert|drop|alter|truncate|system prompt|secret|password/.test(lower)) { audit('SECURITY_REFUSAL', customerId || 'unknown', 'Unsafe or privileged copilot request refused.'); return { kind: 'refusal', answer: 'That request is outside the read-only, authorized copilot scope.', evidence: [], refusalCode: 'UNAUTHORIZED_OPERATION' }; }
  const accounts = state.accounts.filter(a => (!customerId || a.customerId === customerId) && visibleAccount(a));
  if (!accounts.length) return { kind: 'refusal', answer: 'No authorized account records were found for this request.', evidence: [], refusalCode: 'OBJECT_ACCESS_DENIED' };
  if (/policy|govern|restriction|dnc|dispute|hardship/.test(lower)) { const p = state.policies.find(p => p.status === 'ACTIVE_DEMO'); const chunks = p.chunks.filter(c => /dnc|dispute|hardship|policy|restriction/.test(`${c.topic} ${lower}`.toLowerCase())); const evidence = (chunks.length ? chunks : p.chunks).map(c => ({ policyId: p.id, version: p.version, chunkId: c.id, text: c.text })); return { kind: 'policy', answer: 'The active demonstration policy requires mandatory restrictions to be respected. An open dispute routes the account for specialist review, and a verified DNC blocks outbound contact.', evidence, citations: evidence.map(e => e.chunkId), policyVersion: p.version, uncertainty: 'This is synthetic demonstration policy evidence, not an official institutional policy.' }; }
  const a = accounts[0]; if (/overdue|balance|arrears/.test(lower)) return { kind: 'structured', answer: `${a.id} has an overdue balance of $${a.overdueBalance.toFixed(2)} with ${a.dpd} days past due.`, evidence: [{ sourceSystem: a.lineage.sourceSystem, sourceRecordId: a.lineage.sourceRecordId, field: 'overdueBalance', value: a.overdueBalance }, { sourceSystem: a.lineage.sourceSystem, sourceRecordId: a.lineage.sourceRecordId, field: 'dpd', value: a.dpd }], sqlProvenance: { view: 'authorized_account_summary', readOnly: true, dataAsOf: a.lineage.observedAt } };
  if (/payment/.test(lower)) { const payments = state.payments.filter(p => p.accountId === a.id); return { kind: 'structured', answer: `${payments.length} payment record(s) are available for ${a.id}; reconciled amount is $${payments.filter(p => p.status === 'RECONCILED').reduce((n,p) => n + p.amount, 0).toFixed(2)}.`, evidence: payments, sqlProvenance: { view: 'authorized_payment_history', readOnly: true, dataAsOf: a.lineage.observedAt } }; }
  if (/promise|ptp|due/.test(lower)) return { kind: 'structured', answer: a.ptp ? `The next promise for ${a.id} is $${a.ptp.amount.toFixed(2)} due ${a.ptp.dueDate}; status is ${a.ptp.status}.` : `No promise-to-pay is recorded for ${a.id}.`, evidence: a.ptp ? [a.ptp] : [], sqlProvenance: { view: 'authorized_promise_history', readOnly: true, dataAsOf: a.lineage.observedAt } };
  if (/recommend|evidence|why/.test(lower)) { const rec = state.recommendations.find(r => r.accountId === a.id); return rec ? { kind: 'structured', answer: recommendationView(rec).explanation, evidence: recommendationView(rec).topFeatures, link: `/customer/${a.customerId}`, uncertainty: 'Score is a deterministic development demonstration, not a trained or calibrated model.' } : { kind: 'ambiguous', answer: 'No recommendation is recorded for this account.', evidence: [] }; }
  if (/transcript|call|note/.test(lower)) { const calls = state.transcripts.filter(t => t.accountId === a.id); return { kind: 'transcript', answer: calls.length ? 'The following snippets are recorded or machine-extracted candidates; they are not independently verified facts.' : 'No authorized transcript is recorded.', evidence: calls }; }
  return { kind: 'ambiguous', answer: 'I can answer authorized questions about overdue balances, payments, promises, policies, recommendations, or transcript evidence. Please be more specific.', evidence: [] };
}

function normalizeIdentifier(kind, value) {
  const raw = String(value || '').trim();
  if (kind === 'email') return raw.toLowerCase();
  if (kind === 'phone') return raw.replace(/[^0-9+]/g, '').replace(/^00/, '+');
  if (kind === 'account') return raw.toUpperCase().replace(/\s+/g, '');
  return raw;
}
function exactIdentityMatch(payload) {
  const matches = [];
  for (const customer of state.customers) {
    const evidence = [];
    if (payload.email && normalizeIdentifier('email', payload.email) === normalizeIdentifier('email', customer.email)) evidence.push('normalized_email');
    if (payload.phone && normalizeIdentifier('phone', payload.phone) === normalizeIdentifier('phone', customer.phone)) evidence.push('normalized_phone');
    if (payload.accountId && state.accounts.some(a => a.id === normalizeIdentifier('account', payload.accountId) && a.customerId === customer.id)) evidence.push('account_reference');
    if (evidence.length) matches.push({ customerId: customer.id, matchType: 'exact', rule: 'exact-normalized-v1', evidence });
  }
  return matches;
}
function validateReadOnlyQuery(sql) {
  const text = String(sql || '').trim();
  const forbidden = /\b(insert|update|delete|drop|alter|truncate|create|grant|revoke|copy|execute)\b/i;
  const multiple = text.includes(';') && text.replace(/;\s*$/, '').includes(';');
  const approvedViews = ['authorized_account_summary', 'authorized_payment_history', 'authorized_promise_history'];
  const view = approvedViews.find(v => text.toLowerCase().includes(v));
  const valid = /^select\b/i.test(text) && !forbidden.test(text) && !multiple && Boolean(view);
  return { valid, readOnly: valid, view: view || null, reasons: valid ? [] : ['Only a single SELECT against an approved read-only view is accepted.'] };
}
function featureSnapshot(account) {
  const payments = state.payments.filter(p => p.accountId === account.id && p.status === 'RECONCILED');
  const calls = state.contacts.filter(c => c.accountId === account.id);
  return { entityKey: account.id, version: 'demo-features-v1', observedAt: account.lineage.observedAt, availableAt: account.lineage.ingestedAt, values: { days_past_due: account.dpd, overdue_balance: account.overdueBalance, recent_payment_count: payments.length, recent_payment_amount: money(payments.reduce((n,p)=>n+p.amount,0)), historical_ptp_adherence: account.features.historicalPtpAdherence, missed_ptp_count: account.ptp?.status === 'BROKEN' ? 1 : 0, days_since_last_payment: account.features.daysSinceLastPayment, contact_count_in_window: calls.length, dispute_open: account.dispute, hardship_review_required: account.hardship }, missing: Object.entries(account.features).filter(([,v])=>v === null || v === undefined).map(([k])=>k), lineage: account.lineage };
}
function experimentMetrics() {
  const accounts = state.accounts.filter(a => a.overdueBalance > 0);
  const maturePromises = accounts.map(a => a.ptp).filter(Boolean).filter(p => p.status !== 'PENDING');
  const kept = maturePromises.filter(p => p.status === 'KEPT').length;
  const cures = accounts.filter(a => a.overdueBalance === 0).length;
  const contacts = state.contacts.filter(c => accounts.some(a => a.id === c.accountId)).length;
  return { cohortSize: accounts.length, cure30d: { numerator: cures, denominator: accounts.length, value: accounts.length ? cures / accounts.length : null, status: 'DEMO_FIXTURE_NOT_MATURE' }, ptpAdherence: { numerator: kept, denominator: maturePromises.length, value: maturePromises.length ? kept / maturePromises.length : null, status: 'DEMO_FIXTURE_NOT_MATURE' }, contactsPerCure: { numerator: contacts, denominator: cures, value: cures ? contacts / cures : null, status: 'DEMO_FIXTURE_NOT_MATURE' } };
}
function assignmentPlan() {
  const agents = state.users.filter(u => u.role === 'collections_agent' || u.role === 'team_lead');
  const eligible = state.accounts.filter(a => visibleAccount(a) && eligibility(a).eligible);
  const assigned = eligible.map((a, i) => ({ accountId: a.id, agentId: agents[i % Math.max(1, agents.length)]?.id || null, reason: 'Eligible after deterministic rules; round-robin development allocation.', constraints: ['mandatory_rules_passed', 'agent_capacity_demo'] }));
  return { status: 'DEVELOPMENT_ADAPTER', objective: 'Maximize eligible account coverage under demo capacity', feasible: true, assigned, unassigned: [], solver: 'local-deterministic-substitute', constraints: ['DNC', 'contact_cap', 'hardship', 'dispute', 'agent_capacity'] };
}

async function route(req, res) {
  const url = new URL(req.url, `http://${req.headers.host || 'localhost'}`); const p = url.pathname; const method = req.method;
  if (method === 'GET' && p === '/health') return json(res, 200, { status: 'ok' });
  if (method === 'GET' && p === '/ready') return json(res, 200, { status: 'ready', dataFile: DATA_FILE, demo: true });
  if (method === 'GET' && p === '/api/v1/meta') return json(res, 200, ok({ status: 'local-demo', capabilities: { structuredCopilot: true, policyEvidence: true, deterministicRules: true, simulatedExecution: true, postgres: false, kafka: false, redis: false, llm: false, trainedModel: false } }));
  if (!p.startsWith('/api/v1/')) return serveStatic(res, p);
  if (method === 'GET' && p === '/api/v1/dashboard') return json(res, 200, ok(dashboard()));
  if (method === 'GET' && p === '/api/v1/customers') return json(res, 200, ok({ rows: state.customers.filter(c => state.accounts.some(a => a.customerId === c.id && visibleAccount(a))).map(c => ({ ...c, accountCount: state.accounts.filter(a => a.customerId === c.id).length })) }));
  if (method === 'GET' && p === '/api/v1/accounts') return json(res, 200, ok({ rows: state.accounts.filter(a => visibleAccount(a)).map(accountSummary) }));
  if (method === 'GET' && p === '/api/v1/payments') return json(res, 200, ok({ rows: state.payments.filter(x => visibleAccount(accountFor(x.accountId))) }));
  if (method === 'GET' && p === '/api/v1/promises') return json(res, 200, ok({ rows: state.accounts.filter(a => visibleAccount(a) && a.ptp).map(a => ({ ...a.ptp, accountId: a.id, customerId: a.customerId })) }));
  if (method === 'GET' && p === '/api/v1/contacts') return json(res, 200, ok({ rows: state.contacts.filter(x => visibleAccount(accountFor(x.accountId))) }));
  if (method === 'GET' && p === '/api/v1/transcripts') return json(res, 200, ok({ rows: state.transcripts.filter(x => visibleAccount(accountFor(x.accountId))) }));
  if (method === 'GET' && p === '/api/v1/hardship') return json(res, 200, ok({ rows: state.accounts.filter(a => a.hardship && visibleAccount(a)).map(a => ({ id: `hardship-${a.id}`, accountId: a.id, customerId: a.customerId, status: 'REVIEW_REQUIRED', source: 'synthetic-hardship-fixture', specialistRequired: true })) }));
  if (method === 'GET' && p === '/api/v1/disputes') return json(res, 200, ok({ rows: state.accounts.filter(a => a.dispute && visibleAccount(a)).map(a => ({ id: `dispute-${a.id}`, accountId: a.id, customerId: a.customerId, status: 'OPEN', source: 'synthetic-dispute-fixture', collectionActionBlocked: true })) }));
  if (method === 'GET' && p === '/api/v1/users') return json(res, 200, ok({ rows: state.users.map(u => ({ id: u.id, name: u.name, role: u.role, assignmentCount: u.assignedAccountIds.length })) }));
  if (method === 'GET' && p === '/api/v1/source-systems') return json(res, 200, ok({ rows: ['loan-servicing', 'card-ledger', 'crm', 'payment-ledger', 'collections', 'hardship', 'dispute'].map(name => ({ name, status: 'DEMO_ADAPTER', lastRefresh: state.meta.snapshotDate })) }));
  if (method === 'POST' && p === '/api/v1/ingestion/payments') { const body = await readBody(req); if (!body.eventId || !body.accountId || body.amount === undefined) return sendError(res, 422, 'VALIDATION_ERROR', 'eventId, accountId, and amount are required.'); if (!accountFor(body.accountId)) return sendError(res, 404, 'NOT_FOUND', 'Account not found.'); const duplicate = state.payments.find(x => x.eventId === body.eventId); if (duplicate) return json(res, 200, ok({ payment: duplicate, duplicate: true, processing: 'idempotent-no-op' })); const payment = { id: id('pay'), eventId: body.eventId, accountId: body.accountId, amount: money(body.amount), status: body.status || 'RECONCILED', date: body.date || now().slice(0,10), sourceSystem: body.sourceSystem || 'local-event-adapter', ingestedAt: now() }; state.payments.unshift(payment); audit('PAYMENT_INGESTED', payment.id, `Payment event ${body.eventId} ingested once.`); return json(res, 201, ok({ payment, duplicate: false })); }
  if (method === 'POST' && p === '/api/v1/identity/match') { const body = await readBody(req); const matches = exactIdentityMatch(body); audit('IDENTITY_MATCH_PROPOSED', body.sourceRecordId || 'unknown', `Exact identity matching returned ${matches.length} candidate(s).`); return json(res, 200, ok({ strategy: 'exact-normalized-v1', matches, requiresReview: false })); }
  if (method === 'POST' && p === '/api/v1/copilot/sql/validate') { const body = await readBody(req); const validation = validateReadOnlyQuery(body.sql); if (!validation.valid) audit('SQL_REJECTED', 'copilot', 'Read-only SQL validation rejected a query.'); return json(res, validation.valid ? 200 : 422, ok(validation)); }
  if (method === 'GET' && p === '/api/v1/features/registry') return json(res, 200, ok({ version: 'demo-features-v1', features: ['days_past_due','overdue_balance','recent_payment_count','recent_payment_amount','historical_ptp_adherence','missed_ptp_count','days_since_last_payment','contact_count_in_window','dispute_open','hardship_review_required'].map(name => ({ name, entityKey: 'account.id', version: 'demo-features-v1', owner: 'local-demo', leakageSafe: true, sourceLineage: 'account/payment/contact fixtures' })) }));
  const featureMatch = p.match(/^\/api\/v1\/features\/([^/]+)$/); if (method === 'GET' && featureMatch) { const a = accountFor(featureMatch[1]); if (!a || !visibleAccount(a)) return sendError(res, 404, 'NOT_FOUND', 'Feature entity not found.'); return json(res, 200, ok({ snapshot: featureSnapshot(a) })); }
  if (method === 'GET' && p === '/api/v1/assignments') return json(res, 200, ok(assignmentPlan()));
  if (method === 'GET' && p === '/api/v1/models') return json(res, 200, ok({ rows: [{ id: 'demo-untrained-v1', target: '30-day cure demonstration', status: 'DEVELOPMENT_DEMONSTRATION', calibrated: false, trained: false, explanation: 'Deterministic fixture score; no production performance claim.' }, { id: 'demo-ptp-break-v1', target: 'PTP break demonstration', status: 'DESIGN_ONLY', calibrated: false, trained: false }] }));
  if (method === 'GET' && p === '/api/v1/experiments') return json(res, 200, ok({ experiment: { id: 'exp-demo-001', status: 'DESIGN_ONLY', treatment: 'Copilot-assisted synthetic cohort', control: 'Manual synthetic cohort', window: 'Not started', metrics: experimentMetrics(), note: 'Metrics are calculated from a tiny synthetic fixture and are not mature or causal evidence.' } }));
  if (method === 'GET' && p === '/api/v1/collections/queue') { const q = url.searchParams; let rows = state.accounts.filter(a => visibleAccount(a)); if (q.get('eligibility') === 'eligible') rows = rows.filter(a => eligibility(a).eligible); if (q.get('hardship') === 'yes') rows = rows.filter(a => a.hardship); if (q.get('search')) { const s = q.get('search').toLowerCase(); rows = rows.filter(a => a.id.includes(s) || customerFor(a.customerId).name.toLowerCase().includes(s)); } return json(res, 200, ok({ rows: rows.map(accountSummary), total: rows.length, page: 1, pageSize: rows.length })); }
  const customerMatch = p.match(/^\/api\/v1\/customers\/([^/]+)$/); if (method === 'GET' && customerMatch) { const c = customerFor(customerMatch[1]); if (!c) return sendError(res, 404, 'NOT_FOUND', 'Customer not found.'); const accounts = state.accounts.filter(a => a.customerId === c.id && visibleAccount(a)); return json(res, 200, ok({ customer: c, accounts: accounts.map(accountSummary), payments: state.payments.filter(x => accounts.some(a => a.id === x.accountId)), contacts: state.contacts.filter(x => accounts.some(a => a.id === x.accountId)), transcripts: state.transcripts.filter(x => accounts.some(a => a.id === x.accountId)), audit: state.audit.filter(x => accounts.some(a => a.id === x.entityId || x.entityId === c.id)).slice(0, 15) })); }
  if (method === 'GET' && p === '/api/v1/recommendations') return json(res, 200, ok({ rows: state.recommendations.filter(r => visibleAccount(accountFor(r.accountId))).map(recommendationView) }));
  const recMatch = p.match(/^\/api\/v1\/recommendations\/([^/]+)\/transition$/); if (method === 'POST' && recMatch) { const body = await readBody(req); const rec = state.recommendations.find(r => r.id === recMatch[1]); if (!rec) return sendError(res, 404, 'NOT_FOUND', 'Recommendation not found.'); const allowed = { PENDING_REVIEW: ['APPROVED','EDITED','REJECTED','ESCALATED'], EDITED: ['APPROVED','REJECTED'], ESCALATED: ['APPROVED','REJECTED'], APPROVED: ['EXECUTED'] }; const next = body.status; if (!allowed[rec.status]?.includes(next)) return sendError(res, 409, 'INVALID_TRANSITION', `Cannot transition ${rec.status} to ${next}.`); const view = recommendationView(rec); if (next === 'APPROVED' && !view.eligibility.eligible) return sendError(res, 422, 'INELIGIBLE_ACTION', 'Mandatory eligibility checks failed; approval is blocked.', { rules: view.eligibility }); if (next === 'EXECUTED' && rec.status !== 'APPROVED') return sendError(res, 409, 'STALE_APPROVAL', 'Execution requires the exact approved recommendation state.'); rec.status = next; rec.reviewReason = body.reason || rec.reviewReason; audit(`RECOMMENDATION_${next}`, rec.id, `Recommendation ${rec.id} moved to ${next}.`, { reason: body.reason || null }); return json(res, 200, ok({ recommendation: recommendationView(rec) })); }
  if (method === 'POST' && p === '/api/v1/copilot') { const body = await readBody(req); const result = copilot(body.question, body.customerId); audit('COPILOT_QUERY', body.customerId || 'authorized-scope', `Copilot classified request as ${result.kind}.`); return json(res, 200, ok(result)); }
  if (method === 'GET' && p === '/api/v1/policies') return json(res, 200, ok({ rows: state.policies }));
  if (method === 'GET' && p === '/api/v1/identity/reviews') return json(res, 200, ok({ rows: state.identityReviews }));
  const idMatch = p.match(/^\/api\/v1\/identity\/reviews\/([^/]+)\/decision$/); if (method === 'POST' && idMatch) { if (user().role !== 'data_steward' && user().role !== 'administrator') return sendError(res, 403, 'FORBIDDEN', 'Only an authorized data steward can resolve identity reviews.'); const body = await readBody(req); const review = state.identityReviews.find(r => r.id === idMatch[1]); if (!review) return sendError(res, 404, 'NOT_FOUND', 'Identity review not found.'); if (!['APPROVED','REJECTED','DEFERRED'].includes(body.status)) return sendError(res, 422, 'VALIDATION_ERROR', 'Decision must be APPROVED, REJECTED, or DEFERRED.'); review.status = body.status; review.reason = body.reason || null; audit(`IDENTITY_${body.status}`, review.id, `Identity review ${review.id} resolved.`); return json(res, 200, ok({ review })); }
  if (method === 'GET' && p === '/api/v1/monitoring') return json(res, 200, ok({ featureFreshness: state.accounts.map(a => ({ accountId: a.id, featureVersion: 'demo-features-v1', observedAt: a.lineage.observedAt, freshness: 'available' })), model: { version: 'demo-untrained-v1', status: 'DEVELOPMENT_DEMONSTRATION', calibrated: false, measuredMetrics: false }, adapters: { kafka: 'DISABLED', spark: 'DISABLED', airflow: 'DISABLED', postgres: 'DISABLED', redis: 'DISABLED', splink: 'DEMONSTRATION_THRESHOLD_ONLY', pgvector: 'DISABLED', orTools: 'DISABLED' }, skew: [] }));
  if (method === 'GET' && p === '/api/v1/audit') return json(res, 200, ok({ rows: state.audit.slice(0, 100) }));
  if (method === 'GET' && p === '/api/v1/experiments') return json(res, 200, ok({ experiment: { id: 'exp-demo-001', status: 'DESIGN_ONLY', treatment: 'Copilot-assisted synthetic cohort', control: 'Manual synthetic cohort', window: 'Not started', metrics: { cure30d: 'Not measured', ptpAdherence: 'Not measured', contactsPerCure: 'Not measured' }, note: 'No causal or performance claim is made.' } }));
  return sendError(res, 404, 'NOT_FOUND', 'API route not found.');
}
function serveStatic(res, pathname) { const safe = pathname === '/' ? '/index.html' : pathname; const file = path.normalize(path.join(PUBLIC, safe)); if (!file.startsWith(PUBLIC)) return sendError(res, 400, 'BAD_PATH', 'Invalid path.'); fs.readFile(file, (err, data) => { if (err) return fs.readFile(path.join(PUBLIC, 'index.html'), (e, d) => { if (e) return sendError(res, 404, 'NOT_FOUND', 'File not found.'); res.writeHead(200, { 'content-type': 'text/html; charset=utf-8' }); res.end(d); }); const ext = path.extname(file); const type = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json' }[ext] || 'application/octet-stream'; res.writeHead(200, { 'content-type': type }); res.end(data); }); }
const server = http.createServer((req, res) => route(req, res).catch(e => sendError(res, e.message === 'invalid_json' ? 400 : 500, e.message === 'invalid_json' ? 'INVALID_JSON' : 'INTERNAL_ERROR', e.message === 'invalid_json' ? 'Request body must be valid JSON.' : 'The local service encountered an unexpected error.')));
server.listen(PORT, '127.0.0.1', () => console.log(`Agentic Collections Copilot local demo listening at http://127.0.0.1:${PORT}`));
