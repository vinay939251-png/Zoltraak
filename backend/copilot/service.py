"""
Layer 2 Natural-Language Copilot Service.
Integrates Google Gemini with deterministic RAG retrieval, read-only SQL provenance,
and strict governance refusal guardrails.
"""
import os
import re
import time
from django.conf import settings
from django.utils import timezone
from accounts.models import Account
from customers.models import Customer
from payments.models import Payment
from promises.models import PromiseToPay
from policies.models import PolicyDocument, PolicyChunk
from audit.utils import log_audit
from copilot.models import CopilotSession, CopilotQuery

# Initialize Gemini if key is provided
_gemini_client_configured = False
try:
    import google.generativeai as genai
    gemini_key = getattr(settings, 'GEMINI_API_KEY', '') or os.getenv('GEMINI_API_KEY', '')
    if gemini_key:
        genai.configure(api_key=gemini_key)
        _gemini_client_configured = True
except Exception:
    _gemini_client_configured = False


class CopilotService:

    PROTECTED_ATTR_PATTERN = re.compile(
        r'\b(gender|sex|marital|spouse|married|single|divorced|citizen|nationality|ethnic|race|accent|vulnerab|household|newcomer|immigrant|accessibility|disability)\b',
        re.IGNORECASE
    )

    UNSAFE_SQL_PATTERN = re.compile(
        r'\b(drop|delete|update|insert|alter|truncate|grant|revoke|exec|execute|union\s+select|benchmark|pg_sleep|sleep|system\s*prompt|secret|api_key|password)\b',
        re.IGNORECASE
    )

    @classmethod
    def process_query(cls, query_text, user, customer_id=None, session_id=None):
        start_time = time.time()
        q = (query_text or '').strip()
        lower = q.lower()

        # Get or create session
        if session_id:
            session = CopilotSession.objects.filter(id=session_id).first()
        else:
            session = None
        if not session:
            customer_obj = Customer.objects.filter(id=customer_id).first() if customer_id else None
            session = CopilotSession.objects.create(
                user=user,
                customer=customer_obj,
                title=f"Consultation: {q[:30]}..." if q else "General Inquiries"
            )

        # 1. Check for empty query
        if not q:
            result = {
                'kind': CopilotQuery.ResponseKind.AMBIGUOUS,
                'answer': 'Please provide a specific query regarding an authorized account, repayment policy, or transcript record.',
                'evidence': [],
                'citations': [],
                'sql_provenance': {},
                'uncertainty': 'Query is empty.',
                'confidence': 0.0
            }
            return cls._save_and_return(session, user, q, result, start_time)

        # 2. Check for Protected Attributes (Section 8 Governance Refusal)
        if cls.PROTECTED_ATTR_PATTERN.search(lower):
            log_audit(
                'SECURITY_REFUSAL',
                customer_id or 'global',
                'Protected personal attribute inference refused by governance policy.',
                actor=user,
                details={'query': q, 'reason': 'PROTECTED_ATTRIBUTE_REQUEST'}
            )
            result = {
                'kind': CopilotQuery.ResponseKind.REFUSAL,
                'answer': 'I cannot analyze, infer, or incorporate protected personal attributes (such as gender, citizenship, marital status, or household structure) into collections recommendations or decisions.',
                'evidence': [],
                'citations': [],
                'sql_provenance': {},
                'refusal_code': 'PROTECTED_ATTRIBUTE_REQUEST',
                'confidence': 1.0
            }
            return cls._save_and_return(session, user, q, result, start_time)

        # 3. Check for Unsafe / Injection attempts
        if cls.UNSAFE_SQL_PATTERN.search(lower):
            log_audit(
                'SECURITY_REFUSAL',
                customer_id or 'global',
                'Unsafe SQL or system instruction query refused by security boundary.',
                actor=user,
                details={'query': q, 'reason': 'UNAUTHORIZED_OPERATION'}
            )
            result = {
                'kind': CopilotQuery.ResponseKind.REFUSAL,
                'answer': 'This operation was refused. The collections copilot only performs read-only, authorized analytical operations and cannot modify data or reveal system internals.',
                'evidence': [],
                'citations': [],
                'sql_provenance': {},
                'refusal_code': 'UNAUTHORIZED_OPERATION',
                'confidence': 1.0
            }
            return cls._save_and_return(session, user, q, result, start_time)

        # 4. Check object authorization
        accessible_accounts = Account.objects.all()
        if user.role == 'collections_agent':
            accessible_accounts = accessible_accounts.filter(assigned_agent=user)

        if customer_id:
            accessible_accounts = accessible_accounts.filter(customer_id=customer_id)

        target_account = accessible_accounts.first()

        # 5. Policy / RAG inquiries
        if any(term in lower for term in ['policy', 'rule', 'cap', 'limit', 'frequency', 'fcac', 'dnc', 'hardship', 'dispute', 'guideline', 'regulation', 'contact restriction', 'consent', 'hours', 'statute', 'compliance', 'outreach', 'call', 'solicitation']):
            from policies.vector_search import vector_search
            search_res = vector_search.search_hybrid(q, top_k=3)
            relevant_chunks = search_res["chunks"]
            citations = search_res["citations"]
            evidence = search_res["evidence"]

            summary = (
                "Under Maple Bank Demonstration Collections Policy (v2.1), mandatory regulatory constraints strictly apply: "
                "1. Verified Do-Not-Contact (DNC) flags prohibit any outbound solicitation. "
                "2. Customer contacts are capped at a maximum of 3 attempted communications per 7-day rolling window. "
                "3. Accounts with active disputes or hardship enrollments require transfer to specialized handlers."
            )

            # Optional Gemini enhancement grounded in retrieved chunks
            if _gemini_client_configured and relevant_chunks:
                try:
                    model = genai.GenerativeModel('gemini-3.8-flash')
                    prompt = (
                        f"You are an enterprise Collections Copilot. Ground your answer strictly in these regulatory policy excerpts:\n"
                        f"{[c.text for c in relevant_chunks]}\n\n"
                        f"Question: {q}\n"
                        f"Provide a concise, direct, professional answer summarizing the policy rule and citing any caps or restrictions."
                    )
                    resp = model.generate_content(prompt, request_options={'timeout': 10})
                    if resp and resp.text:
                        summary = resp.text.strip()
                except Exception:
                    pass

            result = {
                'kind': CopilotQuery.ResponseKind.POLICY,
                'answer': summary,
                'evidence': evidence,
                'citations': citations,
                'sql_provenance': {},
                'uncertainty': 'Grounded in institutional compliance policy records; not formal legal advice.',
                'retrieval_method': search_res.get("method", "HYBRID"),
                'confidence': 0.96
            }
            return cls._save_and_return(session, user, q, result, start_time)

        # 6. Structured Financial / Account queries
        if not target_account:
            result = {
                'kind': CopilotQuery.ResponseKind.REFUSAL,
                'answer': 'No authorized customer account records were found for this query context.',
                'evidence': [],
                'citations': [],
                'sql_provenance': {},
                'refusal_code': 'OBJECT_ACCESS_DENIED',
                'confidence': 1.0
            }
            return cls._save_and_return(session, user, q, result, start_time)

        # Balance / Arrears / DPD
        if any(term in lower for term in ['balance', 'overdue', 'arrears', 'dpd', 'days past due']):
            sql = f"SELECT id, product, overdue_balance, balance, dpd, status FROM account WHERE id = '{target_account.id}'"
            answer = f"Account {target_account.id} ({target_account.product}) has an overdue balance of ${target_account.overdue_balance:,.2f} with {target_account.dpd} days past due (Total balance: ${target_account.balance:,.2f})."
            evidence = [
                {'field': 'overdue_balance', 'value': float(target_account.overdue_balance), 'source_system': target_account.source_system},
                {'field': 'dpd', 'value': target_account.dpd, 'source_system': target_account.source_system},
                {'field': 'product', 'value': target_account.product, 'source_system': target_account.source_system}
            ]
            result = {
                'kind': CopilotQuery.ResponseKind.STRUCTURED,
                'answer': answer,
                'evidence': evidence,
                'citations': [],
                'sql_provenance': {'query': sql, 'view': 'authorized_account_360', 'read_only': True, 'data_as_of': target_account.observed_at.isoformat() if target_account.observed_at else None},
                'confidence': 1.0
            }
            return cls._save_and_return(session, user, q, result, start_time)

        # Payments
        if 'payment' in lower:
            payments = Payment.objects.filter(account=target_account).order_by('-date')[:5]
            sql = f"SELECT id, amount, status, date FROM payment WHERE account_id = '{target_account.id}' ORDER BY date DESC"
            p_list = [{'id': p.id, 'amount': float(p.amount), 'status': p.status, 'date': str(p.date)} for p in payments]
            total_reconciled = sum(p['amount'] for p in p_list if p['status'] == 'RECONCILED')
            answer = f"Found {len(p_list)} recent payment record(s) for account {target_account.id}. Total reconciled: ${total_reconciled:,.2f}."
            result = {
                'kind': CopilotQuery.ResponseKind.STRUCTURED,
                'answer': answer,
                'evidence': p_list,
                'citations': [],
                'sql_provenance': {'query': sql, 'view': 'authorized_payment_history', 'read_only': True, 'data_as_of': target_account.observed_at.isoformat() if target_account.observed_at else None},
                'confidence': 1.0
            }
            return cls._save_and_return(session, user, q, result, start_time)

        # Promises to Pay
        if any(term in lower for term in ['promise', 'ptp']):
            ptps = PromiseToPay.objects.filter(account=target_account).order_by('-due_date')
            sql = f"SELECT id, amount, due_date, status FROM promise_to_pay WHERE account_id = '{target_account.id}'"
            ptp_list = [{'id': p.id, 'amount': float(p.amount), 'due_date': str(p.due_date), 'status': p.status} for p in ptps]
            if ptp_list:
                latest = ptp_list[0]
                answer = f"Account {target_account.id} has a Promise-to-Pay for ${latest['amount']:,.2f} due on {latest['due_date']} (Status: {latest['status']})."
            else:
                answer = f"No active Promise-to-Pay records found for account {target_account.id}."
            result = {
                'kind': CopilotQuery.ResponseKind.STRUCTURED,
                'answer': answer,
                'evidence': ptp_list,
                'citations': [],
                'sql_provenance': {'query': sql, 'view': 'authorized_ptp_ledger', 'read_only': True, 'data_as_of': target_account.observed_at.isoformat() if target_account.observed_at else None},
                'confidence': 1.0
            }
            return cls._save_and_return(session, user, q, result, start_time)

        # General inquiry with Gemini or fallback
        general_answer = f"Account {target_account.id} is currently {target_account.status} with {target_account.dpd} DPD and an overdue balance of ${target_account.overdue_balance:,.2f}."
        if _gemini_client_configured:
            try:
                model = genai.GenerativeModel('gemini-3.8-flash')
                prompt = (
                    f"You are an enterprise collections decision-support copilot. Answer concisely based on this verified data:\n"
                    f"Customer: {target_account.customer.name}\n"
                    f"Account: {target_account.id} ({target_account.product})\n"
                    f"Balance: ${target_account.balance}, Overdue: ${target_account.overdue_balance}, DPD: {target_account.dpd}\n"
                    f"Question: {q}"
                )
                resp = model.generate_content(prompt, request_options={'timeout': 10})
                if resp and resp.text:
                    general_answer = resp.text.strip()
            except Exception:
                pass

        result = {
            'kind': CopilotQuery.ResponseKind.STRUCTURED,
            'answer': general_answer,
            'evidence': [{'account_id': target_account.id, 'customer': target_account.customer.name, 'dpd': target_account.dpd}],
            'citations': [],
            'sql_provenance': {'view': 'authorized_account_summary', 'read_only': True},
            'confidence': 0.9
        }
        return cls._save_and_return(session, user, q, result, start_time)

    @classmethod
    def _save_and_return(cls, session, user, query_text, result, start_time):
        latency = int((time.time() - start_time) * 1000)
        cq = CopilotQuery.objects.create(
            session=session,
            user=user,
            query_text=query_text,
            response_kind=result['kind'],
            answer_text=result['answer'],
            sql_query=result.get('sql_provenance', {}).get('query', ''),
            sql_provenance=result.get('sql_provenance', {}),
            citations=result.get('citations', []),
            evidence=result.get('evidence', []),
            refusal_code=result.get('refusal_code', ''),
            uncertainty_note=result.get('uncertainty', ''),
            confidence_score=result.get('confidence', 1.0),
            latency_ms=latency
        )
        return {
            'query_id': cq.id,
            'session_id': session.id,
            'kind': result['kind'],
            'answer': result['answer'],
            'evidence': result.get('evidence', []),
            'citations': result.get('citations', []),
            'sql_provenance': result.get('sql_provenance', {}),
            'refusal_code': result.get('refusal_code', None),
            'uncertainty': result.get('uncertainty', None),
            'confidence': result.get('confidence', 1.0),
            'latency_ms': latency,
            'timestamp': cq.created_at.isoformat()
        }
