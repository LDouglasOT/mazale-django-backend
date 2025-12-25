from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager,PermissionsMixin


class UserManager(BaseUserManager):
    def create_user(self, phone_number=None, email=None, password=None, **extra_fields):
        if not phone_number and not email:
            raise ValueError('Either phone_number or email must be provided')

        if phone_number:
            extra_fields.setdefault('phone_number', phone_number)
        if email:
            extra_fields.setdefault('email', email)

        user = self.model(**extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number=None, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        return self.create_user(phone_number=phone_number, email=email, password=password, **extra_fields)


class User(AbstractBaseUser,PermissionsMixin):
    # Authentication fields
    phone_number = models.CharField(max_length=20, null=True, blank=True, unique=True)
    email = models.EmailField(null=True, blank=True, unique=True)
    password = models.CharField(max_length=255)
    token = models.CharField(max_length=255, null=True, blank=True)
    refresh_token = models.CharField(max_length=255, null=True, blank=True)
    google_id = models.CharField(max_length=500, null=True, blank=True)

    # Required fields for AbstractBaseUser
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(null=True, blank=True)

    # Managers
    objects = UserManager()

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['email']

    # Personal information
    first_name = models.CharField(max_length=50, null=True, blank=True)
    last_name = models.CharField(max_length=50, null=True, blank=True)
    day = models.CharField(max_length=2, null=True, blank=True)
    month = models.CharField(max_length=2, null=True, blank=True)
    year = models.CharField(max_length=4, null=True, blank=True)
    latitude = models.CharField(max_length=10, null=True, blank=True)
    longitude = models.CharField(max_length=10, null=True, blank=True)
    profile_pic = models.CharField(max_length=255, null=True, blank=True)
    gender = models.CharField(max_length=10, null=True, blank=True)
    about = models.TextField(default="Not set")
    hopes = models.TextField(null=True, blank=True)
    religion = models.CharField(max_length=50, null=True, blank=True)
    
    # Social media links
    contact = models.CharField(max_length=50, default="Not set")
    twitter = models.CharField(max_length=50, default="Not set")
    instagram = models.CharField(max_length=50, default="Not set")
    facebook = models.CharField(max_length=50, default="Not set")
    whatsapp = models.CharField(max_length=15, blank=True, null=True)
    
    # Status fields
    online = models.BooleanField(default=False)
    promoted = models.BooleanField(default=False)
    modified = models.BooleanField(default=False)
    modify = models.IntegerField(default=0)
    
    # Subscription and engagement
    subscription = models.DateTimeField(default=timezone.now)
    end_subscription = models.DateTimeField(default=timezone.now)
    total_shows = models.IntegerField(default=0)
    referal_code = models.CharField(max_length=50, null=True, blank=True)
    promoter_url = models.CharField(max_length=255, null=True, blank=True)
    
    # Arrays and external IDs
    user_images = models.JSONField(null=True, blank=True)
    user_interests = models.JSONField(null=True, blank=True)
    device_id = models.CharField(max_length=255, null=True, blank=True)
    supabase_id = models.CharField(max_length=255, null=True, blank=True)
    supabase_email = models.CharField(max_length=50, null=True, blank=True)
    
    # Timestamps
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}" if self.first_name else f"User {self.id}"

    # Required methods for AbstractBaseUser
    def has_perm(self, perm, obj=None):
        return self.is_superuser

    def has_perms(self, perms, obj=None):
        return self.is_superuser

    def has_module_perms(self, app_label):
        return self.is_superuser

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"


class ProfileLike(models.Model):
    """Represents a user liking another user's profile"""
    liker = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='profiles_liked'
    )
    liked_user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='liked_by'
    )
    superlike = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('liker', 'liked_user')
        verbose_name = "Profile Like"
        verbose_name_plural = "Profile Likes"

    def __str__(self):
        return f"{self.liker} likes {self.liked_user}"


class Match(models.Model):
    """Represents a mutual match between two users"""
    user1 = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='matches_as_user1'
    )
    user2 = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='matches_as_user2'
    )
    seen_by_user1 = models.BooleanField(default=False)
    seen_by_user2 = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user1', 'user2')
        verbose_name = "Match"
        verbose_name_plural = "Matches"

    def __str__(self):
        return f"Match between {self.user1} and {self.user2}"


