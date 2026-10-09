from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ContactInfo, ContactMessage
from .serializers import ContactInfoSerializer, ContactMessageSerializer


class ContactView(APIView):
    """Page contact : sert les coordonnees de l'association (GET) et recoit
    les messages du formulaire (POST). Les deux acces sont publics."""
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(ContactInfoSerializer(ContactInfo.load()).data)

    def post(self, request):
        serializer = ContactMessageSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'detail': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response({'created': True}, status=status.HTTP_201_CREATED)