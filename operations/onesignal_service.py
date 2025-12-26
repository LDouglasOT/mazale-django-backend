# notifications/onesignal_service.py
import requests
from celery import shared_task
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# OneSignal Configuration
ONESIGNAL_APP_ID = "06016505-f0a1-4eec-bcf6-24ffd1b745f2"
ONESIGNAL_API_KEY = getattr(settings, 'ONESIGNAL_API_KEY', 'os_v2_app_ayawkbpqufhozphwet75dn2f6j4x4vz5ziueuwva5hshw2x6zi3zxs4ljpxttcid5m6mik6mfdgy5xixoh3lxtkvudryvkzx6xsnbli')
ONESIGNAL_API_URL = "https://onesignal.com/api/v1/notifications"


def send_onesignal_notification(heading, content, user_ids=None, send_to_all=False, data=None):
    """
    Synchronous function to send OneSignal notifications.
    
    Args:
        heading (str): Notification title
        content (str): Notification message body
        user_ids (list): List of specific OneSignal player IDs to send to
        send_to_all (bool): If True, sends to all subscribed users
        data (dict): Additional data to send with notification
    
    Returns:
        dict: Response from OneSignal API
    """
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": f"Basic {ONESIGNAL_API_KEY}"
    }
    
    payload = {
        "app_id": ONESIGNAL_APP_ID,
        "headings": {"en": heading},
        "contents": {"en": content},
    }
    
    # Add custom data if provided
    if data:
        payload["data"] = data
    
    # Determine target audience
    if send_to_all:
        payload["included_segments"] = ["All"]
    elif user_ids:
        payload["include_player_ids"] = user_ids
    else:
        logger.error("Must specify either user_ids or send_to_all=True")
        return {"error": "No target audience specified"}
    
    try:
        response = requests.post(ONESIGNAL_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        logger.info(f"Notification sent successfully: {result}")
        return result
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send notification: {str(e)}")
        return {"error": str(e)}


@shared_task(bind=True, max_retries=3)
def send_notification_to_all(self, heading, content, data=None):
    """
    Celery task to send notification to all users in background.
    
    Args:
        heading (str): Notification title
        content (str): Notification message body
        data (dict): Additional data to send with notification
    """
    try:
        result = send_onesignal_notification(
            heading=heading,
            content=content,
            send_to_all=True,
            data=data
        )
        return result
    except Exception as e:
        logger.error(f"Error in send_notification_to_all: {str(e)}")
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=3)
def send_notification_to_users(self, heading, content, user_ids, data=None):
    """
    Celery task to send notification to specific users in background.
    
    Args:
        heading (str): Notification title
        content (str): Notification message body
        user_ids (list): List of OneSignal player IDs
        data (dict): Additional data to send with notification
    """
    try:
        result = send_onesignal_notification(
            heading=heading,
            content=content,
            user_ids=user_ids,
            data=data
        )
        return result
    except Exception as e:
        logger.error(f"Error in send_notification_to_users: {str(e)}")
        raise self.retry(exc=e, countdown=60)


# Example usage in views.py
"""
from .onesignal_service import send_notification_to_all, send_notification_to_users

# Send to all users (runs in background)
send_notification_to_all.delay(
    heading="New Update!",
    content="Check out our latest features",
    data={"page": "updates", "id": 123}
)

# Send to specific users (runs in background)
player_ids = ["user1-player-id", "user2-player-id"]
send_notification_to_users.delay(
    heading="Personal Message",
    content="You have a new message",
    user_ids=player_ids,
    data={"type": "message", "message_id": 456}
)
"""


# settings.py configuration needed
"""
# Add to your Django settings.py:

ONESIGNAL_API_KEY = 'your-onesignal-rest-api-key'

# Celery Configuration
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'

# Install required packages:
# pip install celery redis requests
"""