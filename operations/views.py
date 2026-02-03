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


class CustomPageNumberPagination(PageNumberPagination):
    def get_paginated_response(self, data):
        response = super().get_paginated_response(data)
        response.data['page'] = self.page.number
        response.data['page_size'] = self.page.paginator.per_page
        return response
# from .ml_engine import DatingRecommendationEngine
from firebase_admin import credentials, storage,auth
import os
import os
from datetime import datetime
import requests
import redis
from rest_framework import status
from urllib.parse import quote
from .models import ProfileView, UserInteraction, UserPreferenceProfile, PhoneOTP


def send_sms_native(mobile, message, senderid="Mazale", schedule=None, unicode=None, group_id=None):
    """
    Send SMS using SmsNative API following their documentation.
    Builds the URL directly as shown in the documentation example.

    Parameters:
    - mobile: Single number or comma-separated numbers (e.g., "256750123456" or "256750123456,256701123456")
    - message: The SMS message text
    - senderid: Sender name (default: "Mazale")
    - schedule: Optional scheduling in format "yyyy:mm:dd:hh:mm:ss"
    - unicode: Optional unicode setting (1 or 2)
    - group_id: Optional group IDs for sending to groups

    Returns:
    - dict: Response with success status and details
    """
    # Build URL directly as per documentation
    base_url = "http://www.smsnative.com/sendsms.php"
    params = f"user=Mazale&password=jklasdzc.@Ll6442369123..&mobile={mobile}&senderid={senderid}&message={message}"

    # Add optional parameters
    if group_id:
        params += f"&group_id={group_id}"
    if unicode:
        params += f"&unicode={unicode}"
    if schedule:
        params += f"&schedule={schedule}"

    full_url = f"{base_url}?{params}"

    try:
        response = requests.get(full_url)
        print(response)
        # Check response codes as per SmsNative documentation
        if "1111" in response.text:
            return {
                "success": True,
                "message": "SMS Submitted Successfully",
                "response_code": "1111",
                "details": response.text
            }
        elif "1001" in response.text:
            return {
                "success": False,
                "error": "Invalid URL",
                "response_code": "1001",
                "details": response.text
            }
        elif "1005" in response.text:
            return {
                "success": False,
                "error": "Invalid username or password",
                "response_code": "1005",
                "details": response.text
            }
        elif "1010" in response.text:
            return {
                "success": False,
                "error": "Account expired",
                "response_code": "1010",
                "details": response.text
            }
        elif "1015" in response.text:
            return {
                "success": False,
                "error": "Insufficient SMS Credits",
                "response_code": "1015",
                "details": response.text
            }
        elif "1020" in response.text:
            return {
                "success": False,
                "error": "Invalid Sender",
                "response_code": "1020",
                "details": response.text
            }
        elif "1025" in response.text:
            return {
                "success": False,
                "error": "Invalid Schedule Time",
                "response_code": "1025",
                "details": response.text
            }
        elif "1050" in response.text:
            return {
                "success": False,
                "error": "Other error",
                "response_code": "1050",
                "details": response.text
            }
        else:
            return {
                "success": False,
                "error": "Unknown response",
                "details": response.text
            }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


from .models import (
    User, ProfileLike, Match, Conversation, Message,
    Moment, MomentLike, Comment, Gift, UserGift,
    Transaction, Withdrawal, Notification
)
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, UserSerializer,
    UserProfileSerializer, ProfileLikeSerializer, MatchSerializer,
    ConversationSerializer, MessageSerializer, MomentSerializer,
    MomentLikeSerializer, CommentSerializer, GiftSerializer,
    UserGiftSerializer, TransactionSerializer, WithdrawalSerializer,
    NotificationSerializer, PhoneOTPRequestSerializer, PhoneOTPVerifySerializer,
    LoginSerializer
)



