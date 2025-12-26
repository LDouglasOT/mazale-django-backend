from time import timezone
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
from .ml_engine import DatingRecommendationEngine
from .models import ProfileView, UserInteraction, UserPreferenceProfile


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
    NotificationSerializer
)


# ===================== Authentication Views =====================

@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    """Register a new user"""
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        
        # Generate tokens
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
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_user(request):
    """Login user with phone_number/email and password"""
    serializer = UserLoginSerializer(data=request.data)
    if serializer.is_valid():
        phone_number = serializer.validated_data.get('phone_number')
        email = serializer.validated_data.get('email')
        password = serializer.validated_data['password']
        
        # Find user
        user = None
        if phone_number:
            user = User.objects.filter(phone_number=phone_number).first()
        elif email:
            user = User.objects.filter(email=email).first()
        
        if user and check_password(password, user.password):
            # Generate new tokens
            refresh = RefreshToken()
            refresh[jwt_settings.USER_ID_CLAIM] = getattr(user, jwt_settings.USER_ID_FIELD, 'id')
            user.token = str(refresh.access_token)
            user.refresh_token = str(refresh)
            user.online = True
            user.save()
            
            return Response({
                'message': 'Login successful',
                'user': UserSerializer(user).data,
                'token': user.token,
                'refresh_token': user.refresh_token
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


# ===================== User Views =====================

class UserListView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = PageNumberPagination

    def get(self, request):
        """List all users with pagination"""
        print("fetching all users")
        users = User.objects.all()
        users = users.exclude(gender = request.user.gender)
        paginator = self.pagination_class()
        paginated_users = paginator.paginate_queryset(users, request)
        serializer = UserSerializer(paginated_users, many=True)
        return paginator.get_paginated_response(serializer.data)


class UserProfileUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    
    def put(self, request):
        """Update current user profile"""
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# ===================== Profile Like Views =====================

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
        # Check if already liked
        if ProfileLike.objects.filter(liker=liker, liked_user_id=liked_user_id).exists():
            return Response({'error': 'Already liked'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Create like
        profile_like = ProfileLike.objects.create(
            liker=liker,
            liked_user_id=liked_user_id,
            superlike=superlike
        )
        
        # Check for mutual match
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


# ===================== Match Views =====================

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


# ===================== Conversation Views =====================

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
        if len(participant_ids)>1:
            return Response({'error': 'Conversation must have 2 participants'}, status=status.HTTP_400_BAD_REQUEST)
        if request.user.id not in participant_ids:
            participant_ids.append(request.user.id)
        
        # Check if conversation exists between these participants
        conversations = Conversation.objects.filter(participants__id=request.user.id)
        for conv in conversations:
            conv_participant_ids = set(conv.participants.values_list('id', flat=True))
            if conv_participant_ids == set(participant_ids):
                serializer = ConversationSerializer(conv, context={'request': request})
                return Response(serializer.data)
        
        # Create new conversation
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


# ===================== Message Views =====================
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


# ===================== Moment Views =====================

class MomentListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """List moments"""
        queryset = Moment.objects.all().order_by('-created_at')
        user_id = request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(owner_id=user_id)
        
        serializer = MomentSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)
    
    def post(self, request):
        """Create a new moment"""
        data = request.data.copy()
        data['owner'] = request.user.id
        
        serializer = MomentSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
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
        # Get matched user IDs
        matches = Match.objects.filter(Q(user1=user) | Q(user2=user))
        matched_user_ids = []
        for match in matches:
            matched_user_ids.append(match.user2.id if match.user1 == user else match.user1.id)
        
        # Get moments from matched users and self
        moments = Moment.objects.filter(
            Q(owner__id__in=matched_user_ids) | Q(owner=user)
        ).order_by('-created_at')[:50]
        
        serializer = MomentSerializer(moments, many=True, context={'request': request})
        return Response(serializer.data)


# ===================== Comment Views =====================

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


# ===================== Gift Views =====================

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


# ===================== User Gift Views =====================

class UserGiftListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """List user's gifts"""
        user_gifts = UserGift.objects.filter(user=request.user)
        serializer = UserGiftSerializer(user_gifts, many=True)
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
        
        # Check if user already owns this gift
        user_gift, created = UserGift.objects.get_or_create(
            user=request.user,
            gift=gift,
            defaults={'quantity': quantity}
        )
        
        if not created:
            user_gift.quantity += quantity
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
        
        # Decrease sender's quantity
        user_gift.quantity -= quantity
        if user_gift.quantity == 0:
            user_gift.delete()
        else:
            user_gift.save()
        
        # Add to receiver
        receiver_gift, created = UserGift.objects.get_or_create(
            user_id=receiver_id,
            gift_id=gift_id,
            defaults={'quantity': quantity}
        )
        
        if not created:
            receiver_gift.quantity += quantity
            receiver_gift.save()
        
        return Response({'message': 'Gift sent successfully'})


# ===================== Transaction Views =====================

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


# ===================== Withdrawal Views =====================

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


# ===================== Notification Views =====================

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
    

# ===================== NEW: ML-Enhanced User Discovery =====================

class SmartUserListView(APIView):
    """ML-powered user recommendations"""
    permission_classes = [IsAuthenticated]
    pagination_class = PageNumberPagination

    def get(self, request):
        """Get personalized user recommendations"""
        # Initialize ML engine
        engine = DatingRecommendationEngine(request.user)
        
        # Get query parameters
        limit = int(request.query_params.get('limit', 20))
        refresh = request.query_params.get('refresh', 'false').lower() == 'true'
        
        # Update preferences periodically
        if not request.user.last_recommendation_update or \
           (timezone.now() - request.user.last_recommendation_update).days >= 1 or refresh:
            engine.update_user_preferences()
        
        # Get recommended users
        recommended_users = engine.get_recommended_users(limit=limit)
        
        # Paginate
        paginator = self.pagination_class()
        paginated_users = paginator.paginate_queryset(recommended_users, request)
        serializer = UserSerializer(paginated_users, many=True)
        
        return paginator.get_paginated_response(serializer.data)


# ===================== NEW: Profile View Tracking =====================

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
        
        # Create profile view
        profile_view = ProfileView.objects.create(
            viewer=request.user,
            viewed_user_id=viewed_user_id,
            view_duration=view_duration,
            scrolled_to_bottom=scrolled_to_bottom,
            viewed_images_count=viewed_images_count,
            clicked_social_links=clicked_social_links
        )
        
        # Log interaction
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
        
        # Duration scoring (max 40 points)
        if duration >= 60:
            score += 40
        elif duration >= 30:
            score += 30
        elif duration >= 10:
            score += 20
        else:
            score += 10
        
        # Interaction scoring
        if scrolled:
            score += 20
        if images_viewed >= 3:
            score += 25
        elif images_viewed >= 1:
            score += 15
        if clicked_links:
            score += 15
        
        return min(score, 100)


# ===================== MODIFIED: Enhanced Profile Like with ML =====================

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
        
        # Check if already liked
        if ProfileLike.objects.filter(liker=liker, liked_user_id=liked_user_id).exists():
            return Response({'error': 'Already liked'}, status=400)
        
        # Create like
        profile_like = ProfileLike.objects.create(
            liker=liker,
            liked_user_id=liked_user_id,
            superlike=superlike
        )
        
        # Log interaction
        UserInteraction.objects.create(
            user=liker,
            interaction_type='superlike' if superlike else 'like',
            target_user_id=liked_user_id,
            engagement_score=100 if superlike else 75
        )
        
        # Check for mutual match
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
            
            # Boost both users' recommendation scores
            liked_user = User.objects.get(id=liked_user_id)
            liker.recommendation_boost = min(liker.recommendation_boost * 1.1, 2.0)
            liked_user.recommendation_boost = min(liked_user.recommendation_boost * 1.1, 2.0)
            liker.save()
            liked_user.save()
        else:
            response_data['is_match'] = False
        
        # Update user preferences after every 5 likes
        like_count = ProfileLike.objects.filter(liker=liker).count()
        if like_count % 5 == 0:
            engine = DatingRecommendationEngine(liker)
            engine.update_user_preferences()
        
        return Response(response_data, status=201)


class ProfilePassView(APIView):
    """Track when user passes/skips a profile"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Log profile pass for ML learning"""
        passed_user_id = request.data.get('passed_user_id')
        
        if not passed_user_id:
            return Response({'error': 'passed_user_id required'}, status=400)
        
        # Log interaction
        UserInteraction.objects.create(
            user=request.user,
            interaction_type='pass',
            target_user_id=passed_user_id,
            engagement_score=0  # Negative signal
        )
        
        return Response({'message': 'Pass recorded'})


# ===================== NEW: User Analytics Dashboard =====================

class UserAnalyticsView(APIView):
    """Get user's engagement analytics"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get comprehensive user analytics"""
        user = request.user
        engine = DatingRecommendationEngine(user)
        
        # Profile views analytics
        profile_views_made = ProfileView.objects.filter(viewer=user)
        profile_views_received = ProfileView.objects.filter(viewed_user=user)
        
        # Interaction analytics
        interactions = UserInteraction.objects.filter(user=user)
        
        analytics = {
            'engagement_score': user.engagement_score,
            'activity_level': user.activity_level,
            'recommendation_boost': user.recommendation_boost,
            'profile_completeness': engine._calculate_profile_completeness(user) * 100,
            
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
                'swipe_rate': engine.preference_profile.swipe_rate,
                'avg_session_duration': engine.preference_profile.avg_session_duration,
                'distance_importance': engine.preference_profile.distance_importance,
            }
        }
        
        return Response(analytics)


# ===================== MODIFIED: Enhanced Message Sending =====================

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
            
            # Log interaction
            UserInteraction.objects.create(
                user=request.user,
                interaction_type='message_sent',
                target_user=message.receiver,
                engagement_score=50  # Base score for messaging
            )
            
            # Update conversation timestamp
            if message.conversation:
                message.conversation.updated_at = timezone.now()
                message.conversation.save()
            
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)


# ===================== NEW: Boost Engagement Features =====================

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
        
        # Schedule boost removal (you'd typically use Celery for this)
        # For now, just return success
        
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
        
        engine = DatingRecommendationEngine(request.user)
        
        # Get all potential candidates
        candidates = User.objects.exclude(
            id__in=[request.user.id, target_user.id]
        ).exclude(gender=request.user.gender)[:50]
        
        # Score by similarity to target user
        similar_users = []
        for candidate in candidates:
            similarity = engine._calculate_profile_similarity(candidate, target_user)
            if similarity > 0.3:  # Only include reasonably similar users
                similar_users.append((similarity, candidate))
        
        # Sort by similarity
        similar_users.sort(key=lambda x: x[0], reverse=True)
        
        # Return top 10
        results = [user for score, user in similar_users[:10]]
        serializer = UserSerializer(results, many=True)
        
        return Response(serializer.data)


# ===================== NEW: Engagement Optimization =====================

class OptimizeProfileView(APIView):
    """Get suggestions to optimize profile for better matches"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Analyze profile and provide optimization suggestions"""
        user = request.user
        engine = DatingRecommendationEngine(user)
        
        suggestions = []
        
        # Check profile completeness
        completeness = engine._calculate_profile_completeness(user)
        if completeness < 0.7:
            suggestions.append({
                'category': 'profile_completeness',
                'message': 'Your profile is only {}% complete. Add more details to get better matches!'.format(
                    int(completeness * 100)
                ),
                'priority': 'high'
            })
        
        # Check photo count
        if not user.user_images or len(user.user_images) < 4:
            suggestions.append({
                'category': 'photos',
                'message': 'Add more photos! Profiles with 4+ photos get 3x more matches.',
                'priority': 'high'
            })
        
        # Check bio length
        if not user.about or len(user.about) < 100:
            suggestions.append({
                'category': 'bio',
                'message': 'Write a more detailed bio. Profiles with longer bios get 60% more engagement.',
                'priority': 'medium'
            })
        
        # Check interests
        if not user.user_interests or len(user.user_interests) < 3:
            suggestions.append({
                'category': 'interests',
                'message': 'Add at least 3 interests to help us find better matches for you.',
                'priority': 'medium'
            })
        
        # Check activity level
        if user.activity_level == 'low':
            suggestions.append({
                'category': 'activity',
                'message': 'Be more active! Log in daily and engage with profiles to improve your visibility.',
                'priority': 'medium'
            })
        
        # Check swipe rate
        if engine.preference_profile.swipe_rate < 0.1:
            suggestions.append({
                'category': 'engagement',
                'message': 'You\'re very selective! Consider liking more profiles to increase your match potential.',
                'priority': 'low'
            })
        
        return Response({
            'profile_score': int(completeness * 100),
            'engagement_score': int(user.engagement_score),
            'suggestions': suggestions,
            'total_suggestions': len(suggestions)
        })