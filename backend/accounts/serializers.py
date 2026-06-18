from rest_framework import serializers
from django.contrib.auth import get_user_model

# This grabs the CustomUser model you already built in models.py
User = get_user_model()

class UserRegistrationSerializer(serializers.ModelSerializer):
    # write_only=True ensures the password is never sent back out to the frontend by accident
    password = serializers.CharField(write_only=True)
    
    # We map your frontend's 'fullName' JSON key to Django's built-in 'first_name' column
    fullName = serializers.CharField(source='first_name')

    class Meta:
        model = User
        # These fields match exactly what we packed into the JSON in your JavaScript
        fields = ['fullName', 'email', 'phone', 'role', 'password']

    def create(self, validated_data):
        # create_user automatically scrambles (hashes) the password for security before saving
        user = User.objects.create_user(
            username=validated_data['email'], # We use their email as their required username
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            phone=validated_data.get('phone', ''),
            role=validated_data.get('role', '')
        )
        return user