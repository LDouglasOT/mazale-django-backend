# These tasks run periodically to update ML models and user scores

from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import User,UserInteraction, ProfileView, ProfileLike, Message
from .ml_engine import DatingRecommendationEngine
from celery import shared_task
from django.utils import timezone

@shared_task
def update_all_user_preferences():
    """
    Update preference profiles for all active users
    Run this daily
    """
    active_users = User.objects.filter(
        last_login__gte=timezone.now() - timedelta(days=7)
    )
    
    updated_count = 0
    for user in active_users:
        try:
            engine = DatingRecommendationEngine(user)
            engine.update_user_preferences()
            updated_count += 1
        except Exception as e:
            print(f"Error updating preferences for user {user.id}: {e}")
    
    return f"Updated {updated_count} user preference profiles"


@shared_task
def decay_recommendation_boosts():
    """
    Gradually decay recommendation boosts to baseline
    Run this hourly
    """
    users_with_boost = User.objects.filter(recommendation_boost__gt=1.0)
    
    for user in users_with_boost:
        # Decay by 5% per hour towards 1.0
        new_boost = user.recommendation_boost - ((user.recommendation_boost - 1.0) * 0.05)
        user.recommendation_boost = max(new_boost, 1.0)
        user.save(update_fields=['recommendation_boost'])
    
    return f"Decayed {users_with_boost.count()} user boosts"


@shared_task
def calculate_engagement_scores():
    """
    Recalculate engagement scores for all users
    Run this daily
    """

    
    users = User.objects.all()
    
    for user in users:
        # Calculate comprehensive engagement score
        recent_cutoff = timezone.now() - timedelta(days=30)
        
        scores = {
            'profile_views': ProfileView.objects.filter(
                viewer=user, created_at__gte=recent_cutoff
            ).count() * 1,
            
            'likes_given': ProfileLike.objects.filter(
                liker=user, created_at__gte=recent_cutoff
            ).count() * 2,
            
            'messages_sent': Message.objects.filter(
                sender=user, created_at__gte=recent_cutoff
            ).count() * 3,
            
            'profile_completeness': DatingRecommendationEngine(user)._calculate_profile_completeness(user) * 50,
            
            'consistency': UserInteraction.objects.filter(
                user=user, created_at__gte=recent_cutoff
            ).count() * 0.5,
        }
        
        user.engagement_score = sum(scores.values())
        user.save(update_fields=['engagement_score'])
    
    return f"Updated engagement scores for {users.count()} users"


@shared_task
def cleanup_old_interactions():
    """
    Clean up old interaction data to maintain database performance
    Run weekly
    """
    from .models import UserInteraction, ProfileView
    
    cutoff_date = timezone.now() - timedelta(days=90)
    
    # Delete old profile views
    old_views = ProfileView.objects.filter(created_at__lt=cutoff_date)
    view_count = old_views.count()
    old_views.delete()
    
    # Keep interactions but aggregate old ones
    old_interactions = UserInteraction.objects.filter(created_at__lt=cutoff_date)
    interaction_count = old_interactions.count()
    # You might want to aggregate these instead of deleting
    
    return f"Cleaned up {view_count} old profile views"


@shared_task
def generate_daily_recommendations(user_id):
    """
    Pre-generate recommendations for a specific user
    Can be called when user logs in
    """
    try:
        user = User.objects.get(id=user_id)
        engine = DatingRecommendationEngine(user)
        
        # Get top 50 recommendations and cache them
        recommendations = engine.get_recommended_users(limit=50)
        
        # Store recommendation IDs (you might want to use Redis for this)
        recommendation_ids = [u.id for u in recommendations]
        
        return f"Generated {len(recommendation_ids)} recommendations for user {user_id}"
    
    except User.DoesNotExist:
        return f"User {user_id} not found"


@shared_task
def send_engagement_notifications():
    """
    Send notifications to inactive users to boost engagement
    Run daily
    """
    from .models import Notification
    
    # Find users who haven't been active in 3 days
    inactive_since = timezone.now() - timedelta(days=3)
    inactive_users = User.objects.filter(
        last_login__lt=inactive_since,
        last_login__gte=timezone.now() - timedelta(days=7)  # But active within last week
    )
    
    notifications_sent = 0
    for user in inactive_users:
        # Check if they have new profile views
        new_views = ProfileView.objects.filter(
            viewed_user=user,
            created_at__gte=user.last_login
        ).count()
        
        if new_views > 0:
            Notification.objects.create(
                user=user,
                header="You have new profile views!",
                message=f"{new_views} people viewed your profile. Come back and see who's interested!"
            )
            notifications_sent += 1
    
    return f"Sent {notifications_sent} engagement notifications"


@shared_task(name='chat.tasks.update_online_status')
def update_online_status(user_id, is_online):
    """
    Updates the user's online status when they connect/disconnect from Node.js.
    """
    try:
        # If online status is on a Profile model:
        # Profile.objects.filter(user_id=user_id).update(is_online=is_online, last_seen=timezone.now())
        
        # If online status is directly on your User model (mazale project uses operations.User):
        User.objects.filter(id=user_id).update(
            is_online=is_online, 
            last_login=timezone.now() if is_online else timezone.now()
        )
        return f"User {user_id} status updated to {'Online' if is_online else 'Offline'}"
    except Exception as e:
        return f"Status update failed: {str(e)}"



@shared_task(name='chat.tasks.save_message_to_db')
def save_message_to_db(data):
    """
    Background task to save chat messages matching the 'sms' field schema.
    """
    try:
        Message.objects.create(
            conversation_id=data.get('conversation_id'),
            sender_id=data.get('sender_id'),
            receiver_id=data.get('receiver_id'),
            sms=data.get('sms', ''),  # Your model uses 'sms' instead of 'content'
            seen=data.get('seen', False),
            is_image=data.get('is_image', False),
            is_text=data.get('is_text', True),
            # Gift Fields
            gift=data.get('gift', False),
            gift_image=data.get('gift_image'),
            price=data.get('price'),
            quantity=data.get('quantity'),
        )
        return f"Message saved successfully."
    except Exception as e:
        return f"Error saving message: {str(e)}"

@shared_task(name='chat.tasks.update_online_status')
def update_online_status(user_id, is_online):
    """Updates online status on the custom User model."""
    User.objects.filter(id=user_id).update(is_online=is_online)
    return f"User {user_id} online: {is_online}"

@shared_task(name='chat.tasks.mark_as_seen')
def mark_as_seen(message_id, user_id):
    """Updates the 'seen' field as per your model."""
    Message.objects.filter(id=message_id, receiver_id=user_id).update(seen=True)