@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    """Register a new user - requires OTP verification first"""
    print("new user registration")
    print(request.data)
    phone_number = request.data.get('phone_number')
    otp_code = request.data.get('otp_code')

    if not phone_number:
        return Response({'error': 'Phone number is required'}, status=status.HTTP_400_BAD_REQUEST)

    # Step 1: If no OTP code provided, send OTP
    if not otp_code:
        # Check if phone number is already registered
        if User.objects.filter(phone_number=phone_number).exists():
            return Response({'error': 'Phone number already registered'}, status=status.HTTP_400_BAD_REQUEST)

        # Delete any existing OTP for this phone number
        PhoneOTP.objects.filter(phone_number=phone_number).delete()

        # Create new OTP
        otp_obj = PhoneOTP.objects.create(phone_number=phone_number)

        # Send SMS using SmsNative API
        sms_result = send_sms_native(
            mobile=phone_number,
            message=f"Your Mazale verification code is: {otp_obj.otp_code}",
            senderid="Mazale"
        )

        if sms_result["success"]:
            return Response({
                'message': 'OTP sent to your phone number. Please verify to complete registration.',
                'phone_number': phone_number,
                'requires_otp': True
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'error': f'Failed to send OTP: {sms_result["error"]}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Step 2: OTP code provided, verify and register user
    try:
        # Verify OTP
        otp_obj = PhoneOTP.objects.get(phone_number=phone_number, otp_code=otp_code)
        
        if otp_obj.is_expired():
            otp_obj.delete()
            return Response({'error': 'OTP has expired'}, status=status.HTTP_400_BAD_REQUEST)

        # OTP is valid, delete it
        otp_obj.delete()

        # Handle image uploads before registration
        user_images = []
        if request.FILES.getlist('user_images'):
            try:
                bucket = storage.bucket()

                for index, photo in enumerate(request.FILES.getlist('user_images')):
                    # Process image
                    img = Image.open(photo)
                    if img.mode in ("RGBA", "P"):
                        img = img.convert("RGB")

                    # Add watermark
                    draw = ImageDraw.Draw(img)
                    width, height = img.size
                    text = "Mazale Dating App"
                    font_size = int(width * 0.03)
                    try:
                        font = ImageFont.truetype("arial.ttf", font_size)
                    except:
                        font = ImageFont.load_default()

                    bbox = draw.textbbox((0, 0), text, font=font)
                    textwidth, textheight = bbox[2] - bbox[0], bbox[3] - bbox[1]
                    x = width - textwidth - 20
                    y = height - textheight - 20
                    draw.text((x+1, y+1), text, font=font, fill=(0, 0, 0))
                    draw.text((x, y), text, font=font, fill=(255, 255, 255))

                    # Save to BytesIO
                    temp_io = BytesIO()
                    img.save(temp_io, format="JPEG", quality=90)
                    temp_io.seek(0)

                    # Upload to Firebase
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    firebase_path = f'users/{phone_number}/profile_{timestamp}_{index}.jpg'
                    blob = bucket.blob(firebase_path)
                    blob.upload_from_file(temp_io, content_type="image/jpeg")
                    blob.make_public()
                    user_images.append(blob.public_url)

            except Exception as e:
                print(f"Image upload error: {str(e)}")
                return Response(
                    {"error": f"Failed to upload images: {str(e)}"}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        # Prepare user data for serializer
        # Create a clean dictionary without file objects
        user_data = {}
        for key, value in request.data.items():
            if key != 'user_images':  # Skip the file objects
                user_data[key] = value
        
        # Add the uploaded image URLs as a list
        if user_images:
            user_data['user_images'] = user_images
        
        print(f"User data being sent to serializer: {user_data}")

        # Create user
        serializer = UserLoginSerializer(data=user_data)
        if serializer.is_valid():
            user = serializer.save()

            # Generate JWT tokens
            refresh = RefreshToken()
            refresh[jwt_settings.USER_ID_CLAIM] = getattr(user, jwt_settings.USER_ID_FIELD, 'id')
            user.token = str(refresh.access_token)
            user.refresh_token = str(refresh)
            user.save()

            return Response({
                'message': 'User registered successfully',
                'user': UserSerializer(user).data,
                'token': user.token,
                'refresh_token': user.refresh_token
            }, status=status.HTTP_201_CREATED)
        
        print(f"Serializer errors: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    except PhoneOTP.DoesNotExist:
        return Response({'error': 'Invalid OTP code'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def request_phone_otp(request):
    """Request OTP for phone number registration"""
    serializer = PhoneOTPRequestSerializer(data=request.data)
    if serializer.is_valid():
        phone_number = serializer.validated_data['phone_number']

        PhoneOTP.objects.filter(phone_number=phone_number).delete()

        # Create new OTP
        otp_obj = PhoneOTP.objects.create(phone_number=phone_number)
        print(otp_obj.otp_code)

        # Send SMS using SmsNative API
        sms_result = send_sms_native(
            mobile=phone_number,
            message=f"Your Mazale verification code is: {otp_obj.otp_code}",
            senderid="Mazale"
        )

        if sms_result["success"]:
            return Response({
                'message': 'OTP sent successfully',
                'phone_number': phone_number
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'error': f'Failed to send SMS: {sms_result["error"]}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_phone_otp(request):
    """Verify OTP for phone number"""
    serializer = PhoneOTPVerifySerializer(data=request.data)
    if serializer.is_valid():
        phone_number = serializer.validated_data['phone_number']
        otp_code = serializer.validated_data['otp_code']

        try:
            otp_obj = PhoneOTP.objects.get(phone_number=phone_number, otp_code=otp_code)
            if otp_obj.is_expired():
                return Response({'error': 'OTP has expired'}, status=status.HTTP_400_BAD_REQUEST)
            otp_obj.verified=True
            otp_obj.save()
            # OTP is valid, delete it and allow registration
            return Response({
                'message': 'OTP verified successfully',
                'phone_number': phone_number,
                'verified': True
            }, status=status.HTTP_200_OK)

        except PhoneOTP.DoesNotExist:
            return Response({'error': 'Invalid OTP'}, status=status.HTTP_400_BAD_REQUEST)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_user(request):
    """Login user with phone_number/email and password"""
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        phone_number = serializer.validated_data.get('phone_number')
        email = serializer.validated_data.get('email')
        password = serializer.validated_data['password']

        user = None
        if phone_number:
            user = User.objects.filter(phone_number=phone_number).first()
        elif email:
            user = User.objects.filter(email=email).first()

        if user and check_password(password, user.password):
            refresh = RefreshToken()
            refresh[jwt_settings.USER_ID_CLAIM] = getattr(user, jwt_settings.USER_ID_FIELD, 'id')
            user.token = str(refresh.access_token)
            user.refresh_token = str(refresh)
            user.online = True
            user.save()
            print(user.token)
            print(user.refresh_token)
            print(user.first_name)
            print(user.last_name)
            return Response({
                'token': user.token,
                'id': user.id,
                'first_name': user.first_name,
                'last_name': user.last_name
            }, status=status.HTTP_200_OK)

        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_user(request):
    """Logout user"""
    user = request.user
    user.online = False
    user.save()
    return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)



class UserListView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination

    def get(self, request):
        """List all users with pagination"""
        print("fetching all users")
        users = User.objects.filter(gender__isnull=False).exclude(gender=request.user.gender)
        paginator = self.pagination_class()
        paginated_users = paginator.paginate_queryset(users, request)
        serializer = UserSerializer(paginated_users, many=True)

        # Update user's current page after successful pagination
        if hasattr(paginator, 'page') and paginator.page:
            request.user.current_page = paginator.page.number
            request.user.save(update_fields=['current_page'])

        return paginator.get_paginated_response(serializer.data)


class UserProfileUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        """Get current user profile"""
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
    
    def put(self, request):
        """Update current user profile"""
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProfileLikeListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """List likes made by current user"""
        likes = ProfileLike.objects.filter(liker=request.user)
        serializer = ProfileLikeSerializer(likes, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        """Like a user's profile"""
        liker = request.user
        liked_user_id = request.data.get('liked_user')
        superlike = request.data.get('superlike', False)
        if liker.id == liked_user_id:
            return Response({'error': 'Cannot like your own profile'}, status=status.HTTP_400_BAD_REQUEST)
        if ProfileLike.objects.filter(liker=liker, liked_user_id=liked_user_id).exists():
            return Response({'error': 'Already liked'}, status=status.HTTP_400_BAD_REQUEST)
        
        profile_like = ProfileLike.objects.create(
            liker=liker,
            liked_user_id=liked_user_id,
            superlike=superlike
        )
        
        mutual_like = ProfileLike.objects.filter(
            liker_id=liked_user_id,
            liked_user_id=liker.id
        ).exists()
        
        response_data = ProfileLikeSerializer(profile_like).data
        
        if mutual_like:
       
            match = Match.objects.create(
                user1=liker,
                user2_id=liked_user_id
            )
            response_data['match'] = MatchSerializer(match).data
            response_data['is_match'] = True
        else:
            response_data['is_match'] = False
        
        return Response(response_data, status=status.HTTP_201_CREATED)


class ProfileLikeDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk):
        """Get profile like details"""
        profile_like = get_object_or_404(ProfileLike, pk=pk)
        serializer = ProfileLikeSerializer(profile_like)
        return Response(serializer.data)
    
    def delete(self, request, pk):
        """Unlike a profile"""
        profile_like = get_object_or_404(ProfileLike, pk=pk)
        if profile_like.liker == request.user:
            profile_like.delete()
            return Response({'message': 'Profile unliked'}, status=status.HTTP_204_NO_CONTENT)
        return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)


class ProfileLikeReceivedView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get likes received by current user"""
        likes = ProfileLike.objects.filter(liked_user=request.user)
        serializer = ProfileLikeSerializer(likes, many=True)
        return Response(serializer.data)



class MatchListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """List all matches for current user"""
        user = request.user
        matches = Match.objects.filter(
            Q(user1=user) | Q(user2=user)
        ).order_by('-created_at')
        serializer = MatchSerializer(matches, many=True)
        return Response(serializer.data)


class MatchDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk):
        """Get match details"""
        match = get_object_or_404(Match, pk=pk)
        serializer = MatchSerializer(match)
        return Response(serializer.data)


class MatchMarkSeenView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk):
        """Mark match as seen"""
        match = get_object_or_404(Match, pk=pk)
        user = request.user
        
        if match.user1 == user:
            match.seen_by_user1 = True
        elif match.user2 == user:
            match.seen_by_user2 = True
        else:
            return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
        
        match.save()
        return Response({'message': 'Match marked as seen'})


class NewMatchesView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get unseen matches"""
        user = request.user
        matches = Match.objects.filter(
            Q(user1=user, seen_by_user1=False) | Q(user2=user, seen_by_user2=False)
        )
        serializer = MatchSerializer(matches, many=True)
        return Response(serializer.data)



class ConversationListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """List all conversations for current user"""
        conversations = Conversation.objects.filter(
            participants=request.user
        ).order_by('-updated_at')
        serializer = ConversationSerializer(conversations, many=True, context={'request': request})
        return Response(serializer.data)
    
    def post(self, request):
        """Create or get existing conversation"""
        participant_ids = request.data.get('participants', [])
        if len(participant_ids) < 1:
            return Response({'error': 'Conversation must have 2 participants'}, status=status.HTTP_400_BAD_REQUEST)
        if request.user.id not in participant_ids:
            participant_ids.append(request.user.id)
        
        conversations = Conversation.objects.filter(participants__id=request.user.id)
        for conv in conversations:
            conv_participant_ids = set(conv.participants.values_list('id', flat=True))
            if conv_participant_ids == set(participant_ids):
                serializer = ConversationSerializer(conv, context={'request': request})
                return Response(serializer.data)
        
        conversation = Conversation.objects.create()
        conversation.participants.set(participant_ids)
        
        serializer = ConversationSerializer(conversation, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ConversationDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk):
        """Get conversation details"""
        conversation = get_object_or_404(Conversation, pk=pk)
        serializer = ConversationSerializer(conversation, context={'request': request})
        return Response(serializer.data)
    
    def put(self, request, pk):
        """Update conversation"""
        conversation = get_object_or_404(Conversation, pk=pk)
        serializer = ConversationSerializer(conversation, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        """Delete conversation"""
        conversation = get_object_or_404(Conversation, pk=pk)
        conversation.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def verify_token(request):
    """Verify JWT token and return user data"""
    user = request.user
    return Response({
        'id': user.id,
        'user_id': user.id,
        'username': user.first_name,
        'lastname': user.last_name,
        'googleid': user.google_id,
        'email': user.email,
        'phone_number': user.phone_number,
    }, status=200)


class MessageListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """List messages"""
        conversation_id = request.query_params.get('conversation')
        if conversation_id:
            messages = Message.objects.filter(conversation_id=conversation_id).order_by('created_at')
        else:
            messages = Message.objects.filter(
                Q(sender=request.user) | Q(receiver=request.user)
            ).order_by('-created_at')
        
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        """Send a message"""
        data = request.data.copy()
        data['sender'] = request.user.id
        
        serializer = MessageSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MessageDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk):
        """Get message details"""
        message = get_object_or_404(Message, pk=pk)
        serializer = MessageSerializer(message)
        return Response(serializer.data)
    
    def put(self, request, pk):
        """Update message"""
        message = get_object_or_404(Message, pk=pk)
        serializer = MessageSerializer(message, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        """Delete message"""
        message = get_object_or_404(Message, pk=pk)
        message.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MessageMarkSeenView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk):
        """Mark message as seen"""
        message = get_object_or_404(Message, pk=pk)
        if message.receiver == request.user:
            message.seen = True
            message.save()
            return Response({'message': 'Message marked as seen'})
        return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)


class MessageMarkConversationSeenView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Mark all messages in a conversation as seen"""
        conversation_id = request.data.get('conversation_id')
        updated = Message.objects.filter(
            conversation_id=conversation_id,
            receiver=request.user,
            seen=False
        ).update(seen=True)
        return Response({'message': f'{updated} messages marked as seen'})

import os
from io import BytesIO
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from django.core.files.base import ContentFile
from rest_framework.response import Response
from rest_framework import status


class MomentListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """List moments"""
        queryset = Moment.objects.all().order_by('-created_at')        
        serializer = MomentSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)
    
    def post(self, request):
    
        # 1. Extract files from the request
        # Flutter sends these as multipart/form-data
        images = request.FILES.getlist('images')
        photo_urls = []
        
        # 2. Upload to Firebase only if images exist
        if images:
            try:
                bucket = storage.bucket()
                
                for index, photo in enumerate(images):
                    # --- WATERMARK PROCESS START ---
                    # 1. Open the image
                    img = Image.open(photo)
                    if img.mode in ("RGBA", "P"):
                        img = img.convert("RGB")
                    
                    # 2. Prepare Drawing context
                    draw = ImageDraw.Draw(img)
                    width, height = img.size
                    
                    # 3. Define text and dynamic font size (e.g., 3% of image width)
                    text = "Mazale Dating App"
                    font_size = int(width * 0.03)
                    
                    # Note: On many servers, you might need a full path to a .ttf file
                    # If this fails, it will default to a tiny standard font
                    try:
                        font = ImageFont.truetype("arial.ttf", font_size)
                    except:
                        font = ImageFont.load_default()

                    # 4. Position text (Bottom Right with padding)
                    margin = 20
                    # Using textbbox for Pillow 10.0.0+ compatibility
                    bbox = draw.textbbox((0, 0), text, font=font)
                    textwidth, textheight = bbox[2] - bbox[0], bbox[3] - bbox[1]
                    x = width - textwidth - margin
                    y = height - textheight - margin
                    
                    # 5. Draw a subtle shadow/outline for readability and then the text
                    draw.text((x+1, y+1), text, font=font, fill=(0, 0, 0)) # Shadow
                    draw.text((x, y), text, font=font, fill=(255, 255, 255)) # White text
                    
                    # 6. Save modified image to a BytesIO object
                    temp_io = BytesIO()
                    img.save(temp_io, format="JPEG", quality=90)
                    temp_io.seek(0)
                    # --- WATERMARK PROCESS END ---

                    # Generate a unique filename
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    file_extension = ".jpg" # Since we converted to RGB/JPEG
                    firebase_path = f'moments/{request.user.id}/{timestamp}_{index}{file_extension}'
                    
                    # Perform Upload using the in-memory file
                    blob = bucket.blob(firebase_path)
                    blob.upload_from_file(temp_io, content_type="image/jpeg")
                    
                    blob.make_public()
                    photo_urls.append(blob.public_url)
                    
            except Exception as e:
                print(f"Firebase Storage Error: {str(e)}")
                return Response({"error": "Failed to upload images"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 3. Construct a CLEAN Python Dictionary
        # We avoid using request.data.copy() directly to prevent QueryDict nesting issues
        moment_data = {
            "owner": request.user.id,
            "tagline": request.data.get('tagline', ''),
            "images": photo_urls  # This is now a clean Python list: ['url1', 'url2']
        }

        # 4. Serialize and Save
        serializer = MomentSerializer(data=moment_data, context={'request': request})
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        # 5. Debugging output if validation fails
        print("Serializer Errors:", serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MomentDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk):
        """Get moment details"""
        moment = get_object_or_404(Moment, pk=pk)
        serializer = MomentSerializer(moment, context={'request': request})
        return Response(serializer.data)
    
    def put(self, request, pk):
        """Update moment"""
        moment = get_object_or_404(Moment, pk=pk)
        serializer = MomentSerializer(moment, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        """Delete a moment (only owner can delete)"""
        moment = get_object_or_404(Moment, pk=pk)
        if moment.owner != request.user:
            return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
        moment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MomentLikeView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk):
        """Like a moment"""
        moment = get_object_or_404(Moment, pk=pk)
        user = request.user
        like, created = MomentLike.objects.get_or_create(moment=moment, user=user)
        
        if created:
            moment.likes_count += 1
            moment.save()
            return Response({'message': 'Moment liked'}, status=status.HTTP_201_CREATED)
        
        return Response({'message': 'Already liked'}, status=status.HTTP_200_OK)


class MomentUnlikeView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk):
        """Unlike a moment"""
        moment = get_object_or_404(Moment, pk=pk)
        user = request.user
        
        deleted = MomentLike.objects.filter(moment=moment, user=user).delete()
        
        if deleted[0] > 0:
            moment.likes_count = max(0, moment.likes_count - 1)
            moment.save()
            return Response({'message': 'Moment unliked'})
        
        return Response({'message': 'Not liked'}, status=status.HTTP_400_BAD_REQUEST)


class MomentFeedView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get moment feed from matches and followed users"""
        user = request.user

        matches = Match.objects.filter(Q(user1=user) | Q(user2=user))
        matched_user_ids = []
        for match in matches:
            matched_user_ids.append(match.user2.id if match.user1 == user else match.user1.id)
        
        moments = Moment.objects.filter(
            Q(owner__id__in=matched_user_ids) | Q(owner=user)
        ).order_by('-created_at')[:50]
        
        serializer = MomentSerializer(moments, many=True, context={'request': request})
        return Response(serializer.data)



class CommentListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """List comments"""
        moment_id = request.query_params.get('moment_id')

        if moment_id == None:
            return Response({'error': 'moment_id query parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
        moment_exits = Moment.objects.filter(id=moment_id).first()
        if not moment_exits:
            return Response({'error': 'Moment not found'}, status=status.HTTP_404_NOT_FOUND)
        
        comments = Comment.objects.filter(moment_id=moment_id).order_by('created_at')
        
        serializer = CommentSerializer(comments, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        """Create a comment"""
        data = request.data.copy()
        data['author'] = request.user.id
        
        serializer = CommentSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CommentDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk):
        """Get comment details"""
        comment = get_object_or_404(Comment, pk=pk)
        serializer = CommentSerializer(comment)
        return Response(serializer.data)
    
    def put(self, request, pk):
        """Update comment"""
        comment = get_object_or_404(Comment, pk=pk)
        serializer = CommentSerializer(comment, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        """Delete a comment (only author can delete)"""
        comment = get_object_or_404(Comment, pk=pk)
        if comment.author != request.user:
            return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
        comment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)



class GiftListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """List all gifts"""
        gifts = Gift.objects.all()
        serializer = GiftSerializer(gifts, many=True)
        return Response(serializer.data)


class GiftDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk):
        """Get gift details"""
        gift = get_object_or_404(Gift, pk=pk)
        serializer = GiftSerializer(gift)
        return Response(serializer.data)


class GiftCategoriesView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get gifts grouped by value ranges"""
        low = Gift.objects.filter(value__lt=200)
        medium = Gift.objects.filter(value__gte=200, value__lt=500)
        high = Gift.objects.filter(value__gte=500)
        
        return Response({
            'low': GiftSerializer(low, many=True).data,
            'medium': GiftSerializer(medium, many=True).data,
            'high': GiftSerializer(high, many=True).data
        })



class UserGiftListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """List user's gifts"""
        user_gifts = UserGift.objects.filter(user=request.user)
        serializer = UserGiftSerializer(user_gifts, many=True)
        print("User gifts fetched")
        print(serializer.data)
        return Response(serializer.data)


class UserGiftDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk):
        """Get user gift details"""
        user_gift = get_object_or_404(UserGift, pk=pk)
        serializer = UserGiftSerializer(user_gift)
        return Response(serializer.data)


class UserGiftPurchaseView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Purchase a gift"""
        gift_id = request.data.get('gift_id')
        quantity = request.data.get('quantity', 1)
        
        try:
            gift = Gift.objects.get(id=gift_id)
        except Gift.DoesNotExist:
            return Response({'error': 'Gift not found'}, status=status.HTTP_404_NOT_FOUND)
        
        user_gift, created = UserGift.objects.get_or_create(
            user=request.user,
            gift=gift,
            defaults={'quantity': quantity}
        )
        
        if not created:
            user_gift.quantity += int(quantity)
            user_gift.save()
        
        serializer = UserGiftSerializer(user_gift)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class UserGiftSendView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Send a gift to another user"""
        gift_id = request.data.get('gift_id')
        receiver_id = request.data.get('receiver_id')
        quantity = request.data.get('quantity', 1)
        
        try:
            user_gift = UserGift.objects.get(user=request.user, gift_id=gift_id)
        except UserGift.DoesNotExist:
            return Response({'error': 'You do not own this gift'}, status=status.HTTP_400_BAD_REQUEST)
        
        if user_gift.quantity < quantity:
            return Response({'error': 'Insufficient quantity'}, status=status.HTTP_400_BAD_REQUEST)
        
        user_gift.quantity -= quantity
        if user_gift.quantity == 0:
            user_gift.delete()
        else:
            user_gift.save()
        
        receiver_gift, created = UserGift.objects.get_or_create(
            user_id=receiver_id,
            gift_id=gift_id,
            defaults={'quantity': quantity}
        )
        
        if not created:
            receiver_gift.quantity += quantity
            receiver_gift.save()
        
        return Response({'message': 'Gift sent successfully'})



class TransactionListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """List user's transactions"""
        transactions = Transaction.objects.filter(user=request.user).order_by('-created_at')
        serializer = TransactionSerializer(transactions, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        """Create a transaction"""
        data = request.data.copy()
        data['user'] = request.user.id
        
        serializer = TransactionSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TransactionDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk):
        """Get transaction details"""
        transaction = get_object_or_404(Transaction, pk=pk)
        serializer = TransactionSerializer(transaction)
        return Response(serializer.data)


class TransactionStatsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get transaction statistics"""
        transactions = Transaction.objects.filter(user=request.user)
        total_amount = sum(t.amount for t in transactions)
        fulfilled_count = transactions.filter(fulfilled=True).count()
        pending_count = transactions.filter(fulfilled=False).count()
        
        return Response({
            'total_transactions': transactions.count(),
            'total_amount': total_amount,
            'fulfilled': fulfilled_count,
            'pending': pending_count
        })



class WithdrawalListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """List user's withdrawals"""
        withdrawals = Withdrawal.objects.filter(user=request.user).order_by('-created_at')
        serializer = WithdrawalSerializer(withdrawals, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        """Request a withdrawal"""
        data = request.data.copy()
        data['user'] = request.user.id
        
        serializer = WithdrawalSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class WithdrawalDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk):
        """Get withdrawal details"""
        withdrawal = get_object_or_404(Withdrawal, pk=pk)
        serializer = WithdrawalSerializer(withdrawal)
        return Response(serializer.data)


class WithdrawalPendingView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get pending withdrawals"""
        withdrawals = Withdrawal.objects.filter(user=request.user, approved=False)
        serializer = WithdrawalSerializer(withdrawals, many=True)
        return Response(serializer.data)


class WithdrawalApprovedView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get approved withdrawals"""
        withdrawals = Withdrawal.objects.filter(user=request.user, approved=True)
        serializer = WithdrawalSerializer(withdrawals, many=True)
        return Response(serializer.data)



class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """List notifications"""
        user = request.user
        notifications = Notification.objects.filter(
            Q(user=user) | Q(is_global=True)
        ).order_by('-created_at')
        serializer = NotificationSerializer(notifications, many=True)
        return Response(serializer.data)


class NotificationDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk):
        """Get notification details"""
        notification = get_object_or_404(Notification, pk=pk)
        serializer = NotificationSerializer(notification)
        return Response(serializer.data)


class NotificationMarkSeenView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk):
        """Mark notification as seen"""
        notification = get_object_or_404(Notification, pk=pk)
        if notification.user == request.user or notification.is_global:
            notification.seen = True
            notification.save()
            return Response({'message': 'Notification marked as seen'})
        return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)


class NotificationMarkAllSeenView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Mark all notifications as seen"""
        updated = Notification.objects.filter(
            Q(user=request.user) | Q(is_global=True),
            seen=False
        ).update(seen=True)
        return Response({'message': f'{updated} notifications marked as seen'})


class NotificationUnreadCountView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get count of unread notifications"""
        user = request.user
        count = Notification.objects.filter(
            Q(user=user) | Q(is_global=True),
            seen=False
        ).count()
        return Response({'unread_count': count})
    


class SmartUserListView(APIView):
    """ML-powered user recommendations"""
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination

    def get(self, request):
        """Get personalized user recommendations"""
        # engine = DatingRecommendationEngine(request.user)

        limit = int(request.query_params.get('limit', 10))
        # refresh = request.query_params.get('refresh', 'false').lower() == 'true'

        # now = timezone.now()
        # if not request.user.last_recommendation_update or \
        #    (now - request.user.last_recommendation_update).days >= 1 or refresh:
        #     engine.update_user_preferences()

        # recommended_users = engine.get_recommended_users(limit=limit)
        recommended_users = User.objects.filter(gender__isnull=False).exclude(gender=request.user.gender)[:limit]

        paginator = self.pagination_class()
        paginated_users = paginator.paginate_queryset(recommended_users, request)
        serializer = UserSerializer(paginated_users, many=True)

        # Update user's current page after successful pagination
        if hasattr(paginator, 'page') and paginator.page:
            request.user.current_page = paginator.page.number
            request.user.save(update_fields=['current_page'])

        return paginator.get_paginated_response(serializer.data)



class ProfileViewTrackingView(APIView):
    """Track detailed profile viewing behavior"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Log profile view with engagement metrics"""
        viewed_user_id = request.data.get('viewed_user_id')
        view_duration = request.data.get('view_duration', 0)
        scrolled_to_bottom = request.data.get('scrolled_to_bottom', False)
        viewed_images_count = request.data.get('viewed_images_count', 0)
        clicked_social_links = request.data.get('clicked_social_links', False)
        
        if not viewed_user_id:
            return Response({'error': 'viewed_user_id required'}, status=400)
        
        profile_view = ProfileView.objects.create(
            viewer=request.user,
            viewed_user_id=viewed_user_id,
            view_duration=view_duration,
            scrolled_to_bottom=scrolled_to_bottom,
            viewed_images_count=viewed_images_count,
            clicked_social_links=clicked_social_links
        )
        
        engagement_score = self._calculate_view_engagement(
            view_duration, scrolled_to_bottom, viewed_images_count, clicked_social_links
        )
        
        UserInteraction.objects.create(
            user=request.user,
            interaction_type='profile_view',
            target_user_id=viewed_user_id,
            engagement_score=engagement_score
        )
        
        return Response({'message': 'Profile view tracked', 'engagement_score': engagement_score})
    
    def _calculate_view_engagement(self, duration, scrolled, images_viewed, clicked_links):
        """Calculate engagement score from viewing behavior"""
        score = 0
        
        if duration >= 60:
            score += 40
        elif duration >= 30:
            score += 30
        elif duration >= 10:
            score += 20
        else:
            score += 10
        
        if scrolled:
            score += 20
        if images_viewed >= 3:
            score += 25
        elif images_viewed >= 1:
            score += 15
        if clicked_links:
            score += 15
        
        return min(score, 100)



class EnhancedProfileLikeView(APIView):
    """Enhanced like tracking with ML insights"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Like a user's profile with ML tracking"""
        liker = request.user
        liked_user_id = request.data.get('liked_user')
        superlike = request.data.get('superlike', False)
        
        if liker.id == liked_user_id:
            return Response({'error': 'Cannot like your own profile'}, status=400)
        
        if ProfileLike.objects.filter(liker=liker, liked_user_id=liked_user_id).exists():
            return Response({'error': 'Already liked'}, status=400)
        
        profile_like = ProfileLike.objects.create(
            liker=liker,
            liked_user_id=liked_user_id,
            superlike=superlike
        )
        
        UserInteraction.objects.create(
            user=liker,
            interaction_type='superlike' if superlike else 'like',
            target_user_id=liked_user_id,
            engagement_score=100 if superlike else 75
        )
        
        mutual_like = ProfileLike.objects.filter(
            liker_id=liked_user_id,
            liked_user_id=liker.id
        ).exists()
        
        response_data = ProfileLikeSerializer(profile_like).data
        
        if mutual_like:
            match = Match.objects.create(
                user1=liker,
                user2_id=liked_user_id
            )
            response_data['match'] = MatchSerializer(match).data
            response_data['is_match'] = True
            
            liked_user = User.objects.get(id=liked_user_id)
            liker.recommendation_boost = min(liker.recommendation_boost * 1.1, 2.0)
            liked_user.recommendation_boost = min(liked_user.recommendation_boost * 1.1, 2.0)
            liker.save()
            liked_user.save()
        else:
            response_data['is_match'] = False
        
        like_count = ProfileLike.objects.filter(liker=liker).count()
        # if like_count % 5 == 0:
        #     engine = DatingRecommendationEngine(liker)
        #     engine.update_user_preferences()
        
        return Response(response_data, status=201)


class ProfilePassView(APIView):
    """Track when user passes/skips a profile"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Log profile pass for ML learning"""
        passed_user_id = request.data.get('passed_user_id')
        
        if not passed_user_id:
            return Response({'error': 'passed_user_id required'}, status=400)
        
        UserInteraction.objects.create(
            user=request.user,
            interaction_type='pass',
            target_user_id=passed_user_id,
            engagement_score=0
        )
        
        return Response({'message': 'Pass recorded'})



class UserAnalyticsView(APIView):
    """Get user's engagement analytics"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get comprehensive user analytics"""
        user = request.user
        # engine = DatingRecommendationEngine(user)

        profile_views_made = ProfileView.objects.filter(viewer=user)
        profile_views_received = ProfileView.objects.filter(viewed_user=user)

        interactions = UserInteraction.objects.filter(user=user)

        analytics = {
            'engagement_score': user.engagement_score,
            'activity_level': user.activity_level,
            'recommendation_boost': user.recommendation_boost,
            'profile_completeness': 50,  # engine._calculate_profile_completeness(user) * 100,

            'profile_views': {
                'made': profile_views_made.count(),
                'received': profile_views_received.count(),
                'avg_duration': profile_views_made.aggregate(Avg('view_duration'))['view_duration__avg'] or 0,
            },

            'interactions': {
                'total': interactions.count(),
                'likes': interactions.filter(interaction_type='like').count(),
                'superlikes': interactions.filter(interaction_type='superlike').count(),
                'messages': interactions.filter(interaction_type='message_sent').count(),
                'avg_engagement': interactions.aggregate(Avg('engagement_score'))['engagement_score__avg'] or 0,
            },

            'matches': {
                'total': Match.objects.filter(Q(user1=user) | Q(user2=user)).count(),
                'new': Match.objects.filter(
                    Q(user1=user, seen_by_user1=False) | Q(user2=user, seen_by_user2=False)
                ).count(),
            },

            'preferences': {
                'swipe_rate': 0,  # engine.preference_profile.swipe_rate,
                'avg_session_duration': 0,  # engine.preference_profile.avg_session_duration,
                'distance_importance': 0,  # engine.preference_profile.distance_importance,
            }
        }

        return Response(analytics)



class EnhancedMessageListView(APIView):
    """Enhanced message tracking with ML"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Send a message with ML tracking"""
        data = request.data.copy()
        data['sender'] = request.user.id
        
        serializer = MessageSerializer(data=data)
        if serializer.is_valid():
            message = serializer.save()
            
            UserInteraction.objects.create(
                user=request.user,
                interaction_type='message_sent',
                target_user=message.receiver,
                engagement_score=50
            )
            
            if message.conversation:
                message.conversation.updated_at = timezone.now()
                message.conversation.save()
            
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)



class UserBoostView(APIView):
    """Temporarily boost user's visibility"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Apply boost to user profile"""
        duration_hours = int(request.data.get('duration_hours', 1))
        boost_factor = float(request.data.get('boost_factor', 2.0))
        
        user = request.user
        user.recommendation_boost = boost_factor
        user.save()
        
        
        return Response({
            'message': f'Boost applied for {duration_hours} hours',
            'new_boost': user.recommendation_boost
        })


class SimilarUsersView(APIView):
    """Find users similar to a given user"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, user_id):
        """Get users similar to the specified user"""
        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)

        # engine = DatingRecommendationEngine(request.user)

        candidates = User.objects.exclude(
            id__in=[request.user.id, target_user.id]
        ).filter(gender__isnull=False).exclude(gender=request.user.gender)[:50]

        # similar_users = []
        # for candidate in candidates:
        #     similarity = engine._calculate_profile_similarity(candidate, target_user)
        #     if similarity > 0.3:
        #         similar_users.append((similarity, candidate))

        # similar_users.sort(key=lambda x: x[0], reverse=True)

        # results = [user for score, user in similar_users[:10]]
        results = candidates[:10]
        serializer = UserSerializer(results, many=True)

        return Response(serializer.data)



class OptimizeProfileView(APIView):
    """Get suggestions to optimize profile for better matches"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Analyze profile and provide optimization suggestions"""
        user = request.user
        # engine = DatingRecommendationEngine(user)

        suggestions = []

        completeness = 0.5  # engine._calculate_profile_completeness(user)
        if completeness < 0.7:
            suggestions.append({
                'category': 'profile_completeness',
                'message': 'Your profile is only {}% complete. Add more details to get better matches!'.format(
                    int(completeness * 100)
                ),
                'priority': 'high'
            })

        if not user.user_images or len(user.user_images) < 4:
            suggestions.append({
                'category': 'photos',
                'message': 'Add more photos! Profiles with 4+ photos get 3x more matches.',
                'priority': 'high'
            })

        if not user.about or len(user.about) < 100:
            suggestions.append({
                'category': 'bio',
                'message': 'Write a more detailed bio. Profiles with longer bios get 60% more engagement.',
                'priority': 'medium'
            })

        if not user.user_interests or len(user.user_interests) < 3:
            suggestions.append({
                'category': 'interests',
                'message': 'Add at least 3 interests to help us find better matches for you.',
                'priority': 'medium'
            })

        if user.activity_level == 'low':
            suggestions.append({
                'category': 'activity',
                'message': 'Be more active! Log in daily and engage with profiles to improve your visibility.',
                'priority': 'medium'
            })

        # if engine.preference_profile.swipe_rate < 0.1:
        #     suggestions.append({
        #         'category': 'engagement',
        #         'message': 'You\'re very selective! Consider liking more profiles to increase your match potential.',
        #         'priority': 'low'
        #     })

        return Response({
            'profile_score': int(completeness * 100),
            'engagement_score': int(user.engagement_score),
            'suggestions': suggestions,
            'total_suggestions': len(suggestions)
        })

redis_client = redis.from_url(
    'rediss://default:AdGbAAIncDFlNjQ4ZmI2MzZkM2E0M2JlODQ5ZjE2NGQ2ODYyNzA0NHAxNTM2NTk@one-perch-53659.upstash.io:6379',
    ssl_cert_reqs=None,
    decode_responses=True
)


class SocketHandshakeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            user = request.user
            auth_header = request.headers.get('Authorization', '').split()
            if not auth_header or len(auth_header) < 2:
                return Response({"error": "No token found"}, status=400)
            
            token = auth_header[1]
            
            user_data = {
                "id": user.id,
                "first_name": user.first_name or user.username,
                "profile_pic": getattr(user, 'profile_pic_url', '')
            }
            redis_key = f"session:{token}"
            redis_client.setex(
                redis_key,
                86400,
                json.dumps(user_data)
            )

            return Response({
                "message": "Socket session seeded",
                "token": token
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




   
    
class SMSDeliveryEngine(APIView):
    def post(self, request):
        """
        Sends an SMS via SmsNative HTTP API following their documentation.
        Supports all parameters: mobile, message, senderid, schedule, unicode, group_id
        """
        mobile = request.data.get("mobile")
        message = request.data.get("message")
        senderid = request.data.get("senderid", "Mazale")
        schedule = request.data.get("schedule")  # Format: yyyy:mm:dd:hh:mm:ss
        unicode = request.data.get("unicode")    # 1 or 2
        group_id = request.data.get("group_id")  # Comma-separated group IDs

        if not mobile or not message:
            return Response(
                {"error": "Mobile and message fields are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Send SMS using the unified SmsNative function
        sms_result = send_sms_native(
            mobile=mobile,
            message=message,
            senderid=senderid,
            schedule=schedule,
            unicode=unicode,
            group_id=group_id
        )

        if sms_result["success"]:
            return Response({
                "success": True,
                "message": sms_result["message"],
                "response_code": sms_result.get("response_code"),
                "details": sms_result["details"]
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                "success": False,
                "error": sms_result["error"],
                "response_code": sms_result.get("response_code"),
                "details": sms_result.get("details")
            }, status=status.HTTP_400_BAD_REQUEST)