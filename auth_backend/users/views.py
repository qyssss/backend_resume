from django.shortcuts import render
from google.api_core.exceptions import PermissionDenied, InvalidArgument
# Create your views here.
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
# from .firebase_config import db
from common.firebase_utils import get_users_collection
from .serializers import UserSerializer
import jwt
import datetime
from django.conf import settings
# accounts/views.py
from django.contrib.auth.hashers import make_password
# from .forms import RegistrationForm
from django.conf import settings
from google.cloud.firestore_v1 import FieldFilter
from google.cloud import firestore
import google.auth

# 配置详细日志
import logging
# logging.basicConfig(level=logging.DEBUG)
# logger = logging.getLogger(__name__)
class RegisterView(APIView):
    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data

            # 检查邮箱是否已存在
            users_ref = get_users_collection()
            query = users_ref.where(
                filter=FieldFilter("email", "==", data['email'])
            ).limit(1).get()
            #query = users_ref.where('email', '==', data['email']).limit(1).get()
            if query:
                return Response({'error': 'Email already exists'}, status=status.HTTP_400_BAD_REQUEST)

            # 创建新用户
            user_data = {
                'email': data['email'],
                'username': data['username'],
                'password': data['password']
            }
            users_ref.add(user_data)

            return Response({'message': 'User created successfully'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return Response({'error': 'Email and password required'}, status=status.HTTP_400_BAD_REQUEST)
        users_ref = get_users_collection()

        try:
            # 更新后的查询方式
            query = users_ref.where(
                filter=FieldFilter("email", "==", email)
            ).where(
                filter=FieldFilter("password", "==", password)
            ).limit(1).get()
            if not query:
                return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

            # 生成 JWT 令牌
            user = query[0].to_dict()
            payload = {
                'user_id': query[0].id,
                'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
            }
            token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
            return Response({
                'token': token,
                'user_id': query[0].id,
                'username': user['username']
            })
        except Exception as e:
            print("未知错误:", type(e).__name__, e)


class ProfileView(APIView):
    def get(self, request):
        user_id = request.query_params.get('user_id')
        user_ref = get_users_collection().document(user_id).get()

        if not user_ref.exists:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        user_data = user_ref.to_dict()
        return Response({
            'username': user_data['username'],
            'email': user_data['email']
        })