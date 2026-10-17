from rest_framework import serializers
from features.models import FeatureDefinition, FeatureSnapshot


class FeatureDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeatureDefinition
        fields = '__all__'


class FeatureSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeatureSnapshot
        fields = '__all__'
