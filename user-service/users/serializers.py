from rest_framework import serializers
from .models import UserProfile, DetectionHistory


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ('id', 'user_id', 'username', 'email', 'role', 'created_at')
        read_only_fields = ('id', 'created_at')


class DetectionHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = DetectionHistory
        fields = ('id', 'image_name', 'result', 'confidence', 'label', 'created_at')
        read_only_fields = ('id', 'created_at')