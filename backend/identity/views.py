"""
Identity resolution views — match candidate review and reversible merge crosswalks.
"""
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from identity.models import IdentityMatchCandidate, IdentityMergeHistory
from identity.serializers import IdentityMatchCandidateSerializer, IdentityMergeHistorySerializer
from customers.models import CustomerIdentity
from audit.utils import log_audit


class IdentityCandidateViewSet(viewsets.ModelViewSet):
    queryset = IdentityMatchCandidate.objects.select_related('customer').all().order_by('-score')
    serializer_class = IdentityMatchCandidateSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=['post'], url_path='action')
    def perform_action(self, request, pk=None):
        candidate = self.get_object()
        user = request.user
        action_name = request.data.get('action')  # 'approve', 'reject', 'defer'
        reason = request.data.get('reason', '')

        if action_name == 'approve':
            candidate.status = IdentityMatchCandidate.Status.APPROVED
            candidate.reviewed_by = user
            candidate.reviewed_at = timezone.now()
            candidate.reason = reason
            candidate.save()

            # Record customer identity linkage
            CustomerIdentity.objects.get_or_create(
                source_system=candidate.source_system,
                source_id=candidate.source_record_id,
                defaults={
                    'customer': candidate.customer,
                    'match_type': CustomerIdentity.MatchType.PROBABILISTIC,
                    'score': candidate.score,
                    'evidence': candidate.evidence
                }
            )

            # Record reversible merge history
            merge_record = IdentityMergeHistory.objects.create(
                customer=candidate.customer,
                previous_golden_id=f"pending-{candidate.source_system}-{candidate.source_record_id}",
                new_golden_id=candidate.customer.id,
                source_ids=[f"{candidate.source_system}:{candidate.source_record_id}"],
                actor=user,
                reason=reason or 'Steward approved probabilistic Splink match',
                evidence={'candidate_id': candidate.id, 'score': candidate.score, 'evidence': candidate.evidence}
            )

            log_audit(
                'IDENTITY_APPROVED',
                candidate.id,
                f"Approved identity match {candidate.source_system}:{candidate.source_record_id} -> {candidate.customer.name}",
                actor=user,
                details={'merge_id': merge_record.id, 'score': candidate.score}
            )

            return Response({
                'message': 'Identity match approved and crosswalk updated.',
                'candidate': IdentityMatchCandidateSerializer(candidate).data,
                'merge_history_id': merge_record.id
            })

        elif action_name == 'reject':
            candidate.status = IdentityMatchCandidate.Status.REJECTED
            candidate.reviewed_by = user
            candidate.reviewed_at = timezone.now()
            candidate.reason = reason
            candidate.save()

            log_audit(
                'IDENTITY_REJECTED',
                candidate.id,
                f"Rejected identity candidate {candidate.source_system}:{candidate.source_record_id}",
                actor=user,
                details={'reason': reason}
            )
            return Response({
                'message': 'Identity match rejected.',
                'candidate': IdentityMatchCandidateSerializer(candidate).data
            })

        elif action_name == 'defer':
            candidate.status = IdentityMatchCandidate.Status.DEFERRED
            candidate.reviewed_by = user
            candidate.reviewed_at = timezone.now()
            candidate.reason = reason
            candidate.save()

            log_audit(
                'IDENTITY_DEFERRED',
                candidate.id,
                f"Deferred identity candidate {candidate.id}",
                actor=user,
                details={'reason': reason}
            )
            return Response({
                'message': 'Identity match deferred.',
                'candidate': IdentityMatchCandidateSerializer(candidate).data
            })

        return Response({'error': 'Invalid action. Must be approve, reject, or defer.'}, status=status.HTTP_400_BAD_REQUEST)


class IdentityMergeHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = IdentityMergeHistory.objects.all().order_by('-created_at')
    serializer_class = IdentityMergeHistorySerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=['post'], url_path='unmerge')
    def unmerge(self, request, pk=None):
        """
        Reverses a previously executed identity merge per Section 7.5.
        Restores isolated identity representation and marks merge record reversed.
        """
        merge_record = self.get_object()
        if merge_record.reversed:
            return Response({'error': 'This merge has already been reversed.'}, status=status.HTTP_400_BAD_REQUEST)

        reason = request.data.get('reason', 'Steward requested crosswalk unmerge')
        merge_record.reversed = True
        merge_record.reversed_at = timezone.now()
        merge_record.reversed_by = request.user
        merge_record.reversal_reason = reason
        merge_record.save()

        # Remove the linked identity record to unlink
        for sid in merge_record.source_ids:
            if ':' in sid:
                sys_name, rec_id = sid.split(':', 1)
                CustomerIdentity.objects.filter(customer=merge_record.customer, source_system=sys_name, source_id=rec_id).delete()

        log_audit(
            'ASSIGNMENT_CHANGED',
            merge_record.id,
            f"Reversed identity merge: unlinked {merge_record.source_ids} from {merge_record.customer.name}",
            actor=request.user,
            details={'reversal_reason': reason}
        )

        return Response({
            'message': 'Identity crosswalk successfully reversed (unmerged).',
            'merge_record': IdentityMergeHistorySerializer(merge_record).data
        })
