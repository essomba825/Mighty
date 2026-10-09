from django.contrib.auth import get_user_model
from django.db import models
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class LoginSerializer(TokenObtainPairSerializer):
    """Connexion par nom d'utilisateur OU email (champ unique 'identifier')."""
    identifier = serializers.CharField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.pop('email', None)

    def validate(self, attrs):
        identifier = attrs.pop('identifier')
        user = User.objects.filter(
            models.Q(username__iexact=identifier) | models.Q(email__iexact=identifier)
        ).first()
        if not user:
            raise serializers.ValidationError("Nom d'utilisateur ou email introuvable.")
        attrs['email'] = user.email
        return super().validate(attrs)


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'password', 'first_name', 'last_name', 'phone', 'role']

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'first_name', 'last_name', 'phone',
                  'role', 'status', 'date_joined']
        read_only_fields = ['role', 'status', 'date_joined']


class AdminUserSerializer(serializers.ModelSerializer):
    """Serializer réservé aux admins : role et status sont modifiables.

    Permet de valider/rejeter un compte (status) et de promouvoir un membre
    (role) sans passer par l'Admin Django.
    """
    full_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name',
            'full_name', 'phone', 'role', 'status', 'is_staff',
            'date_joined', 'last_login',
        ]
        read_only_fields = ['id', 'email', 'username', 'date_joined', 'last_login']

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username
