from rest_framework import serializers
from calls.models import CollectionContact, CallTranscript, HardshipCase, Dispute


class CollectionContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = CollectionContact
        fields = '__all__'


class CallTranscriptSerializer(serializers.ModelSerializer):
    class Meta:
        model = CallTranscript
        fields = '__all__'


class HardshipCaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = HardshipCase
        fields = '__all__'


class DisputeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dispute
        fields = '__all__'
