from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

User = get_user_model() # gets our CustomUser model

class RegisterSerializer(serializers.ModelSerializer):
    # password field - write only means it never shows in response
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password] # runs django password rules
    )
    password2 = serializers.CharField(
        write_only=True,
        required=True
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'password2', 'role')

    def validate(self, attrs):
        # Check both passwords match
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError(
                {"password": "Passwords do not match!"}
            )
        return attrs

    def create(self, validated_data):
        # Remove password2 before creating user
        validated_data.pop('password2')
        # create_user automatically hashes the password
        user = User.objects.create_user(**validated_data)
        return user


class UserSerializer(serializers.ModelSerializer):
    # Used to return user info (no password!)
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'role', 'date_joined')