from datetime import date, datetime
import firebase_admin
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User
from .serializers import UserSerializer
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from django.core.files.storage import default_storage
import firebase_admin
from firebase_admin import credentials, storage,auth
import os
from .serializers import UserProfileSerializer


@api_view(['POST'])
@permission_classes([AllowAny])
def google_auth_receiver(request):
    id_token = request.data.get('idToken')
    print(id_token)

    try:
        # Verify the Firebase ID Token
        decoded_token = auth.verify_id_token(id_token)
        google_id = decoded_token['uid']
        email = decoded_token.get('email')
        is_new_user = False
        user = User.objects.filter(google_id=google_id).first()
        print(user)
        if user==None:
            is_new_user = True
            user = User.objects.filter(email=email).first()
            if user:
                user.google_id = google_id
                user.save()
            else:
                # 3. Create new user if they don't exist at all
                full_name = decoded_token.get('name', 'Google User').split(' ')
                user = User.objects.create(
                    google_id=google_id,
                    email=email,
                    first_name=full_name[0],
                    last_name=" ".join(full_name[1:]) if len(full_name) > 1 else "",
                    profile_pic=decoded_token.get('picture'),
                    online=True
                )
                user.set_unusable_password()
                user.save()
                is_new_user = True
        # Generate tokens exactly like your phone login logic
        refresh = RefreshToken.for_user(user)
        user.token = str(refresh.access_token)
        user.refresh_token = str(refresh)
        user.online = True
        user.save()
     
        return Response({
            'message': 'Login successful',
            'user': UserSerializer(user).data,
            'token': user.token,
            'refresh_token': user.refresh_token,
            'is_new_user': user.gender==None,
            'google_id': google_id,
            'id': user.id,
            'firstname': user.first_name,
            'lastname': user.last_name

        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_401_UNAUTHORIZED)
    
@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def upload_photos(request):
    """
    Upload user photos to Firebase and create/update user profile
    """
    try:
        # 1. Extract Data
        google_id = request.data.get('google_id')
        phone_number = request.data.get('phone_number')
        gender = request.data.get('gender')
        birthday = request.data.get('birthday')
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')
        interests_raw = request.data.get('interests', "") 
        # 2. Validate required fields
        if not all([google_id, phone_number, gender, birthday]):
            return Response(
                {'error': 'google_id, phone_number, gender, and birthday are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 3. Handle Birthday and Age logic
        try:
            birthday_date = datetime.strptime(birthday, '%Y-%m-%d').date()
            today = date.today()
            age = today.year - birthday_date.year - ((today.month, today.day) < (birthday_date.month, birthday_date.day))
            
            if age < 18:
                return Response({'error': 'User must be at least 18 years old'}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError:
            return Response({'error': 'Invalid birthday format. Use YYYY-MM-DD'}, status=status.HTTP_400_BAD_REQUEST)

        # 4. Process Interests for JSONField
        # Convert comma-separated string to a list: "coding, sports" -> ["coding", "sports"]
        if isinstance(interests_raw, str) and interests_raw:
            interests_list = [i.strip() for i in interests_raw.split(',') if i.strip()]
        elif isinstance(interests_raw, list):
            interests_list = interests_raw
        else:
            interests_list = []

        # 5. Firebase Storage Upload
        bucket = storage.bucket()
        photo_urls = []
        
        for i in range(1, 5):
            photo_key = f'photo_{i}'
            if photo_key in request.FILES:
                photo = request.FILES[photo_key]
                file_extension = os.path.splitext(photo.name)[1]
                firebase_path = f'user_photos/{google_id}/photo_{i}{file_extension}'
                
                blob = bucket.blob(firebase_path)
                blob.upload_from_file(photo.file, content_type=photo.content_type)
                blob.make_public()
                photo_urls.append(blob.public_url)

        user = User.objects.filter(google_id=google_id).first()
        if not user:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        user.phone_number = phone_number
        user.gender = gender
        user.day = birthday
        user.latitude = latitude
        user.longitude = longitude
        
        # This now saves as a valid JSON list
        user.hopes = interests_list 
        
        # If your user_images is also a JSONField, this works perfectly:
        user.user_images = photo_urls 
        
        user.save()

        return Response({
            'message': 'Profile updated successfully',
            'interests_saved': interests_list
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)