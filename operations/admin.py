from django.contrib import admin
from .models import (
    User, ProfileLike, Match, Conversation, Message,
    Moment, MomentLike, Comment, Gift, UserGift,
    Transaction, Withdrawal, Notification,PhoneOTP
)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['id', 'first_name', 'last_name', 'phone_number', 'email', 'gender', 'online', 'promoted', 'created']
    list_filter = ['online', 'promoted', 'gender', 'created']
    search_fields = ['first_name', 'last_name', 'phone_number', 'email']
    readonly_fields = ['created', 'updated', 'token', 'refresh_token']
    
    fieldsets = (
        ('Authentication', {
            'fields': ('phone_number', 'email', 'password', 'token', 'refresh_token', 'google_id')
        }),
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'day', 'month', 'year', 'gender', 'profile_pic', 'about', 'hopes', 'religion')
        }),
        ('Location', {
            'fields': ('latitude', 'longitude')
        }),
        ('Social Media', {
            'fields': ('contact', 'twitter', 'instagram', 'facebook', 'whatsapp')
        }),
        ('Status & Subscription', {
            'fields': ('online', 'promoted', 'subscription', 'end_subscription', 'total_shows')
        }),
        ('Additional', {
            'fields': ('user_images', 'user_interests', 'referal_code', 'promoter_url', 'device_id', 'modified', 'modify')
        }),
        ('External IDs', {
            'fields': ('supabase_id', 'supabase_email')
        }),
        ('Timestamps', {
            'fields': ('created', 'updated')
        }),
    )


@admin.register(ProfileLike)
class ProfileLikeAdmin(admin.ModelAdmin):
    list_display = ['id', 'liker', 'liked_user', 'superlike', 'created_at']
    list_filter = ['superlike', 'created_at']
    search_fields = ['liker__first_name', 'liked_user__first_name']
    raw_id_fields = ['liker', 'liked_user']


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ['id', 'user1', 'user2', 'seen_by_user1', 'seen_by_user2', 'created_at']
    list_filter = ['seen_by_user1', 'seen_by_user2', 'created_at']
    search_fields = ['user1__first_name', 'user2__first_name']
    raw_id_fields = ['user1', 'user2']


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['id', 'created_at', 'updated_at', 'get_participants']
    list_filter = ['created_at', 'updated_at']
    filter_horizontal = ['participants']
    
    def get_participants(self, obj):
        return ", ".join([str(p) for p in obj.participants.all()[:3]])
    get_participants.short_description = 'Participants'


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'sender', 'receiver', 'conversation', 'sms_preview', 'seen', 'gift', 'created_at']
    list_filter = ['seen', 'gift', 'is_image', 'is_text', 'created_at']
    search_fields = ['sms', 'sender__first_name', 'receiver__first_name']
    raw_id_fields = ['conversation', 'sender', 'receiver']
    
    def sms_preview(self, obj):
        return obj.sms[:50] + '...' if len(obj.sms) > 50 else obj.sms
    sms_preview.short_description = 'Message'


@admin.register(Moment)
class MomentAdmin(admin.ModelAdmin):
    list_display = ['id', 'owner', 'tagline', 'hashtag', 'likes_count', 'total_gifts', 'created_at']
    list_filter = ['created_at']
    search_fields = ['owner__first_name', 'tagline', 'hashtag']
    raw_id_fields = ['owner']


@admin.register(MomentLike)
class MomentLikeAdmin(admin.ModelAdmin):
    list_display = ['id', 'moment', 'user', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__first_name', 'moment__tagline']
    raw_id_fields = ['moment', 'user']


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['id', 'moment', 'author', 'text_preview', 'created_at']
    list_filter = ['created_at']
    search_fields = ['text', 'author__first_name']
    raw_id_fields = ['moment', 'author']
    
    def text_preview(self, obj):
        return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
    text_preview.short_description = 'Comment'


@admin.register(Gift)
class GiftAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'value', 'image']
    search_fields = ['name']


@admin.register(UserGift)
class UserGiftAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'gift', 'quantity', 'purchased_at']
    list_filter = ['purchased_at']
    search_fields = ['user__first_name', 'gift__name']
    raw_id_fields = ['user', 'gift']


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'amount', 'reason', 'fulfilled', 'transaction_reference', 'created_at']
    list_filter = ['fulfilled', 'created_at']
    search_fields = ['user__first_name', 'transaction_reference', 'reason']
    raw_id_fields = ['user']


@admin.register(Withdrawal)
class WithdrawalAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'amount', 'mobile_number', 'approved', 'transaction_id', 'created_at']
    list_filter = ['approved', 'created_at', 'processed_at']
    search_fields = ['user__first_name', 'mobile_number', 'transaction_id']
    raw_id_fields = ['user']
    
    actions = ['approve_withdrawals']
    
    def approve_withdrawals(self, request, queryset):
        from django.utils import timezone
        queryset.update(approved=True, processed_at=timezone.now())
        self.message_user(request, f"{queryset.count()} withdrawals approved")
    approve_withdrawals.short_description = "Approve selected withdrawals"


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'header', 'message_preview', 'is_global', 'seen', 'created_at']
    list_filter = ['is_global', 'seen', 'created_at']
    search_fields = ['header', 'message', 'user__first_name']
    raw_id_fields = ['user']
    
    def message_preview(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'Message'


@admin.register(PhoneOTP)
class PhoneOTPAdmin(admin.ModelAdmin):
    list_display = ['id', 'phone_number', 'otp_code', 'created_at', 'expires_at', 'is_expired']
    list_filter = ['created_at', 'expires_at']
    search_fields = ['phone_number', 'otp_code']
    readonly_fields = ['id', 'created_at', 'expires_at', 'otp_code']

    def is_expired(self, obj):
        return obj.is_expired()
    is_expired.boolean = True
    is_expired.short_description = 'Expired'