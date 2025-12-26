from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .onesignal_service import send_notification_to_all, send_notification_to_users

class TestNotificationAllView(APIView):
    """
    API endpoint to send test notification to all users via Celery
    """
    def post(self, request, *args, **kwargs):
        result = send_notification_to_all.delay(
            heading="Test Notification",
            content="This is a test notification to all users!",
            data={"test": True}
        )
        return Response(
            {"status": "sent", "task_id": result.id}, 
            status=status.HTTP_202_ACCEPTED
        )

class TestNotificationSpecificView(APIView):
    """
    API endpoint to send test notification to specific users via Celery
    """
    def post(self, request, *args, **kwargs):
        # In a real scenario, you might get these from request.data
        player_ids = request.data.get("player_ids", ["test-player-id-1", "test-player-id-2"])
        
        result = send_notification_to_users.delay(
            heading="Personal Test",
            content="This is a test notification to specific users!",
            user_ids=player_ids,
            data={"type": "personal", "test": True}
        )
        return Response(
            {"status": "sent", "task_id": result.id}, 
            status=status.HTTP_202_ACCEPTED
        )