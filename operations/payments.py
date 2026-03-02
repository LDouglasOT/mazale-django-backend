import json
from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.settings import api_settings as jwt_settings
from django.contrib.auth.hashers import check_password
from django.db.models import Q
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404


def subScribeToPremiun(self,request):

    return Response({'success': 'Successfully recieved the payment'}, status=status.HTTP_201_CREATED)

def checkPayment(request):

    return Response({'success': 'Successfully recieved the payment'}, status=status.HTTP_201_CREATED)