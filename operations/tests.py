from django.test import TestCase
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth.hashers import make_password
from .models import User, ProfileLike, Match, Moment, Gift, UserGift


class UserAuthenticationTestCase(APITestCase):
    """Test user authentication endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        self.register_url = '/api/auth/register/'
        self.login_url = '/api/auth/login/'
        self.logout_url = '/api/auth/logout/'
        
        self.user_data = {
            'phone_number': '+256700000000',
            'email': 'test@example.com',
            'password': 'testpass123',
            'confirm_password': 'testpass123',
            'first_name': 'Test',
            'last_name': 'User',
            'gender': 'male'
        }
    
    def test_user_registration(self):
        """Test user can register successfully"""
        response = self.client.post(self.register_url, self.user_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('token', response.data)
        self.assertIn('refresh_token', response.data)
        self.assertIn('user', response.data)
        
        # Check user was created
        self.assertTrue(User.objects.filter(phone_number='+256700000000').exists())
    
    def test_user_login_with_phone(self):
        """Test user can login with phone number"""
        # Create user first
        User.objects.create(
            phone_number='+256700000000',
            password=make_password('testpass123'),
            first_name='Test',
            last_name='User'
        )
        
        login_data = {
            'phone_number': '+256700000000',
            'password': 'testpass123'
        }
        
        response = self.client.post(self.login_url, login_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        self.assertIn('user', response.data)
    
    def test_user_login_with_email(self):
        """Test user can login with email"""
        # Create user first
        User.objects.create(
            email='test@example.com',
            password=make_password('testpass123'),
            first_name='Test',
            last_name='User'
        )
        
        login_data = {
            'email': 'test@example.com',
            'password': 'testpass123'
        }
        
        response = self.client.post(self.login_url, login_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
    
    def test_login_with_wrong_password(self):
        """Test login fails with wrong password"""
        User.objects.create(
            phone_number='+256700000000',
            password=make_password('testpass123'),
            first_name='Test'
        )
        
        login_data = {
            'phone_number': '+256700000000',
            'password': 'wrongpassword'
        }
        
        response = self.client.post(self.login_url, login_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class UserProfileTestCase(APITestCase):
    """Test user profile endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        
        # Create test user
        self.user = User.objects.create(
            phone_number='+256700000000',
            password=make_password('testpass123'),
            first_name='Test',
            last_name='User',
            token='test_token_123'
        )
        
        # Authenticate
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.user.token)
    
    def test_get_current_user_profile(self):
        """Test getting current user profile"""
        response = self.client.get('/api/users/me/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['first_name'], 'Test')
        self.assertEqual(response.data['phone_number'], '+256700000000')
    
    def test_update_profile(self):
        """Test updating user profile"""
        update_data = {
            'about': 'Updated bio',
            'user_interests': ['travel', 'music']
        }
        
        response = self.client.put('/api/users/update_profile/', update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['about'], 'Updated bio')
    
    def test_discover_users(self):
        """Test discovering new users"""
        # Create another user
        User.objects.create(
            phone_number='+256700000001',
            password=make_password('testpass123'),
            first_name='Jane',
            online=True
        )
        
        response = self.client.get('/api/users/discover/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data), 0)


class ProfileLikeTestCase(APITestCase):
    """Test profile like endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        
        # Create test users
        self.user1 = User.objects.create(
            phone_number='+256700000000',
            password=make_password('testpass123'),
            first_name='User1',
            token='token_user1'
        )
        
        self.user2 = User.objects.create(
            phone_number='+256700000001',
            password=make_password('testpass123'),
            first_name='User2'
        )
        
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.user1.token)
    
    def test_like_profile(self):
        """Test liking a profile"""
        like_data = {
            'liked_user': self.user2.id,
            'superlike': False
        }
        
        response = self.client.post('/api/profile-likes/', like_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['is_match'], False)
        
        # Check like was created
        self.assertTrue(
            ProfileLike.objects.filter(liker=self.user1, liked_user=self.user2).exists()
        )
    
    def test_mutual_like_creates_match(self):
        """Test mutual like creates a match"""
        # User2 likes User1 first
        ProfileLike.objects.create(liker=self.user2, liked_user=self.user1)
        
        # User1 likes User2
        like_data = {
            'liked_user': self.user2.id,
            'superlike': False
        }
        
        response = self.client.post('/api/profile-likes/', like_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['is_match'], True)
        self.assertIn('match', response.data)
        
        # Check match was created
        self.assertTrue(
            Match.objects.filter(user1=self.user1, user2=self.user2).exists()
        )


class MomentTestCase(APITestCase):
    """Test moment endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        
        self.user = User.objects.create(
            phone_number='+256700000000',
            password=make_password('testpass123'),
            first_name='Test',
            token='test_token'
        )
        
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.user.token)
    
    def test_create_moment(self):
        """Test creating a moment"""
        moment_data = {
            'tagline': 'Beautiful sunset',
            'hashtag': '#sunset',
            'images': ['url1', 'url2']
        }
        
        response = self.client.post('/api/moments/', moment_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['tagline'], 'Beautiful sunset')
        
        # Check moment was created
        self.assertTrue(Moment.objects.filter(owner=self.user).exists())
    
    def test_like_moment(self):
        """Test liking a moment"""
        moment = Moment.objects.create(
            owner=self.user,
            tagline='Test moment'
        )
        
        response = self.client.post(f'/api/moments/{moment.id}/like/')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check likes count increased
        moment.refresh_from_db()
        self.assertEqual(moment.likes_count, 1)
    
    def test_get_moments(self):
        """Test getting moments feed"""
        Moment.objects.create(owner=self.user, tagline='Moment 1')
        Moment.objects.create(owner=self.user, tagline='Moment 2')
        
        response = self.client.get('/api/moments/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 2)


class GiftTestCase(APITestCase):
    """Test gift endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        
        self.user = User.objects.create(
            phone_number='+256700000000',
            password=make_password('testpass123'),
            first_name='Test',
            token='test_token'
        )
        
        self.gift = Gift.objects.create(
            name='Rose',
            value=100,
            image='rose.png'
        )
        
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.user.token)
    
    def test_get_gifts(self):
        """Test getting available gifts"""
        response = self.client.get('/api/gifts/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data['results']), 0)
    
    def test_purchase_gift(self):
        """Test purchasing a gift"""
        purchase_data = {
            'gift_id': self.gift.id,
            'quantity': 5
        }
        
        response = self.client.post('/api/user-gifts/purchase/', purchase_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['quantity'], 5)
        
        # Check user gift was created
        self.assertTrue(
            UserGift.objects.filter(user=self.user, gift=self.gift).exists()
        )


class MessageTestCase(APITestCase):
    """Test messaging endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        
        self.user1 = User.objects.create(
            phone_number='+256700000000',
            password=make_password('testpass123'),
            first_name='User1',
            token='token1'
        )
        
        self.user2 = User.objects.create(
            phone_number='+256700000001',
            password=make_password('testpass123'),
            first_name='User2'
        )
        
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.user1.token)
    
    def test_create_conversation(self):
        """Test creating a conversation"""
        conversation_data = {
            'participants': [self.user2.id]
        }
        
        response = self.client.post('/api/conversations/', conversation_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)
    
    def test_send_message(self):
        """Test sending a message"""
        # First create conversation
        from .models import Conversation
        conversation = Conversation.objects.create()
        conversation.participants.set([self.user1, self.user2])
        
        message_data = {
            'conversation': conversation.id,
            'receiver': self.user2.id,
            'sms': 'Hello!',
            'is_text': True
        }
        
        response = self.client.post('/api/messages/', message_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['sms'], 'Hello!')


class NotificationTestCase(APITestCase):
    """Test notification endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        
        self.user = User.objects.create(
            phone_number='+256700000000',
            password=make_password('testpass123'),
            first_name='Test',
            token='test_token'
        )
        
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.user.token)
    
    def test_get_notifications(self):
        """Test getting user notifications"""
        from .models import Notification
        
        Notification.objects.create(
            user=self.user,
            message='Test notification',
            header='Test'
        )
        
        response = self.client.get('/api/notifications/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data['results']), 0)
    
    def test_mark_notification_seen(self):
        """Test marking notification as seen"""
        from .models import Notification
        
        notification = Notification.objects.create(
            user=self.user,
            message='Test notification',
            seen=False
        )
        
        response = self.client.post(f'/api/notifications/{notification.id}/mark_seen/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check notification was marked seen
        notification.refresh_from_db()
        self.assertTrue(notification.seen)