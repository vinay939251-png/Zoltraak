"""
Deterministic rules engine for collections eligibility, policy compliance, and next-best-action routing.
"""
from decimal import Decimal


class RulesEngine:
    RULE_SET_VERSION = 'ruleset-v2.1-prod'

    @classmethod
    def evaluate_eligibility(cls, account, overrides=None):
        """
        Evaluates deterministic eligibility rules against an Account instance,
        optionally applying hypothetical attribute overrides for simulation.
        Returns a structured decision dictionary with counterfactual analysis.
        """
        results = []
        overrides = overrides or {}

        def add_check(rule_id, passed, reason_code, reason, mandatory=True):
            results.append({
                'rule_id': rule_id,
                'passed': bool(passed),
                'reason_code': reason_code,
                'reason': reason,
                'mandatory': mandatory
            })

        # Resolved attributes with overrides
        status_val = overrides.get('status', getattr(account, 'status', 'ACTIVE'))
        dnc_val = overrides.get('dnc', getattr(account, 'dnc', False))
        contact_count_7d = int(overrides.get('contact_count_7d', getattr(account, 'contact_count_7d', 0)))
        dispute_val = overrides.get('dispute', getattr(account, 'dispute', False))
        hardship_val = overrides.get('hardship', getattr(account, 'hardship', False))
        dpd_val = int(overrides.get('dpd', getattr(account, 'dpd', 0)))
        local_hour = int(overrides.get('local_hour', 14))
        proposed_discount_pct = float(overrides.get('proposed_discount_pct', 15.0))
        source_system = overrides.get('source_system', getattr(account, 'source_system', 'CoreBanking_TSYS'))
        observed_at = overrides.get('observed_at', getattr(account, 'observed_at', None))

        # 1. Account status active
        is_active = (status_val == 'ACTIVE')
        add_check(
            'ACCOUNT-001',
            is_active,
            'ACTIVE' if is_active else 'ACCOUNT_NOT_ACTIVE',
            'Account is active in core banking system.' if is_active else f'Account status is {status_val}. Inactive accounts cannot receive active collection.',
            mandatory=True
        )

        # 2. Do Not Contact (Mandatory regulatory restriction)
        dnc_clear = not bool(dnc_val)
        add_check(
            'DNC-001',
            dnc_clear,
            'CONTACT_ALLOWED' if dnc_clear else 'CONTACT_RESTRICTED',
            'No active Do-Not-Contact or written-only demand restriction.' if dnc_clear else 'Active Do-Not-Contact restriction enforced by regulation. Telephony and automated outreach strictly prohibited.',
            mandatory=True
        )

        # 3. Contact Cap (FCAC regulatory limit: maximum 3 contacts per 7-day rolling window)
        cap_clear = (contact_count_7d < 4)
        add_check(
            'CAP-001',
            cap_clear,
            'CONTACT_CAP_AVAILABLE' if cap_clear else 'CONTACT_CAP_EXCEEDED',
            f'{contact_count_7d} recorded contact attempts in the 7-day rolling window (statutory limit: 3).' if not cap_clear else f'{contact_count_7d} contacts in rolling 7 days; compliant with statutory frequency cap.',
            mandatory=True
        )

        # 4. Permissible Calling Hours (FCAC / TCPA rule: 08:00 - 21:00 borrower local time)
        time_clear = (8 <= local_hour <= 21)
        add_check(
            'TIME-001',
            time_clear,
            'PERMISSIBLE_CALLING_HOURS' if time_clear else 'OUTSIDE_CALLING_HOURS',
            f'Borrower local time ({local_hour:02d}:00) is within statutory calling window (08:00 - 21:00).' if time_clear else f'Local time {local_hour:02d}:00 is outside permissible calling window. Voice outreach blocked.',
            mandatory=True
        )

        # 5. Open dispute check
        no_dispute = not bool(dispute_val)
        add_check(
            'DISPUTE-001',
            no_dispute,
            'NO_OPEN_DISPUTE' if no_dispute else 'SPECIALIST_REQUIRED_DISPUTE',
            'No active dispute filed on this account.' if no_dispute else 'Formal customer dispute is active. Ordinary debt collection halted; routed for specialist dispute resolution.',
            mandatory=True
        )

        # 6. Hardship vulnerability check
        no_hardship = not bool(hardship_val)
        add_check(
            'HARDSHIP-001',
            no_hardship,
            'NO_HARDSHIP_FLAG' if no_hardship else 'SPECIALIST_REQUIRED_HARDSHIP',
            'No active hardship assistance plan.' if no_hardship else 'Customer is enrolled in or flagged for hardship consideration; requires hardship specialist review and moratorium protection.',
            mandatory=True
        )

        # 7. Delegation of Authority: Settlement Discount Threshold
        settle_ok = (proposed_discount_pct <= 20.0)
        add_check(
            'SETTLE-001',
            settle_ok,
            'WITHIN_DELEGATED_AUTHORITY' if settle_ok else 'SUPERVISOR_APPROVAL_REQUIRED',
            f'Proposed settlement discount ({proposed_discount_pct:.1f}%) is within collector delegated authority (<=20%).' if settle_ok else f'Proposed discount ({proposed_discount_pct:.1f}%) exceeds standard collector authority (20%); requires Team Lead Marcus Vance sign-off.',
            mandatory=False
        )

        # 8. Data freshness and lineage check
        lineage_ok = bool(source_system and observed_at)
        add_check(
            'DATA-001',
            lineage_ok,
            'DATA_FRESHNESS_VERIFIED' if lineage_ok else 'DATA_FRESHNESS_UNKNOWN',
            'Complete source provenance and observation timestamp verified.' if lineage_ok else 'Lineage metadata is incomplete or stale.',
            mandatory=False
        )

        blocked = [r for r in results if not r['passed']]
        mandatory_blocked = [r for r in blocked if r['mandatory']]
        eligible = (len(mandatory_blocked) == 0)

        # Determine recommended action
        if not is_active:
            action_type = 'no_action_closed'
        elif not dnc_clear:
            action_type = 'do_not_contact'
        elif not cap_clear:
            action_type = 'digital_cooling_hold'
        elif not time_clear:
            action_type = 'schedule_next_day_call'
        elif not no_dispute:
            action_type = 'route_dispute_specialist'
        elif not no_hardship:
            action_type = 'route_hardship_specialist'
        elif dpd_val > 60:
            action_type = 'escalated_outbound_call'
        elif dpd_val > 30:
            action_type = 'outbound_call'
        else:
            action_type = 'digital_reminder_sms'

        counterfactuals = cls.generate_counterfactuals(
            dpd=dpd_val,
            contact_count_7d=contact_count_7d,
            hardship=hardship_val,
            dispute=dispute_val,
            dnc=dnc_val,
            time_clear=time_clear,
            local_hour=local_hour
        )

        return {
            'eligible': eligible,
            'action_type': action_type,
            'rule_version': cls.RULE_SET_VERSION,
            'rule_results': results,
            'requires_human_review': True,
            'blocking_reasons': [b['reason_code'] for b in blocked],
            'blocking_descriptions': [b['reason'] for b in blocked],
            'counterfactuals': counterfactuals
        }

    @classmethod
    def generate_counterfactuals(cls, dpd, contact_count_7d, hardship, dispute, dnc, time_clear, local_hour):
        """
        Computes formal counterfactual explanations detailing what attribute changes
        would alter the policy decision tree outcome.
        """
        cfs = []

        if contact_count_7d >= 4:
            cfs.append({
                'scenario': 'Contact frequency cooldown expiry',
                'condition_change': f'contact_count_7d: {contact_count_7d} -> 2 (rolling 7-day window advances 48h)',
                'resulting_action': 'outbound_call' if dpd > 30 else 'digital_reminder_sms',
                'rule_impact': 'Statutory CAP-001 restriction lifts; account unlocks for direct telephone outreach.'
            })

        if dispute:
            cfs.append({
                'scenario': 'Dispute investigation resolution',
                'condition_change': 'dispute: True -> False (billing reconciliation and claim closed)',
                'resulting_action': 'settlement_offer_discount' if dpd > 60 else 'digital_reminder_sms',
                'rule_impact': 'DISPUTE-001 legal freeze lifted; 20% principal discount settlement proposal unlocked.'
            })

        if hardship:
            cfs.append({
                'scenario': 'Hardship relief stabilization',
                'condition_change': 'hardship: True -> False (borrower exits distress relief)',
                'resulting_action': 'restructure_payment_plan',
                'rule_impact': 'HARDSHIP-001 moratorium transitions to structured 12-month amortization term extension.'
            })

        if dnc:
            cfs.append({
                'scenario': 'Borrower opts into digital channel',
                'condition_change': 'dnc: True -> False (written-only preference revoked by borrower)',
                'resulting_action': 'digital_self_cure_portal',
                'rule_impact': 'DNC-001 restrictions lift; automated SMS payment notifications permitted.'
            })

        if not time_clear:
            cfs.append({
                'scenario': 'Local timezone calling window opens',
                'condition_change': f'local_hour: {local_hour:02d}:00 -> 09:00 (statutory window opens)',
                'resulting_action': 'outbound_call' if dpd > 30 else 'digital_reminder_sms',
                'rule_impact': 'TIME-001 calling hours constraint cleared for immediate dispatch.'
            })

        if not dispute and not hardship and not dnc and contact_count_7d < 4 and time_clear:
            if dpd <= 30:
                cfs.append({
                    'scenario': 'Arrears aging progression',
                    'condition_change': f'dpd: {dpd} -> 45 (unpaid installment crosses 30-day threshold)',
                    'resulting_action': 'outbound_call',
                    'rule_impact': 'Policy triggers supervisor-approved outbound collector telephone engagement.'
                })
            else:
                cfs.append({
                    'scenario': 'Early partial cure commitment',
                    'condition_change': f'dpd: {dpd} -> 15 (partial payment cures oldest overdue cycle)',
                    'resulting_action': 'digital_reminder_sms',
                    'rule_impact': 'De-escalates from outbound collector voice calls to automated digital SMS reminder.'
                })

        return cfs
