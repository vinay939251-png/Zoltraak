"""
Decisioning views — recommendations, rule sets, and decision memory snapshots.
"""
from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from decisioning.models import Recommendation, RuleSetVersion, DecisionMemory
from decisioning.serializers import RecommendationSerializer, RuleSetVersionSerializer, DecisionMemorySerializer
from decisioning.engine import RulesEngine
from accounts.models import Account
from audit.utils import log_audit


class RecommendationViewSet(viewsets.ModelViewSet):
    queryset = Recommendation.objects.select_related('account', 'account__customer', 'reviewed_by').all().order_by('-created_at')
    serializer_class = RecommendationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()
        if user.is_authenticated and user.role == 'collections_agent':
            qs = qs.filter(account__assigned_agent=user)
        account_id = self.request.query_params.get('account')
        if account_id:
            qs = qs.filter(account_id=account_id)
        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)
        return qs

    @action(detail=False, methods=['post'], url_path='generate')
    def generate(self, request):
        """Generates or updates recommendation for an account based on rules engine."""
        account_id = request.data.get('account_id')
        if not account_id:
            return Response({'error': 'account_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        account = Account.objects.filter(id=account_id).first()
        if not account:
            return Response({'error': 'Account not found.'}, status=status.HTTP_404_NOT_FOUND)

        eval_res = RulesEngine.evaluate_eligibility(account)

        # Create or update recommendation
        rec = Recommendation.objects.create(
            account=account,
            version=1,
            status=Recommendation.Status.PENDING_REVIEW,
            target='30-day cure propensity',
            score=0.78 if eval_res['eligible'] else 0.20,
            model_version='champion-xgb-cure-v2',
            prediction_timestamp=timezone.now(),
            action=eval_res['action_type'],
            top_features=[
                {'feature': 'days_past_due', 'value': account.dpd, 'importance': 0.35, 'direction': 'negative'},
                {'feature': 'overdue_balance', 'value': float(account.overdue_balance), 'importance': 0.28, 'direction': 'negative'},
                {'feature': 'historical_ptp_adherence', 'value': account.historical_ptp_adherence, 'importance': 0.22, 'direction': 'positive'},
                {'feature': 'recent_payment_count', 'value': account.recent_payment_count, 'importance': 0.15, 'direction': 'positive'}
            ]
        )

        # Persist DecisionMemory
        DecisionMemory.objects.create(
            recommendation=rec,
            account_id=account.id,
            feature_values={
                'dpd': account.dpd,
                'overdue_balance': float(account.overdue_balance),
                'contact_count_7d': account.contact_count_7d,
                'hardship': account.hardship,
                'dispute': account.dispute
            },
            feature_timestamps={'observed_at': account.observed_at.isoformat() if account.observed_at else None},
            feature_version='features-v2.1',
            model_id='model-xgb-cure',
            model_version='v2.0',
            model_prediction=rec.score,
            policy_version='demo-policy-v2.1',
            rule_version=eval_res['rule_version']
        )

        log_audit(
            'SEED_CREATED',
            rec.id,
            f"Generated recommendation '{rec.action}' for account {account.id}",
            actor=request.user,
            details={'action': rec.action, 'eligible': eval_res['eligible']}
        )

        return Response(RecommendationSerializer(rec).data, status=status.HTTP_201_CREATED)


class RuleSetVersionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = RuleSetVersion.objects.all().order_by('-created_at')
    serializer_class = RuleSetVersionSerializer
    permission_classes = [permissions.IsAuthenticated]


class DecisionMemoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DecisionMemory.objects.all().order_by('-created_at')
    serializer_class = DecisionMemorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        rec_id = self.request.query_params.get('recommendation')
        if rec_id:
            qs = qs.filter(recommendation_id=rec_id)
        account_id = self.request.query_params.get('account_id')
        if account_id:
            qs = qs.filter(account_id=account_id)
        return qs


class EvaluateRulesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        account_id = request.data.get('account_id')
        overrides = request.data.get('overrides') or {}

        account = None
        if account_id:
            account = Account.objects.filter(id=account_id).first()

        if not account:
            if not overrides:
                return Response({'error': 'account_id or overrides dictionary is required.'}, status=status.HTTP_400_BAD_REQUEST)
            class MockAccount:
                id = overrides.get('account_id', 'sim-acct-001')
                status = overrides.get('status', 'ACTIVE')
                dnc = overrides.get('dnc', False)
                contact_count_7d = int(overrides.get('contact_count_7d', 0))
                dispute = overrides.get('dispute', False)
                hardship = overrides.get('hardship', False)
                dpd = int(overrides.get('dpd', 25))
                source_system = 'SimulationSandbox'
                observed_at = timezone.now()
            account = MockAccount()

        result = RulesEngine.evaluate_eligibility(account, overrides=overrides)
        return Response(result)

