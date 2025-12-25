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
        'username': user.username,
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
        if moment_id:
            comments = Comment.objects.filter(moment_id=moment_id).order_by('created_at')
        else:
            comments = Comment.objects.all().order_by('-created_at')
        
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