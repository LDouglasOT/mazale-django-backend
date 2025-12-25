from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    # Authentication
    register_user, login_user, logout_user,
    
    # Users
    UserListView, UserProfileUpdateView,verify_token,
    
    # Profile Likes
    ProfileLikeListView, ProfileLikeDetailView, ProfileLikeReceivedView,
    
    # Matches
    MatchListView, MatchDetailView, MatchMarkSeenView, NewMatchesView,
    
    # Conversations
    ConversationListView, ConversationDetailView,
    
    # Messages
    MessageListView, MessageDetailView, MessageMarkSeenView, 
    MessageMarkConversationSeenView,
    
    # Moments
    MomentListView, MomentDetailView, MomentLikeView, MomentUnlikeView, 
    MomentFeedView,
    
    # Comments
    CommentListView, CommentDetailView,
    
    # Gifts
    GiftListView, GiftDetailView, GiftCategoriesView,
    
    # User Gifts
    UserGiftListView, UserGiftDetailView, UserGiftPurchaseView, UserGiftSendView,
    
    # Transactions
    TransactionListView, TransactionDetailView, TransactionStatsView,
    
    # Withdrawals
    WithdrawalListView, WithdrawalDetailView, WithdrawalPendingView, 
    WithdrawalApprovedView,
    
    # Notifications
    NotificationListView, NotificationDetailView, NotificationMarkSeenView,
    NotificationMarkAllSeenView, NotificationUnreadCountView,
)

urlpatterns = [
    # ===================== Authentication =====================
    path('auth/register/', register_user, name='register'),
    path('auth/login/', login_user, name='login'),
    path('auth/logout/', logout_user, name='logout'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # ===================== Users =====================
    path('users/', UserListView.as_view(), name='user-list'),
    path('users/update-profile/', UserProfileUpdateView.as_view(), name='user-update-profile'),
    
    # ===================== Profile Likes =====================
    path('profile-likes/', ProfileLikeListView.as_view(), name='profilelike-list'),
    path('profile-likes/<int:pk>/', ProfileLikeDetailView.as_view(), name='profilelike-detail'),
    path('profile-likes/received/', ProfileLikeReceivedView.as_view(), name='profilelike-received'),
    
    # ===================== Matches =====================
    path('matches/', MatchListView.as_view(), name='match-list'),
    path('matches/<int:pk>/', MatchDetailView.as_view(), name='match-detail'),
    path('matches/<int:pk>/mark-seen/', MatchMarkSeenView.as_view(), name='match-mark-seen'),
    path('matches/new/', NewMatchesView.as_view(), name='match-new'),
    path('auth/verify/', verify_token, name='verify_token'),
    
    # ===================== Conversations =====================
    path('conversations/', ConversationListView.as_view(), name='conversation-list'),
    path('conversations/<int:pk>/', ConversationDetailView.as_view(), name='conversation-detail'),
    
    # ===================== Messages =====================
    path('messages/', MessageListView.as_view(), name='message-list'),
    path('messages/<int:pk>/', MessageDetailView.as_view(), name='message-detail'),
    path('messages/<int:pk>/mark-seen/', MessageMarkSeenView.as_view(), name='message-mark-seen'),
    path('messages/mark-conversation-seen/', MessageMarkConversationSeenView.as_view(), name='message-mark-conversation-seen'),
    
    # ===================== Moments =====================
    path('moments/', MomentListView.as_view(), name='moment-list'),
    path('moments/<int:pk>/', MomentDetailView.as_view(), name='moment-detail'),
    path('moments/<int:pk>/like/', MomentLikeView.as_view(), name='moment-like'),
    path('moments/<int:pk>/unlike/', MomentUnlikeView.as_view(), name='moment-unlike'),
    path('moments/feed/', MomentFeedView.as_view(), name='moment-feed'),
    
    # ===================== Comments =====================
    path('comments/', CommentListView.as_view(), name='comment-list'),
    path('comments/<int:pk>/', CommentDetailView.as_view(), name='comment-detail'),
    
    # ===================== Gifts =====================
    path('gifts/', GiftListView.as_view(), name='gift-list'),
    path('gifts/<int:pk>/', GiftDetailView.as_view(), name='gift-detail'),
    path('gifts/categories/', GiftCategoriesView.as_view(), name='gift-categories'),
    
    # ===================== User Gifts =====================
    path('user-gifts/', UserGiftListView.as_view(), name='usergift-list'),
    path('user-gifts/<int:pk>/', UserGiftDetailView.as_view(), name='usergift-detail'),
    path('user-gifts/purchase/', UserGiftPurchaseView.as_view(), name='usergift-purchase'),
    path('user-gifts/send/', UserGiftSendView.as_view(), name='usergift-send'),
    
    # ===================== Transactions =====================
    path('transactions/', TransactionListView.as_view(), name='transaction-list'),
    path('transactions/<int:pk>/', TransactionDetailView.as_view(), name='transaction-detail'),
    path('transactions/stats/', TransactionStatsView.as_view(), name='transaction-stats'),
    
    # ===================== Withdrawals =====================
    path('withdrawals/', WithdrawalListView.as_view(), name='withdrawal-list'),
    path('withdrawals/<int:pk>/', WithdrawalDetailView.as_view(), name='withdrawal-detail'),
    path('withdrawals/pending/', WithdrawalPendingView.as_view(), name='withdrawal-pending'),
    path('withdrawals/approved/', WithdrawalApprovedView.as_view(), name='withdrawal-approved'),
    
    # ===================== Notifications =====================
    path('notifications/', NotificationListView.as_view(), name='notification-list'),
    path('notifications/<int:pk>/', NotificationDetailView.as_view(), name='notification-detail'),
    path('notifications/<int:pk>/mark-seen/', NotificationMarkSeenView.as_view(), name='notification-mark-seen'),
    path('notifications/mark-all-seen/', NotificationMarkAllSeenView.as_view(), name='notification-mark-all-seen'),
    path('notifications/unread-count/', NotificationUnreadCountView.as_view(), name='notification-unread-count'),
]