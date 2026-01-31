from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from math import radians, sin, cos, sqrt, atan2
from .models import User
import json

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    Returns distance in kilometers
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    # Radius of earth in kilometers
    r = 6371
    
    return r * c

@csrf_exempt
@require_http_methods(["GET", "POST"])
def nearby_users(request):
    """
    Endpoint to get nearby users based on current user's location
    Accepts: GET or POST
    Parameters:
        - latitude (optional): Current latitude, defaults to user's stored location
        - longitude (optional): Current longitude, defaults to user's stored location
        - radius (optional): Search radius in km, defaults to 50
        - limit (optional): Max number of users to return, defaults to 100
    """
    try:
        # Get the authenticated user
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return JsonResponse({'error': 'Invalid authorization header'}, status=401)
        
        token = auth_header.split(' ')[1]
        
        try:
            current_user = User.objects.get(token=token)
        except User.DoesNotExist:
            return JsonResponse({'error': 'Invalid token'}, status=401)
        
        # Get parameters
        if request.method == 'POST':
            data = json.loads(request.body) if request.body else {}
            user_lat = data.get('latitude')
            user_lon = data.get('longitude')
            radius = float(data.get('radius', 50))
            limit = int(data.get('limit', 100))
        else:
            user_lat = request.GET.get('latitude')
            user_lon = request.GET.get('longitude')
            radius = float(request.GET.get('radius', 50))
            limit = int(request.GET.get('limit', 100))
        
        # Use stored location if not provided
        if not user_lat or not user_lon:
            user_lat = current_user.latitude
            user_lon = current_user.longitude
        
        if not user_lat or not user_lon:
            return JsonResponse({
                'error': 'Location not available. Please provide latitude and longitude.'
            }, status=400)
        
        user_lat = float(user_lat)
        user_lon = float(user_lon)
        
        # Update current user's location if provided
        if request.method == 'POST':
            if 'latitude' in data and 'longitude' in data:
                current_user.latitude = str(user_lat)
                current_user.longitude = str(user_lon)
                current_user.save(update_fields=['latitude', 'longitude'])
        
        # Get all users except the current user with valid locations
        all_users = User.objects.exclude(id=current_user.id).filter(
            latitude__isnull=False,
            longitude__isnull=False,
            is_active=True
        ).exclude(
            latitude='',
            longitude=''
        )
        
        # Calculate distances and filter by radius
        nearby_users_data = []
        
        for user in all_users:
            try:
                user_location_lat = float(user.latitude)
                user_location_lon = float(user.longitude)
                
                # Calculate distance
                distance = haversine_distance(
                    user_lat, user_lon,
                    user_location_lat, user_location_lon
                )
                
                # Only include users within the specified radius
                if distance <= radius:
                    # Calculate age
                    age = None
                    if user.year and user.month and user.day:
                        try:
                            from datetime import datetime
                            birth_date = datetime(
                                int(user.year),
                                int(user.month),
                                int(user.day)
                            )
                            today = datetime.now()
                            age = today.year - birth_date.year - (
                                (today.month, today.day) < (birth_date.month, birth_date.day)
                            )
                        except (ValueError, TypeError):
                            age = None
                    
                    # Handle user_interests - convert to comma-separated string if list
                    interests = ""
                    if user.user_interests:
                        if isinstance(user.user_interests, list):
                            interests = ", ".join(user.user_interests)
                        elif isinstance(user.user_interests, str):
                            interests = user.user_interests
                    
                    # Handle user_images
                    images = []
                    if user.user_images:
                        if isinstance(user.user_images, list):
                            images = user.user_images
                        elif isinstance(user.user_images, str):
                            try:
                                images = json.loads(user.user_images)
                            except:
                                images = [user.user_images]
                    
                    nearby_users_data.append({
                        'id': user.id,
                        'first_name': user.first_name or 'User',
                        'last_name': user.last_name or '',
                        'name': f"{user.first_name or 'User'} {user.last_name or ''}".strip(),
                        'age': age,
                        'profile_pic': user.profile_pic or '',
                        'latitude': user_location_lat,
                        'longitude': user_location_lon,
                        'distance': round(distance, 2),
                        'bio': user.about or user.hopes or '',
                        'interests': interests,
                        'gender': user.gender,
                        'online': user.online,
                        'promoted': user.promoted,
                        'engagement_score': user.engagement_score,
                        'activity_level': user.activity_level,
                        'user_images': images,
                        'phone_number': user.phone_number,
                        'email': user.email,
                    })
            except (ValueError, TypeError) as e:
                # Skip users with invalid location data
                continue
        
        # Sort by distance (closest first)
        nearby_users_data.sort(key=lambda x: x['distance'])
        
        # Limit results
        nearby_users_data = nearby_users_data[:limit]
        
        return JsonResponse({
            'success': True,
            'count': len(nearby_users_data),
            'radius_km': radius,
            'your_location': {
                'latitude': user_lat,
                'longitude': user_lon
            },
            'people': nearby_users_data
        })
        
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'success': False
        }, status=500)


# Optional: Endpoint to update user location only
@csrf_exempt
@require_http_methods(["POST"])
def update_location(request):
    """
    Update current user's location
    """
    try:
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return JsonResponse({'error': 'Invalid authorization header'}, status=401)
        
        token = auth_header.split(' ')[1]
        
        try:
            user = User.objects.get(token=token)
        except User.DoesNotExist:
            return JsonResponse({'error': 'Invalid token'}, status=401)
        
        data = json.loads(request.body)
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        
        if not latitude or not longitude:
            return JsonResponse({'error': 'Latitude and longitude required'}, status=400)
        
        user.latitude = str(latitude)
        user.longitude = str(longitude)
        user.save(update_fields=['latitude', 'longitude'])
        
        return JsonResponse({
            'success': True,
            'message': 'Location updated successfully',
            'latitude': latitude,
            'longitude': longitude
        })
        
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'success': False
        }, status=500)


