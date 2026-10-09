from rest_framework import serializers

from .models import Payment, PaymentRequest


class PaymentInitiateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['id', 'contribution', 'provider', 'phone_number', 'reference', 'status']
        read_only_fields = ['reference', 'status']

    def validate(self, attrs):
        if attrs['contribution'].amount <= 0:
            raise serializers.ValidationError('Montant invalide.')
        if hasattr(attrs['contribution'], 'payment'):
            raise serializers.ValidationError('Un paiement existe déjà pour cette contribution.')
        return attrs


class PaymentRequestVerifySerializer(serializers.Serializer):
    transaction_code = serializers.CharField(max_length=100, required=True)

    def validate_transaction_code(self, value):
        value = (value or '').strip()
        if len(value) < 4:
            raise serializers.ValidationError('Code de transaction trop court (4 caractères min).')
        return value


class PaymentRequestSerializer(serializers.ModelSerializer):
    project_title = serializers.CharField(source='project.title', read_only=True, default=None)

    class Meta:
        model = PaymentRequest
        fields = ['id', 'payment_ref', 'project', 'project_title', 'amount', 'phone_number',
                  'provider', 'status', 'transaction_code', 'contribution', 'created_at',
                  'verified_at']
        read_only_fields = fields


class PaymentSerializer(serializers.ModelSerializer):
    project_title = serializers.CharField(source='contribution.project.title',
                                          read_only=True, default=None)

    class Meta:
        model = Payment
        fields = ['id', 'contribution', 'project_title', 'provider', 'phone_number',
                  'amount', 'reference', 'status', 'created_at', 'updated_at']
        read_only_fields = fields