from rest_framework import serializers
from .models import User


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, style={'input_type': 'password'})
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role', 'password', 'is_active', 'date_joined']
        read_only_fields = ['id', 'date_joined']
        extra_kwargs = {
            'email': {'required': True},
        }
    
    def create(self, validated_data):
        """
        Créer un nouvel utilisateur avec mot de passe hashé
        """
        password = validated_data.pop('password', None)
        
        if not password:
            raise serializers.ValidationError({'password': 'Le mot de passe est obligatoire'})
        
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user
    
    def update(self, instance, validated_data):
        """
        Mettre à jour un utilisateur existant
        Si le mot de passe est fourni, il sera hashé
        """
        password = validated_data.pop('password', None)
        
        # Mettre à jour les autres champs
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Hasher le mot de passe si fourni
        if password:
            instance.set_password(password)
        
        instance.save()
        return instance
