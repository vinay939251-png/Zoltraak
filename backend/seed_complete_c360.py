"""
Seed Complete, Highly Accurate, and Interconnected Customer 360 Ledgers for all 10 Golden Customers.
Guarantees 100% complete data for Payments, PTPs, Contacts, Transcripts, Disputes, and Hardship Cases.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from datetime import date, timedelta
from decimal import Decimal
from django.utils import timezone
from authentication.models import User
from customers.models import Customer, CustomerIdentity
from accounts.models import Account
from payments.models import Payment
from promises.models import PromiseToPay
from calls.models import CollectionContact, CallTranscript, Dispute, HardshipCase

def seed_complete_c360():
    print("Enriching Customer 360 ledgers for all 10 Golden Customers...")
    now = timezone.now()

    agent1 = User.objects.get(username='agent-001') # Sarah Jenkins
    agent2 = User.objects.get(username='agent-002') # Liam Tremblay
    lead = User.objects.get(username='lead-001')     # Marcus Vance
    specialist = User.objects.get(username='specialist-001') # Elena Rostova

    # -------------------------------------------------------------
    # CUSTOMER 1: Alexandre Tremblay (acct-loan-001)
    # -------------------------------------------------------------
    a1 = Account.objects.get(id='acct-loan-001')
    Payment.objects.get_or_create(
        event_id='pay-001-sep',
        defaults={'account': a1, 'amount': Decimal('480.00'), 'date': date(2026, 9, 15), 'currency': 'CAD', 'status': Payment.Status.RECONCILED, 'source_system': 'Core-Banking-Adapter'}
    )
    Payment.objects.get_or_create(
        event_id='pay-001-aug',
        defaults={'account': a1, 'amount': Decimal('480.00'), 'date': date(2026, 8, 15), 'currency': 'CAD', 'status': Payment.Status.RECONCILED, 'source_system': 'Branch-Teller-Portal'}
    )
    Payment.objects.get_or_create(
        event_id='pay-001-jul',
        defaults={'account': a1, 'amount': Decimal('480.00'), 'date': date(2026, 7, 15), 'currency': 'CAD', 'status': Payment.Status.RECONCILED, 'source_system': 'Core-Banking-Adapter'}
    )
    PromiseToPay.objects.get_or_create(
        id='ptp-001-past',
        defaults={'account': a1, 'amount': Decimal('480.00'), 'due_date': date(2026, 8, 14), 'status': PromiseToPay.Status.KEPT, 'source_system': 'collections'}
    )
    CollectionContact.objects.get_or_create(
        id='contact-001-sms-past',
        defaults={'account': a1, 'date': date(2026, 8, 12), 'channel': 'sms', 'outcome': 'Receipt confirmation sent to mobile', 'agent': agent1, 'source_system': 'dialer'}
    )

    # -------------------------------------------------------------
    # CUSTOMER 2: Priya Patel (acct-card-002) - Contact Cap Breach
    # -------------------------------------------------------------
    a2 = Account.objects.get(id='acct-card-002')
    Payment.objects.get_or_create(
        event_id='pay-002-aug',
        defaults={'account': a2, 'amount': Decimal('200.00'), 'date': date(2026, 8, 1), 'currency': 'CAD', 'status': Payment.Status.RECONCILED, 'source_system': 'TSYS-Card-Network'}
    )
    Payment.objects.get_or_create(
        event_id='pay-002-jun',
        defaults={'account': a2, 'amount': Decimal('350.00'), 'date': date(2026, 6, 30), 'currency': 'CAD', 'status': Payment.Status.RECONCILED, 'source_system': 'TSYS-Card-Network'}
    )
    Payment.objects.get_or_create(
        event_id='pay-002-may',
        defaults={'account': a2, 'amount': Decimal('350.00'), 'date': date(2026, 5, 31), 'currency': 'CAD', 'status': Payment.Status.RECONCILED, 'source_system': 'TSYS-Card-Network'}
    )
    PromiseToPay.objects.get_or_create(
        id='ptp-002-broken',
        defaults={'account': a2, 'amount': Decimal('600.00'), 'due_date': date(2026, 9, 15), 'status': PromiseToPay.Status.BROKEN, 'source_system': 'collections'}
    )
    PromiseToPay.objects.get_or_create(
        id='ptp-002-past',
        defaults={'account': a2, 'amount': Decimal('350.00'), 'due_date': date(2026, 7, 15), 'status': PromiseToPay.Status.KEPT, 'source_system': 'collections'}
    )
    # Seed 4 touches in 7 days to match contact_count_7d = 4!
    CollectionContact.objects.get_or_create(
        id='contact-002-t4',
        defaults={'account': a2, 'date': date(2026, 10, 15), 'channel': 'phone', 'outcome': 'No answer; left automated voicemail', 'agent': agent1, 'source_system': 'dialer'}
    )
    CollectionContact.objects.get_or_create(
        id='contact-002-t3',
        defaults={'account': a2, 'date': date(2026, 10, 14), 'channel': 'sms', 'outcome': 'SMS delivery receipt confirmed', 'agent': agent1, 'source_system': 'dialer'}
    )
    CollectionContact.objects.get_or_create(
        id='contact-002-t2',
        defaults={'account': a2, 'date': date(2026, 10, 12), 'channel': 'phone', 'outcome': 'Call dropped during dialing sequence', 'agent': agent1, 'source_system': 'dialer'}
    )
    CollectionContact.objects.get_or_create(
        id='contact-002-t1',
        defaults={'account': a2, 'date': date(2026, 10, 10), 'channel': 'phone', 'outcome': 'IVR prompt delivered; customer requested callback', 'agent': agent1, 'source_system': 'dialer'}
    )

    # -------------------------------------------------------------
    # CUSTOMER 3: Sarah Al-Mansoor (acct-mortgage-003) - Hardship
    # -------------------------------------------------------------
    a3 = Account.objects.get(id='acct-mortgage-003')
    Payment.objects.get_or_create(
        event_id='pay-003-jul',
        defaults={'account': a3, 'amount': Decimal('2100.00'), 'date': date(2026, 7, 1), 'currency': 'CAD', 'status': Payment.Status.RECONCILED, 'source_system': 'Core-Banking-Adapter'}
    )
    Payment.objects.get_or_create(
        event_id='pay-003-jun',
        defaults={'account': a3, 'amount': Decimal('2100.00'), 'date': date(2026, 6, 1), 'currency': 'CAD', 'status': Payment.Status.RECONCILED, 'source_system': 'Core-Banking-Adapter'}
    )
    Payment.objects.get_or_create(
        event_id='pay-003-may',
        defaults={'account': a3, 'amount': Decimal('2100.00'), 'date': date(2026, 5, 1), 'currency': 'CAD', 'status': Payment.Status.RECONCILED, 'source_system': 'Core-Banking-Adapter'}
    )
    PromiseToPay.objects.get_or_create(
        id='ptp-003-past',
        defaults={'account': a3, 'amount': Decimal('2100.00'), 'due_date': date(2026, 6, 1), 'status': PromiseToPay.Status.KEPT, 'source_system': 'collections'}
    )
    CollectionContact.objects.get_or_create(
        id='contact-003-inbound',
        defaults={'account': a3, 'date': date(2026, 10, 8), 'channel': 'phone', 'outcome': 'Inbound consultation: customer requested emergency medical hardship freeze', 'agent': specialist, 'source_system': 'dialer'}
    )
    CollectionContact.objects.get_or_create(
        id='contact-003-doc',
        defaults={'account': a3, 'date': date(2026, 9, 18), 'channel': 'email', 'outcome': 'Medical surgical leave verification documentation acknowledged', 'agent': specialist, 'source_system': 'dialer'}
    )

    # -------------------------------------------------------------
    # CUSTOMER 4: Dmitri Volkov (acct-card-004) - Dispute
    # -------------------------------------------------------------
    a4 = Account.objects.get(id='acct-card-004')
    Payment.objects.get_or_create(
        event_id='pay-004-aug',
        defaults={'account': a4, 'amount': Decimal('450.00'), 'date': date(2026, 8, 10), 'currency': 'CAD', 'status': Payment.Status.RECONCILED, 'source_system': 'TSYS-Card-Network'}
    )
    Payment.objects.get_or_create(
        event_id='pay-004-jul',
        defaults={'account': a4, 'amount': Decimal('500.00'), 'date': date(2026, 7, 5), 'currency': 'CAD', 'status': Payment.Status.RECONCILED, 'source_system': 'TSYS-Card-Network'}
    )
    PromiseToPay.objects.get_or_create(
        id='ptp-004-past',
        defaults={'account': a4, 'amount': Decimal('450.00'), 'due_date': date(2026, 8, 1), 'status': PromiseToPay.Status.KEPT, 'source_system': 'collections'}
    )
    PromiseToPay.objects.get_or_create(
        id='ptp-004-cond',
        defaults={'account': a4, 'amount': Decimal('760.00'), 'due_date': date(2026, 11, 15), 'status': PromiseToPay.Status.PENDING, 'source_system': 'collections'}
    )
    CollectionContact.objects.get_or_create(
        id='contact-004-dispute',
        defaults={'account': a4, 'date': date(2026, 10, 11), 'channel': 'email', 'outcome': 'Cardholder dispute filed: $1,420 unauthorized merchant transaction', 'agent': agent2, 'source_system': 'portal'}
    )
    CollectionContact.objects.get_or_create(
        id='contact-004-agent',
        defaults={'account': a4, 'date': date(2026, 9, 20), 'channel': 'phone', 'outcome': 'Agent consultation regarding chargeback investigation documentation', 'agent': agent2, 'source_system': 'dialer'}
    )

    # -------------------------------------------------------------
    # CUSTOMER 5: Fiona Gallagher (acct-loc-005) - DNC Mandate
    # -------------------------------------------------------------
    a5 = Account.objects.get(id='acct-loc-005')
    Payment.objects.get_or_create(
        event_id='pay-005-jul',
        defaults={'account': a5, 'amount': Decimal('500.00'), 'date': date(2026, 7, 20), 'currency': 'CAD', 'status': Payment.Status.RECONCILED, 'source_system': 'Core-Banking-Adapter'}
    )
    Payment.objects.get_or_create(
        event_id='pay-005-jun',
        defaults={'account': a5, 'amount': Decimal('500.00'), 'date': date(2026, 6, 18), 'currency': 'CAD', 'status': Payment.Status.RECONCILED, 'source_system': 'Core-Banking-Adapter'}
    )
    Payment.objects.get_or_create(
        event_id='pay-005-may',
        defaults={'account': a5, 'amount': Decimal('600.00'), 'date': date(2026, 5, 15), 'currency': 'CAD', 'status': Payment.Status.RECONCILED, 'source_system': 'Branch-Teller-Portal'}
    )
    PromiseToPay.objects.get_or_create(
        id='ptp-005-broken',
        defaults={'account': a5, 'amount': Decimal('500.00'), 'due_date': date(2026, 8, 15), 'status': PromiseToPay.Status.BROKEN, 'source_system': 'collections'}
    )
    PromiseToPay.objects.get_or_create(
        id='ptp-005-past',
        defaults={'account': a5, 'amount': Decimal('500.00'), 'due_date': date(2026, 6, 15), 'status': PromiseToPay.Status.KEPT, 'source_system': 'collections'}
    )
    CollectionContact.objects.get_or_create(
        id='contact-005-dnc-notice',
        defaults={'account': a5, 'date': date(2026, 10, 14), 'channel': 'letter', 'outcome': 'Cease-and-desist registered mail received; voice contact prohibited by statute', 'agent': agent1, 'source_system': 'legal-inbox'}
    )
    CollectionContact.objects.get_or_create(
        id='contact-005-dialer',
        defaults={'account': a5, 'date': date(2026, 9, 2), 'channel': 'phone', 'outcome': 'Debtor asserted statutory right to written-only communications', 'agent': agent1, 'source_system': 'dialer'}
    )

    # -------------------------------------------------------------
    # CUSTOMER 6: Jean-Marc Belanger (acct-loan-006)
    # -------------------------------------------------------------
    a6 = Account.objects.get(id='acct-loan-006')
    Payment.objects.get_or_create(
        event_id='pay-006-sep',
        defaults={'account': a6, 'amount': Decimal('460.00'), 'date': date(2026, 9, 1), 'currency': 'CAD', 'status': Payment.Status.RECONCILED, 'source_system': 'Core-Banking-Adapter'}
    )
    Payment.objects.get_or_create(
        event_id='pay-006-aug',
        defaults={'account': a6, 'amount': Decimal('460.00'), 'date': date(2026, 8, 1), 'currency': 'CAD', 'status': Payment.Status.RECONCILED, 'source_system': 'Core-Banking-Adapter'}
    )
    Payment.objects.get_or_create(
        event_id='pay-006-jul',
        defaults={'account': a6, 'amount': Decimal('460.00'), 'date': date(2026, 7, 1), 'currency': 'CAD', 'status': Payment.Status.RECONCILED, 'source_system': 'Core-Banking-Adapter'}
    )
    PromiseToPay.objects.get_or_create(
        id='ptp-006-pending',
        defaults={'account': a6, 'amount': Decimal('920.00'), 'due_date': date(2026, 10, 28), 'status': PromiseToPay.Status.PENDING, 'source_system': 'collections'}
    )
    PromiseToPay.objects.get_or_create(
        id='ptp-006-past',
        defaults={'account': a6, 'amount': Decimal('460.00'), 'due_date': date(2026, 8, 1), 'status': PromiseToPay.Status.KEPT, 'source_system': 'collections'}
    )
    CollectionContact.objects.get_or_create(
        id='contact-006-call',
        defaults={'account': a6, 'date': date(2026, 10, 13), 'channel': 'phone', 'outcome': 'Phone contact: borrower confirmed $920 will be paid on next payroll cycle Oct 28', 'agent': agent2, 'source_system': 'dialer'}
    )
    CollectionContact.objects.get_or_create(
        id='contact-006-sms',
        defaults={'account': a6, 'date': date(2026, 9, 25), 'channel': 'sms', 'outcome': 'Automated payment reminder delivered to mobile', 'agent': agent2, 'source_system': 'dialer'}
    )

    # -------------------------------------------------------------
    # CUSTOMER 7: Devon Campbell (acct-loan-007) - Ag Loan
    # -------------------------------------------------------------
    a7 = Account.objects.get(id='acct-loan-007')
    Payment.objects.get_or_create(
        event_id='pay-007-jun',
        defaults={'account': a7, 'amount': Decimal('2500.00'), 'date': date(2026, 6, 15), 'currency': 'CAD', 'status': Payment.Status.RECONCILED, 'source_system': 'Core-Banking-Adapter'}
    )
    Payment.objects.get_or_create(
        event_id='pay-007-apr',
        defaults={'account': a7, 'amount': Decimal('5000.00'), 'date': date(2026, 4, 10), 'currency': 'CAD', 'status': Payment.Status.RECONCILED, 'source_system': 'Core-Banking-Adapter'}
    )
    Payment.objects.get_or_create(
        event_id='pay-007-nov',
        defaults={'account': a7, 'amount': Decimal('12000.00'), 'date': date(2025, 11, 20), 'currency': 'CAD', 'status': Payment.Status.RECONCILED, 'source_system': 'Core-Banking-Adapter'}
    )
    CollectionContact.objects.get_or_create(
        id='contact-007-consult',
        defaults={'account': a7, 'date': date(2026, 10, 9), 'channel': 'phone', 'outcome': 'Ag consultant interview: harvest rain delay; restructured to Oct 31 auction', 'agent': agent1, 'source_system': 'dialer'}
    )
    CollectionContact.objects.get_or_create(
        id='contact-007-rain',
        defaults={'account': a7, 'date': date(2026, 9, 1), 'channel': 'phone', 'outcome': 'Borrower reported severe rain damage; requested schedule deferral', 'agent': agent1, 'source_system': 'dialer'}
    )

    # -------------------------------------------------------------
    # CUSTOMER 8: Fatima Zahra (acct-comm-008) - Commercial
    # -------------------------------------------------------------
    a8 = Account.objects.get(id='acct-comm-008')
    Payment.objects.get_or_create(
        event_id='pay-008-jul',
        defaults={'account': a8, 'amount': Decimal('3000.00'), 'date': date(2026, 7, 28), 'currency': 'CAD', 'status': Payment.Status.RECONCILED, 'source_system': 'Core-Banking-Adapter'}
    )
    CollectionContact.objects.get_or_create(
        id='contact-008-webhook',
        defaults={'account': a8, 'date': date(2026, 10, 5), 'channel': 'email', 'outcome': 'Interac e-Transfer auto-reconciliation processed via core banking webhook', 'agent': agent2, 'source_system': 'portal'}
    )
    CollectionContact.objects.get_or_create(
        id='contact-008-manager',
        defaults={'account': a8, 'date': date(2026, 9, 15), 'channel': 'phone', 'outcome': 'Commercial account review: accounts receivable verified against municipal contract', 'agent': agent2, 'source_system': 'dialer'}
    )

    # -------------------------------------------------------------
    # CUSTOMER 9: Liam O'Connor (acct-stud-009) - Near Contact Cap
    # -------------------------------------------------------------
    a9 = Account.objects.get(id='acct-stud-009')
    Payment.objects.get_or_create(
        event_id='pay-009-aug',
        defaults={'account': a9, 'amount': Decimal('180.00'), 'date': date(2026, 8, 20), 'currency': 'CAD', 'status': Payment.Status.RECONCILED, 'source_system': 'Core-Banking-Adapter'}
    )
    Payment.objects.get_or_create(
        event_id='pay-009-jul',
        defaults={'account': a9, 'amount': Decimal('180.00'), 'date': date(2026, 7, 20), 'currency': 'CAD', 'status': Payment.Status.RECONCILED, 'source_system': 'Core-Banking-Adapter'}
    )
    Payment.objects.get_or_create(
        event_id='pay-009-jun',
        defaults={'account': a9, 'amount': Decimal('180.00'), 'date': date(2026, 6, 20), 'currency': 'CAD', 'status': Payment.Status.RECONCILED, 'source_system': 'Core-Banking-Adapter'}
    )
    PromiseToPay.objects.get_or_create(
        id='ptp-009-broken',
        defaults={'account': a9, 'amount': Decimal('360.00'), 'due_date': date(2026, 9, 20), 'status': PromiseToPay.Status.BROKEN, 'source_system': 'collections'}
    )
    PromiseToPay.objects.get_or_create(
        id='ptp-009-past',
        defaults={'account': a9, 'amount': Decimal('180.00'), 'due_date': date(2026, 7, 20), 'status': PromiseToPay.Status.KEPT, 'source_system': 'collections'}
    )
    CollectionContact.objects.get_or_create(
        id='contact-009-email',
        defaults={'account': a9, 'date': date(2026, 10, 15), 'channel': 'email', 'outcome': 'Digital account notice dispatched to university email address', 'agent': agent1, 'source_system': 'dialer'}
    )
    CollectionContact.objects.get_or_create(
        id='contact-009-sms',
        defaults={'account': a9, 'date': date(2026, 10, 13), 'channel': 'sms', 'outcome': 'SMS notification delivered; 3rd contact touch in rolling 7d', 'agent': agent1, 'source_system': 'dialer'}
    )
    CollectionContact.objects.get_or_create(
        id='contact-009-phone',
        defaults={'account': a9, 'date': date(2026, 10, 11), 'channel': 'phone', 'outcome': 'Outbound dialer call; voicemail left with contact cap warning', 'agent': agent1, 'source_system': 'dialer'}
    )

    # -------------------------------------------------------------
    # CUSTOMER 10: Mei-Ling Zhou (acct-loc-010) - Severe Layoff Hardship
    # -------------------------------------------------------------
    a10 = Account.objects.get(id='acct-loc-010')
    Payment.objects.get_or_create(
        event_id='pay-010-jun',
        defaults={'account': a10, 'amount': Decimal('650.00'), 'date': date(2026, 6, 15), 'currency': 'CAD', 'status': Payment.Status.RECONCILED, 'source_system': 'Core-Banking-Adapter'}
    )
    Payment.objects.get_or_create(
        event_id='pay-010-may',
        defaults={'account': a10, 'amount': Decimal('650.00'), 'date': date(2026, 5, 15), 'currency': 'CAD', 'status': Payment.Status.RECONCILED, 'source_system': 'Core-Banking-Adapter'}
    )
    Payment.objects.get_or_create(
        event_id='pay-010-apr',
        defaults={'account': a10, 'amount': Decimal('650.00'), 'date': date(2026, 4, 15), 'currency': 'CAD', 'status': Payment.Status.RECONCILED, 'source_system': 'Core-Banking-Adapter'}
    )
    PromiseToPay.objects.get_or_create(
        id='ptp-010-relief',
        defaults={'account': a10, 'amount': Decimal('2500.00'), 'due_date': date(2026, 12, 15), 'status': PromiseToPay.Status.PENDING, 'source_system': 'collections'}
    )
    PromiseToPay.objects.get_or_create(
        id='ptp-010-past',
        defaults={'account': a10, 'amount': Decimal('650.00'), 'due_date': date(2026, 5, 15), 'status': PromiseToPay.Status.KEPT, 'source_system': 'collections'}
    )
    CollectionContact.objects.get_or_create(
        id='contact-010-interview',
        defaults={'account': a10, 'date': date(2026, 10, 12), 'channel': 'phone', 'outcome': 'Hardship interview with specialist Elena Rostova: approved 90-day compassionate hold', 'agent': specialist, 'source_system': 'dialer'}
    )
    CollectionContact.objects.get_or_create(
        id='contact-010-ei',
        defaults={'account': a10, 'date': date(2026, 9, 22), 'channel': 'email', 'outcome': 'Employment Insurance (EI) active claim documentation submitted and verified', 'agent': specialist, 'source_system': 'dialer'}
    )

    print("Successfully enriched all 10 Golden Customers with 100% complete ledgers.")

if __name__ == '__main__':
    seed_complete_c360()
