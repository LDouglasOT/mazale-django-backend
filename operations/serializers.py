from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from .models import (
    User, ProfileLike, Match, Conversation, Message,
    Moment, MomentLike, Comment, Gift, UserGift,
    Transaction, Withdrawal, Notification,ProfileView, UserInteraction, UserPreferenceProfile, PhoneOTP
)

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            'phone_number', 'email', 'password', 'confirm_password',
            'first_name', 'last_name', 'gender', 'day', 'month', 'year',
            'user_images', 'engagement_score', 'recommendation_boost', 'activity_level',
            'compatibility_score', 'profile_completeness',
        ]
        read_only_fields = [
            'id', 'engagement_score', 'recommendation_boost',
            'activity_level', 'compatibility_score', 'profile_completeness'
        ]


    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords don't match")
        return data

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        validated_data['password'] = make_password(validated_data['password'])
        return User.objects.create(**validated_data)


class UserLoginSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'phone_number', 'email', 'password', 'first_name', 'last_name',
            'day', 'month', 'year', 'latitude', 'longitude', 'gender',
            'about', 'hopes', 'religion', 'user_images', 'user_interests'
        ]
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        """Create and return a new user instance"""
        # Extract password to hash it separately
        password = validated_data.pop('password', None)

        # Create user instance
        user = User(**validated_data)

        # Set the password (this will hash it)
        if password:
            user.set_password(password)

        user.save()
        return user

    def validate_phone_number(self, value):
        """Ensure phone number is unique"""
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("Phone number already registered")
        return value


class LoginSerializer(serializers.Serializer):
    """Serializer for user login - only validates credentials exist"""
    phone_number = serializers.CharField(required=False, allow_blank=True)
    email = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        phone_number = data.get('phone_number')
        email = data.get('email')
        password = data.get('password')

        if not phone_number and not email:
            raise serializers.ValidationError("Either phone_number or email is required")

        if not password:
            raise serializers.ValidationError("Password is required")

        return data


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'phone_number', 'email', 'first_name', 'last_name',
            'day', 'month', 'year', 'latitude', 'longitude', 'profile_pic',
            'gender', 'about', 'hopes', 'religion', 'contact', 'twitter',
            'instagram', 'facebook', 'whatsapp', 'online', 'promoted',
            'subscription', 'end_subscription', 'total_shows', 'user_images',
            'user_interests', 'created', 'updated'
        ]
        read_only_fields = ['id', 'created', 'updated']


class UserProfileSerializer(serializers.ModelSerializer):
    """Detailed user profile with additional info"""
    moments_count = serializers.SerializerMethodField()
    matches_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'first_name', 'last_name', 'profile_pic', 'gender',
            'about', 'hopes', 'religion', 'user_images', 'user_interests',
            'online', 'promoted', 'moments_count', 'matches_count'
        ]

    def get_moments_count(self, obj):
        return obj.moments.count()

    def get_matches_count(self, obj):
        return obj.matches_as_user1.count() + obj.matches_as_user2.count()


class ProfileLikeSerializer(serializers.ModelSerializer):
    liker_name = serializers.CharField(source='liker.first_name', read_only=True)
    liked_user_name = serializers.CharField(source='liked_user.first_name', read_only=True)

    class Meta:
        model = ProfileLike
        fields = ['id', 'liker', 'liked_user', 'liker_name', 'liked_user_name', 
                  'superlike', 'created_at']
        read_only_fields = ['id', 'created_at']


