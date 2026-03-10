from rest_framework import serializers
from .models import User, Service, Notification


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, style={'input_type': 'password'})
    service_nom = serializers.CharField(source='service.nom', read_only=True)
    signature_url = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role', 'password', 'is_active', 'date_joined', 
                  'service', 'service_nom', 'signature_electronique', 'signature_url']
        read_only_fields = ['id', 'date_joined']
        extra_kwargs = {
            'email': {'required': True},
        }
    
    def get_signature_url(self, obj):
        """Retourne l'URL complète de la signature électronique"""
        if obj.signature_electronique:
            request = self.context.get('request')
            if request is not None:
                return request.build_absolute_uri(obj.signature_electronique.url)
            return obj.signature_electronique.url
        return None
    
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


class ServiceSerializer(serializers.ModelSerializer):
    """Serializer pour les services"""
    utilisateurs = UserSerializer(many=True, read_only=True)
    nombre_utilisateurs = serializers.SerializerMethodField()
    
    class Meta:
        model = Service
        fields = ['id', 'nom', 'description', 'utilisateurs', 'nombre_utilisateurs', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_nombre_utilisateurs(self, obj):
        return obj.utilisateurs.count()


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer pour les notifications"""
    
    class Meta:
        model = Notification
        fields = ['id', 'type', 'titre', 'message', 'lue', 'courrier_id', 'document_id', 'created_at', 'lue_at']
        read_only_fields = ['id', 'created_at', 'lue_at']
