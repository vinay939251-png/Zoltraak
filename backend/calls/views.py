"""
Contact events, call transcripts, hardship cases, and disputes views.
"""
from rest_framework import viewsets, permissions
from rest_framework.views import APIView
from calls.models import CollectionContact, CallTranscript, HardshipCase, Dispute
from calls.serializers import CollectionContactSerializer, CallTranscriptSerializer, HardshipCaseSerializer, DisputeSerializer


class CollectionContactViewSet(viewsets.ModelViewSet):
    queryset = CollectionContact.objects.all().order_by('-date')
    serializer_class = CollectionContactSerializer
    permission_classes = [permissions.IsAuthenticated]


class CallTranscriptViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CallTranscript.objects.all().order_by('-created_at')
    serializer_class = CallTranscriptSerializer
    permission_classes = [permissions.IsAuthenticated]


class HardshipCaseViewSet(viewsets.ModelViewSet):
    queryset = HardshipCase.objects.all().order_by('-created_at')
    serializer_class = HardshipCaseSerializer
    permission_classes = [permissions.IsAuthenticated]


class DisputeViewSet(viewsets.ModelViewSet):
    queryset = Dispute.objects.all().order_by('-created_at')
    serializer_class = DisputeSerializer
    permission_classes = [permissions.IsAuthenticated]


class TranscribeAudioView(APIView):
    """
    Ingests and processes audio transcripts using Whisper signal extraction adapter.
    Extracts structured signals (PTP, Hardship, Dispute, Ownership Denials) and updates account flags.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from rest_framework.response import Response
        from rest_framework import status
        from accounts.models import Account
        from calls.whisper_service import transcription_adapter
        from data_platform.streaming.producer import KafkaProducer

        account_id = request.data.get('account_id')
        text = request.data.get('text', '').strip()
        language = request.data.get('language', 'en')

        if not account_id or not text:
            return Response({'error': 'Both account_id and text are required.'}, status=status.HTTP_400_BAD_REQUEST)

        account = Account.objects.filter(id=account_id).first()
        if not account:
            return Response({'error': f'Account {account_id} not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Process with Whisper signal extraction
        extraction = transcription_adapter.process_transcript(account_id, text, language=language)

        # Save transcript record
        transcript = CallTranscript.objects.create(
            account=account,
            language=language,
            text=text,
            signals=extraction['signals']
        )

        # Automatically flag account or create draft case if severe signal detected
        flagged_actions = []
        for sig in extraction['signals']:
            sig_type = sig['signal_type']
            if sig_type == 'HARDSHIP_INDICATOR' and not account.hardship:
                account.hardship = True
                account.save(update_fields=['hardship'])
                HardshipCase.objects.create(
                    account=account,
                    status=HardshipCase.Status.REVIEW_REQUIRED,
                    source='whisper-transcription',
                    notes=f"Extracted signal: {sig['value'].get('category')} (Evidence: {sig['evidence_snippet']})"
                )
                flagged_actions.append('HARDSHIP_FLAG_APPLIED')

            elif sig_type == 'DISPUTE_INDICATOR' and not account.dispute:
                account.dispute = True
                account.save(update_fields=['dispute'])
                Dispute.objects.create(
                    account=account,
                    status=Dispute.Status.OPEN,
                    source='whisper-transcription',
                    notes=f"Extracted signal: {sig['value'].get('category')} (Evidence: {sig['evidence_snippet']})"
                )
                flagged_actions.append('DISPUTE_FLAG_APPLIED')

        # Publish event to Kafka
        try:
            producer = KafkaProducer()
            producer.send({
                "eventId": f"evt-call-{transcript.id}",
                "eventType": "call.completed",
                "occurredAt": transcript.created_at.isoformat(),
                "ingestedAt": transcript.created_at.isoformat(),
                "sourceSystem": "whisper-transcription",
                "correlationId": f"corr-{transcript.id}",
                "accountId": account.id,
                "transcriptId": transcript.id,
                "language": language
            }, key=account.id)
        except Exception:
            pass

        return Response({
            'status': 'PROCESSED',
            'transcript_id': transcript.id,
            'signals': extraction['signals'],
            'signal_count': len(extraction['signals']),
            'requires_escalation': extraction['requires_escalation'],
            'automated_actions_triggered': flagged_actions,
            'provenance': extraction['provenance']
        }, status=status.HTTP_201_CREATED)