class MatchSerializer(serializers.ModelSerializer):
    user1_details = UserProfileSerializer(source='user1', read_only=True)
    user2_details = UserProfileSerializer(source='user2', read_only=True)

    class Meta:
        model = Match
        fields = ['id', 'user1', 'user2', 'user1_details', 'user2_details',
                  'seen_by_user1', 'seen_by_user2', 'created_at']
        read_only_fields = ['id', 'created_at']


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.first_name', read_only=True)
    sender_profile_pic = serializers.CharField(source='sender.profile_pic', read_only=True)

    class Meta:
        model = Message
        fields = [
            'id', 'conversation', 'sender', 'receiver', 'sender_name',
            'sender_profile_pic', 'sms', 'seen', 'is_image', 'is_text',
            'gift', 'gift_image', 'price', 'quantity', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ConversationSerializer(serializers.ModelSerializer):
    participants_details = UserProfileSerializer(source='participants', many=True, read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ['id', 'participants', 'participants_details', 'last_message',
                  'unread_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_last_message(self, obj):
        last_msg = obj.messages.order_by('-created_at').first()
        if last_msg:
            return MessageSerializer(last_msg).data
        return None

    def get_unread_count(self, obj):
        user = self.context.get('request').user if self.context.get('request') else None
        if user:
            return obj.messages.filter(receiver=user, seen=False).count()
        return 0


class MomentLikeSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.first_name', read_only=True)

    class Meta:
        model = MomentLike
        fields = ['id', 'moment', 'user', 'user_name', 'created_at']
        read_only_fields = ['id', 'created_at']


class CommentSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.first_name', read_only=True)
    author_profile_pic = serializers.CharField(source='author.profile_pic', read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'moment', 'author', 'author_name', 'author_profile_pic',
                  'text', 'image', 'created_at']
        read_only_fields = ['id', 'created_at']


class MomentSerializer(serializers.ModelSerializer):
    owner_details = UserProfileSerializer(source='owner', read_only=True)
    comments = CommentSerializer(many=True, read_only=True)
    likes = MomentLikeSerializer(many=True, read_only=True)
    is_liked_by_user = serializers.SerializerMethodField()

    class Meta:
        model = Moment
        fields = [
            'id', 'owner', 'owner_details', 'hashtag', 'tagline', 'images',
            'likes_count', 'total_gifts', 'comments', 'likes', 'is_liked_by_user',
            'created_at'
        ]
        read_only_fields = ['id', 'likes_count', 'total_gifts', 'created_at']

    def get_is_liked_by_user(self, obj):
        user = self.context.get('request').user if self.context.get('request') else None
        if user:
            return obj.likes.filter(user=user).exists()
        return False


class GiftSerializer(serializers.ModelSerializer):
    class Meta:
        model = Gift
        fields = ['id', 'name', 'image', 'value']
        read_only_fields = ['id']


class UserGiftSerializer(serializers.ModelSerializer):
    gift_details = GiftSerializer(source='gift', read_only=True)

    class Meta:
        model = UserGift
        fields = ['id', 'user', 'gift', 'gift_details', 'quantity', 'purchased_at']
        read_only_fields = ['id', 'purchased_at']


class TransactionSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.first_name', read_only=True)

    class Meta:
        model = Transaction
        fields = [
            'id', 'user', 'user_name', 'amount', 'reason', 'quantity',
            'fulfilled', 'transaction_reference', 'mno_transaction_reference',
            'issued_receipt_number', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class WithdrawalSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.first_name', read_only=True)

    class Meta:
        model = Withdrawal
        fields = [
            'id', 'user', 'user_name', 'amount', 'quantity', 'mobile_number',
            'approved', 'transaction_id', 'created_at', 'processed_at'
        ]
        read_only_fields = ['id', 'approved', 'transaction_id', 'created_at', 'processed_at']


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'user', 'header', 'message', 'is_global', 'seen', 'created_at']
        read_only_fields = ['id', 'created_at']


class ProfileViewSerializer(serializers.ModelSerializer):
    viewer_name = serializers.CharField(source='viewer.first_name', read_only=True)
    viewed_user_name = serializers.CharField(source='viewed_user.first_name', read_only=True)
    
    class Meta:
        model = ProfileView
        fields = [
            'id', 'viewer', 'viewer_name', 'viewed_user', 'viewed_user_name',
            'view_duration', 'scrolled_to_bottom', 'viewed_images_count',
            'clicked_social_links', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class UserInteractionSerializer(serializers.ModelSerializer):
    target_user_name = serializers.CharField(source='target_user.first_name', read_only=True)
    
    class Meta:
        model = UserInteraction
        fields = [
            'id', 'user', 'interaction_type', 'target_user',
            'target_user_name', 'engagement_score', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class UserPreferenceProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPreferenceProfile
        fields = [
            'id', 'user', 'age_preference_min', 'age_preference_max',
            'distance_importance', 'activity_level_preference',
            'avg_session_duration', 'preferred_time_of_day',
            'swipe_rate', 'response_rate', 'total_engagement_score',
            'interest_weights', 'personality_vector', 'updated_at'
        ]
        read_only_fields = ['id', 'updated_at']


class PhoneOTPSerializer(serializers.ModelSerializer):
    class Meta:
        model = PhoneOTP
        fields = ['phone_number', 'otp_code', 'created_at', 'expires_at']
        read_only_fields = ['otp_code', 'created_at', 'expires_at']


class PhoneOTPRequestSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20)

    def validate_phone_number(self, value):
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("Phone number already registered")
        return value


class PhoneOTPVerifySerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20)
    otp_code = serializers.CharField(max_length=6)