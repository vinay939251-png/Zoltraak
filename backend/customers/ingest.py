"""
Raw Data Ingestion & Entity Separation Engine.
Disambiguates incoming unstructured or semi-structured data across 10 Golden Customers,
separates attributes into domain ledgers (Payments, PTPs, Contacts, Whisper Signals, Regulatory Holds),
and isolates unrelated records in the Dead Letter Queue (DLQ).
"""
import re
import uuid
from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status

from customers.models import Customer, CustomerIdentity
from accounts.models import Account
from payments.models import Payment
from promises.models import PromiseToPay
from calls.models import CollectionContact, CallTranscript, HardshipCase, Dispute
from identity.models import IdentityMatchCandidate
from audit.utils import log_audit


class IngestRawDataView(APIView):
    """
    POST /api/v1/customers/ingest-raw/
    Accepts:
    {
      "raw_text": "string with multi-entity notes, payments, calls, or disputes",
      OR
      "records": [
         {"customer_hint": "...", "account_id": "...", "type": "payment|ptp|contact|transcript|dispute|hardship", "amount": 500, "text": "..."}
      ]
    }
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        raw_text = request.data.get('raw_text', '')
        raw_csv = request.data.get('raw_csv', '')
        records = request.data.get('records', [])
        uploaded_file = request.FILES.get('file')

        if uploaded_file:
            raw_csv = uploaded_file.read().decode('utf-8', errors='ignore')

        if not raw_text and not records and not raw_csv:
            return Response(
                {"error": "Please provide 'raw_csv', 'raw_text', or 'records' array to ingest and separate."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Parse CSV or unstructured text
        if raw_csv and not records:
            records = self._parse_csv(raw_csv)
        elif raw_text and not records:
            if ',' in raw_text and '\n' in raw_text and any(h in raw_text.lower() for h in ['customer', 'amount', 'account', 'phone', 'event_type']):
                records = self._parse_csv(raw_text)
            else:
                records = self._parse_unstructured_text(raw_text)

        all_customers = list(Customer.objects.prefetch_related('accounts', 'identities').all())
        
        separated_events = []
        quarantined_records = []
        steward_candidates = []
        affected_customers = set()

        for rec in records:
            matched_customer, confidence, match_reason = self._resolve_entity(rec, all_customers)

            if not matched_customer or confidence < 0.60:
                # UNRELATED / UNMATCHED -> Route to Dead Letter Queue (DLQ)
                quarantined_records.append({
                    "raw_record": rec,
                    "confidence": round(confidence, 2),
                    "reason": f"No Golden Customer match meeting 0.60 confidence threshold ({match_reason}). Quarantined to Dead Letter Queue.",
                    "status": "DLQ_QUARANTINED"
                })
                continue

            if 0.60 <= confidence < 0.85:
                # AMBIGUOUS -> Create Data Steward Review Candidate
                cand = IdentityMatchCandidate.objects.create(
                    customer=matched_customer,
                    source_system=rec.get('source_system', 'Raw-Ingest-Stream'),
                    source_record_id=rec.get('account_id') or rec.get('id') or f"RAW-{uuid.uuid4().hex[:6]}",
                    score=round(confidence, 2),
                    status=IdentityMatchCandidate.Status.PENDING,
                    evidence=[{"field": "raw_content", "matched_reason": match_reason, "hint": rec.get('customer_hint') or rec.get('name')}],
                    reason=f"Ambiguous record linkage: {match_reason}. Awaiting steward confirmation before merging."
                )
                steward_candidates.append({
                    "candidate_id": cand.id,
                    "target_customer": matched_customer.name,
                    "target_id": matched_customer.id,
                    "confidence": round(confidence, 2),
                    "reason": match_reason
                })
                continue

            # CONFIDENT MATCH (>= 0.85) -> Separate into Domain Ledgers
            primary_account = self._get_target_account(matched_customer, rec)
            domains_affected = []

            # 1. Payment domain
            amount = rec.get('amount')
            is_payment = rec.get('type') == 'payment' or ('payment' in str(rec.get('text', '')).lower() and amount)
            if is_payment and amount and primary_account:
                dec_amount = Decimal(str(amount))
                pay = Payment.objects.create(
                    event_id=f"PAY-RAW-{uuid.uuid4().hex[:8].upper()}",
                    account=primary_account,
                    amount=dec_amount,
                    status=Payment.Status.RECONCILED,
                    date=timezone.now().date(),
                    source_system=rec.get('source_system', 'Automated-Clearing-Ingest')
                )
                # Deduct balance & overdue balance
                primary_account.overdue_balance = max(Decimal('0.00'), primary_account.overdue_balance - dec_amount)
                primary_account.balance = max(Decimal('0.00'), primary_account.balance - dec_amount)
                primary_account.recent_payment_count += 1
                primary_account.recent_payment_amount += dec_amount
                primary_account.days_since_last_payment = 0
                primary_account.save()

                # Reconcile any open PTP
                open_ptps = PromiseToPay.objects.filter(account=primary_account, status=PromiseToPay.Status.PENDING)
                for ptp in open_ptps:
                    if dec_amount >= ptp.amount * Decimal('0.9'):
                        ptp.status = PromiseToPay.Status.KEPT
                        ptp.save()

                domains_affected.append(f"PAYMENT: Reconciled {dec_amount} CAD against {primary_account.id}")

            # 2. Promise to Pay (PTP) domain
            if rec.get('type') == 'ptp' or 'promise to pay' in str(rec.get('text', '')).lower():
                ptp_amt = Decimal(str(rec.get('amount') or primary_account.overdue_balance or '500.00'))
                due_dt = rec.get('due_date') or (timezone.now() + timedelta(days=7)).date()
                ptp = PromiseToPay.objects.create(
                    account=primary_account,
                    amount=ptp_amt,
                    due_date=due_dt,
                    status=PromiseToPay.Status.PENDING,
                    source_system='Raw-Ingest-Stream'
                )
                domains_affected.append(f"PTP: Logged commitment of {ptp_amt} CAD due {due_dt}")

            # 3. Outreach / Contact domain
            is_contact = rec.get('type') == 'contact' or any(k in str(rec.get('text', '')).lower() for k in ['call', 'voicemail', 'dialer', 'sms sent', 'contacted'])
            if is_contact and primary_account:
                channel = rec.get('channel', 'phone').lower()
                if channel not in ['phone', 'email', 'sms', 'letter']:
                    channel = 'phone'
                CollectionContact.objects.create(
                    account=primary_account,
                    date=timezone.now().date(),
                    channel=channel,
                    outcome=rec.get('outcome') or rec.get('text', 'Outreach attempt logged from incoming stream')[:90],
                    source_system=rec.get('source_system', 'Dialer-Ingest')
                )
                primary_account.contact_count_7d += 1
                primary_account.save()
                domains_affected.append(f"CONTACT: Logged {channel.upper()} touch; 7-day touch count is now {primary_account.contact_count_7d}/3")

            # 4. Transcripts & Whisper Signal Extraction
            text_snippet = rec.get('text') or rec.get('transcript') or ''
            if text_snippet and primary_account:
                signals = self._extract_signals(text_snippet)
                CallTranscript.objects.create(
                    account=primary_account,
                    language=rec.get('language', 'en'),
                    text=text_snippet,
                    signals=signals,
                    source_system=rec.get('source_system', 'Whisper-Adapter')
                )
                signal_names = [s['signal'] for s in signals]
                domains_affected.append(f"TRANSCRIPT: Extracted Whisper signals [{', '.join(signal_names) or 'none'}]")

                # Cascade regulatory flags if severe signals detected
                if 'dispute_signal' in signal_names:
                    primary_account.dispute = True
                    primary_account.save()
                    Dispute.objects.get_or_create(
                        account=primary_account,
                        status=Dispute.Status.UNDER_INVESTIGATION,
                        defaults={'source': 'Raw-Signal-Ingest', 'collection_action_blocked': True, 'notes': text_snippet[:200]}
                    )
                    domains_affected.append("REGULATORY: TRIP WIRE TRIPPED -> Active Dispute hold initiated.")

                if 'hardship_indicator' in signal_names and ('layoff' in text_snippet.lower() or 'medical' in text_snippet.lower() or 'emergency' in text_snippet.lower()):
                    primary_account.hardship = True
                    primary_account.save()
                    HardshipCase.objects.get_or_create(
                        account=primary_account,
                        status=HardshipCase.Status.UNDER_REVIEW,
                        defaults={'source': 'Raw-Signal-Ingest', 'specialist_required': True, 'notes': text_snippet[:200]}
                    )
                    domains_affected.append("REGULATORY: TRIP WIRE TRIPPED -> Enrolled in Hardship review.")

                if 'dnc_restriction' in signal_names:
                    primary_account.dnc = True
                    primary_account.save()
                    domains_affected.append("REGULATORY: DNC Flag enabled -> Voice/automated outreach prohibited.")

            affected_customers.add(matched_customer.id)
            separated_events.append({
                "customer_id": matched_customer.id,
                "customer_name": matched_customer.name,
                "confidence": round(confidence, 2),
                "match_reason": match_reason,
                "account_id": primary_account.id if primary_account else "N/A",
                "domains_routed": domains_affected
            })

        # Log provenance to immutable audit log
        log_audit(
            event_type='RAW_INGEST_SEPARATED',
            entity_id=f"batch-{uuid.uuid4().hex[:6]}",
            summary=f"Processed raw data batch: {len(separated_events)} matched and separated, {len(quarantined_records)} quarantined to DLQ, {len(steward_candidates)} sent for steward review.",
            actor=request.user if request.user.is_authenticated else None,
            details={
                "total_records": len(records),
                "affected_customers": list(affected_customers),
                "quarantined_count": len(quarantined_records),
                "steward_candidates_count": len(steward_candidates)
            }
        )

        return Response({
            "status": "COMPLETED",
            "summary": {
                "total_raw_records": len(records),
                "matched_and_separated": len(separated_events),
                "quarantined_to_dlq": len(quarantined_records),
                "ambiguous_steward_reviews": len(steward_candidates)
            },
            "separated_events": separated_events,
            "quarantined_records": quarantined_records,
            "steward_review_candidates": steward_candidates
        })

    def _resolve_entity(self, rec, customers):
        """
        Resolves entity using deterministic and probabilistic matching across 10 Golden Customers.
        Returns (customer_obj, confidence_score, match_reason).
        """
        raw_str = (str(rec.get('customer_hint', '')) + " " +
                   str(rec.get('name', '')) + " " +
                   str(rec.get('account_id', '')) + " " +
                   str(rec.get('email', '')) + " " +
                   str(rec.get('phone', '')) + " " +
                   str(rec.get('text', ''))).lower()

        # 1. Exact Account ID Match
        acct_id = rec.get('account_id', '')
        if acct_id:
            for c in customers:
                for a in c.accounts.all():
                    if a.id.lower() == acct_id.lower() or a.source_record_id.lower() == acct_id.lower():
                        return (c, 1.0, f"Exact Account ID Match ({a.id})")

        # 2. Exact Phone Match
        phone = re.sub(r'[^\d]', '', str(rec.get('phone', '') or ''))
        if len(phone) >= 7:
            for c in customers:
                c_phone = re.sub(r'[^\d]', '', c.phone or '')
                if phone in c_phone or c_phone in phone:
                    return (c, 1.0, f"Exact Phone Match ({c.phone})")

        # 3. Exact Email Match
        email = str(rec.get('email', '')).strip().lower()
        if email and '@' in email:
            for c in customers:
                if c.email and c.email.lower() == email:
                    return (c, 1.0, f"Exact Email Match ({c.email})")

        # 4. Text/Hint-based search across name tokens
        best_match = None
        best_score = 0.0
        best_reason = "No correlation found"

        for c in customers:
            name_parts = c.name.lower().split()
            first_name = name_parts[0] if name_parts else ''
            last_name = name_parts[-1] if len(name_parts) > 1 else ''

            # Full name exact in raw string
            if c.name.lower() in raw_str:
                return (c, 0.98, f"Full Name Match '{c.name}' in raw feed")

            # First + Last name both present
            if first_name in raw_str and last_name in raw_str:
                score = 0.92
                if score > best_score:
                    best_score = score
                    best_match = c
                    best_reason = f"First & Last Name tokens '{first_name} {last_name}' identified"

            # Last name alone with loan or city hint
            elif last_name and len(last_name) > 3 and last_name in raw_str:
                city_hint = c.address.lower() if c.address else ''
                if any(w in raw_str for w in city_hint.split(',')):
                    score = 0.86
                    if score > best_score:
                        best_score = score
                        best_match = c
                        best_reason = f"Surname '{last_name}' + Address Locality match"
                else:
                    score = 0.65  # Ambiguous
                    if score > best_score:
                        best_score = score
                        best_match = c
                        best_reason = f"Ambiguous Surname token '{last_name}' without secondary corroboration"

        if best_match and best_score >= 0.60:
            return (best_match, best_score, best_reason)

        return (None, 0.10, "Uncorrelated / Unrelated party payload")

    def _get_target_account(self, customer, rec):
        """Returns the specific account or the primary active account for this customer."""
        accts = list(customer.accounts.all())
        if not accts:
            return None
        acct_id = rec.get('account_id')
        if acct_id:
            for a in accts:
                if a.id.lower() == acct_id.lower() or a.source_record_id.lower() == acct_id.lower():
                    return a
        return accts[0]

    def _extract_signals(self, text):
        """Extracts conversational signals per Section 11 Whisper signal taxonomy."""
        signals = []
        t = text.lower()
        if any(w in t for w in ['pay', 'payment', 'transfer', 'deposit', 'settle', 'friday', 'sending']):
            signals.append({'signal': 'payment_intent', 'confidence': 0.94})
        if any(w in t for w in ['laid off', 'layoff', 'lost job', 'medical', 'hospital', 'hardship', 'emergency', 'distress', 'ei benefit']):
            signals.append({'signal': 'hardship_indicator', 'confidence': 0.96})
        if any(w in t for w in ['dispute', 'unauthorized', 'fraud', 'not my', 'overcharge', 'billing error', 'challenge']):
            signals.append({'signal': 'dispute_signal', 'confidence': 0.95})
        if any(w in t for w in ['stop calling', 'do not call', 'harass', 'lawyer', 'attorney', 'written only']):
            signals.append({'signal': 'dnc_restriction', 'confidence': 0.98})
        return signals

    def _parse_unstructured_text(self, text):
        """Splits unstructured paragraph or log text into discrete event items."""
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        if len(paragraphs) <= 1:
            paragraphs = [line.strip() for line in text.splitlines() if line.strip()]

        items = []
        for p in paragraphs:
            # Check for amount
            amt_match = re.search(r'\$\s*(\d+(?:,\d{3})*(?:\.\d{2})?)', p)
            amt = float(amt_match.group(1).replace(',', '')) if amt_match else None

            # Detect item category
            rec_type = 'general'
            p_lower = p.lower()
            if 'payment' in p_lower or 'paid' in p_lower:
                rec_type = 'payment'
            elif 'promise' in p_lower or 'ptp' in p_lower:
                rec_type = 'ptp'
            elif 'call' in p_lower or 'dialer' in p_lower:
                rec_type = 'contact'
            elif 'dispute' in p_lower:
                rec_type = 'dispute'
            elif 'hardship' in p_lower or 'laid off' in p_lower or 'medical' in p_lower:
                rec_type = 'hardship'

            items.append({
                "text": p,
                "amount": amt,
                "type": rec_type
            })
        return items

    def _parse_csv(self, csv_text):
        """Parses CSV feed into normalized raw candidate records."""
        import csv
        import io
        records = []
        reader = csv.DictReader(io.StringIO(csv_text.strip()))
        for row in reader:
            amt_val = row.get('amount') or row.get('payment_amount') or ''
            try:
                amt = float(re.sub(r'[^\d.]', '', amt_val)) if amt_val else None
            except Exception:
                amt = None

            records.append({
                "raw_id": row.get('raw_record_id') or row.get('id') or '',
                "customer_hint": row.get('customer_hint') or row.get('customer_name') or row.get('name') or '',
                "account_id": row.get('account_reference') or row.get('account_id') or '',
                "phone": row.get('phone_number') or row.get('phone') or '',
                "email": row.get('email_address') or row.get('email') or '',
                "type": (row.get('event_type') or row.get('type') or 'general').lower(),
                "amount": amt,
                "channel": (row.get('channel') or 'phone').lower(),
                "due_date": row.get('due_date') or row.get('ptp_due_date'),
                "text": row.get('raw_payload_text') or row.get('notes') or row.get('text') or row.get('transcript') or '',
                "source_system": row.get('source_feed') or row.get('source_system') or 'CSV-Ingest'
            })
        return records

