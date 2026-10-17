"""
Machine learning model registry and prediction explanation views.
"""
from rest_framework import viewsets, permissions
from rest_framework.views import APIView
from models_ml.models import ModelRegistry, Prediction
from models_ml.serializers import ModelRegistrySerializer, PredictionSerializer


class ModelRegistryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ModelRegistry.objects.all().order_by('-created_at')
    serializer_class = ModelRegistrySerializer
    permission_classes = [permissions.IsAuthenticated]


class PredictionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Prediction.objects.all().order_by('-created_at')
    serializer_class = PredictionSerializer
    permission_classes = [permissions.IsAuthenticated]


class TrainModelView(APIView):
    """Triggers offline model training & calibration using Scikit-Learn / XGBoost."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from rest_framework.response import Response
        from models_ml.training_service import ml_service

        model_id = request.data.get('model_id', 'cure-probability-v1.0')
        result = ml_service.train_cure_model(model_id=model_id)
        return Response({
            'status': 'SUCCESS',
            'message': f"Model '{model_id}' successfully trained, calibrated, and registered.",
            'details': result
        })


class PredictAccountView(APIView):
    """Generates calibrated Honor Score (0-100) and SHAP local attribution explanations for an account."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from rest_framework.response import Response
        from rest_framework import status
        from accounts.models import Account
        from models_ml.training_service import ml_service

        account_id = request.data.get('account_id')
        model_id = request.data.get('model_id', 'cure-probability-v1.0')

        if not account_id:
            return Response({'error': 'account_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        account = Account.objects.filter(id=account_id).first()
        if not account:
            return Response({'error': f'Account {account_id} not found.'}, status=status.HTTP_404_NOT_FOUND)

        prediction = ml_service.predict_account(account, model_id=model_id)
        return Response(prediction)