class Conversation(models.Model):
    """Chat room between users"""
    participants = models.ManyToManyField(User, related_name='conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Conversation {self.id}"

    class Meta:
        verbose_name = "Conversation"
        verbose_name_plural = "Conversations"


class Message(models.Model):
    """Messages within a conversation"""
    conversation = models.ForeignKey(
        Conversation, 
        on_delete=models.CASCADE, 
        related_name='messages'
    )
    sender = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='sent_messages'
    )
    receiver = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='received_messages'
    )
    sms = models.TextField()
    seen = models.BooleanField(default=False)
    is_image = models.BooleanField(default=False)
    is_text = models.BooleanField(default=False)
    
    # Gift fields
    gift = models.BooleanField(default=False)
    gift_image = models.CharField(max_length=255, null=True, blank=True)
    price = models.IntegerField(null=True, blank=True)
    quantity = models.IntegerField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = "Message"
        verbose_name_plural = "Messages"

    def __str__(self):
        return f"Message from {self.sender} to {self.receiver}"


class Moment(models.Model):
    """Posts/Moments created by users"""
    owner = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='moments'
    )
    hashtag = models.CharField(max_length=50, null=True, blank=True)
    tagline = models.CharField(max_length=255, null=True, blank=True)
    images = models.JSONField(
        null=True,
        blank=True,
        help_text="Array of image URLs"
    )
    likes_count = models.IntegerField(default=0)
    total_gifts = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Moment"
        verbose_name_plural = "Moments"

    def __str__(self):
        return f"Moment by {self.owner} - {self.tagline[:30] if self.tagline else 'No tagline'}"


class MomentLike(models.Model):
    """Tracks users who liked a moment"""
    moment = models.ForeignKey(
        Moment, 
        on_delete=models.CASCADE, 
        related_name='likes'
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='moment_likes'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('moment', 'user')
        verbose_name = "Moment Like"
        verbose_name_plural = "Moment Likes"

    def __str__(self):
        return f"{self.user} likes {self.moment}"


class Comment(models.Model):
    """Comments on moments"""
    moment = models.ForeignKey(
        Moment, 
        on_delete=models.CASCADE, 
        related_name='comments'
    )
    author = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='comments'
    )
    text = models.TextField()
    image = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = "Comment"
        verbose_name_plural = "Comments"

    def __str__(self):
        return f"Comment by {self.author} on {self.moment}"


class Gift(models.Model):
    """Gifts available in the app marketplace"""
    name = models.CharField(max_length=50)
    image = models.CharField(max_length=255)
    value = models.IntegerField(default=0, help_text="Value in app currency")
    
    class Meta:
        verbose_name = "Gift"
        verbose_name_plural = "Gifts"

    def __str__(self):
        return self.name


class UserGift(models.Model):
    """Gifts owned/purchased by users"""
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='gifts'
    )
    gift = models.ForeignKey(
        Gift, 
        on_delete=models.CASCADE, 
        related_name='owners'
    )
    quantity = models.IntegerField(default=1)
    purchased_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "User Gift"
        verbose_name_plural = "User Gifts"

    def __str__(self):
        return f"{self.user} owns {self.quantity}x {self.gift}"


class Transaction(models.Model):
    """Financial transactions"""
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='transactions'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.CharField(max_length=255)
    quantity = models.IntegerField(null=True, blank=True)
    fulfilled = models.BooleanField(default=False)
    transaction_reference = models.CharField(max_length=255)
    mno_transaction_reference = models.CharField(max_length=255, blank=True)
    issued_receipt_number = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Transaction"
        verbose_name_plural = "Transactions"

    def __str__(self):
        return f"Transaction {self.id} - {self.user} - {self.amount}"


class Withdrawal(models.Model):
    """Withdrawal requests from users"""
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='withdrawals'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.IntegerField()
    mobile_number = models.CharField(max_length=20)
    approved = models.BooleanField(default=False)
    transaction_id = models.CharField(max_length=255, default="Not yet set")
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Withdrawal"
        verbose_name_plural = "Withdrawals"

    def __str__(self):
        return f"Withdrawal {self.id} - {self.user} - {self.amount}"


class Notification(models.Model):
    """Notifications for users"""
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='notifications',
        null=True,
        blank=True,
        help_text="Null for global notifications"
    )
    header = models.CharField(max_length=255, null=True, blank=True)
    message = models.TextField()
    is_global = models.BooleanField(default=False)
    seen = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"

    def __str__(self):
        if self.is_global:
            return f"Global Notification: {self.header or self.message[:30]}"
        return f"Notification for {self.user}: {self.header or self.message[:30]}"