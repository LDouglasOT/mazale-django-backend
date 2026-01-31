from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    Read permissions are allowed to any authenticated request.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        elif hasattr(obj, 'user'):
            return obj.user == request.user
        elif hasattr(obj, 'author'):
            return obj.author == request.user
        
        return False


class IsOwner(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to access it.
    """

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        elif hasattr(obj, 'user'):
            return obj.user == request.user
        elif hasattr(obj, 'author'):
            return obj.author == request.user
        elif hasattr(obj, 'liker'):
            return obj.liker == request.user
        
        return False


class IsParticipant(permissions.BasePermission):
    """
    Custom permission for conversations - only participants can access
    """

    def has_object_permission(self, request, view, obj):
        # For conversations, check if user is a participant
        if hasattr(obj, 'participants'):
            return request.user in obj.participants.all()
        
        return False


class IsMessageParticipant(permissions.BasePermission):
    """
    Custom permission for messages - only sender/receiver can access
    """

    def has_object_permission(self, request, view, obj):
        return obj.sender == request.user or obj.receiver == request.user


class IsMatchParticipant(permissions.BasePermission):
    """
    Custom permission for matches - only the matched users can access
    """

    def has_object_permission(self, request, view, obj):
        return obj.user1 == request.user or obj.user2 == request.user


class CanCommentOnMoment(permissions.BasePermission):
    """
    Custom permission to check if user can comment on a moment
    """

    def has_permission(self, request, view):
        # Only authenticated users can comment
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Can only delete own comments
        if request.method == 'DELETE':
            return obj.author == request.user
        return True


class CanManageGift(permissions.BasePermission):
    """
    Custom permission for gift management
    """

    def has_object_permission(self, request, view, obj):
        # Only owner can manage their gifts
        if hasattr(obj, 'user'):
            return obj.user == request.user
        return False


class IsAdminOrOwner(permissions.BasePermission):
    """
    Custom permission to allow admin or owner to access
    """

    def has_object_permission(self, request, view, obj):
        # Admin has full access
        if request.user.is_staff:
            return True
        
        # Owner has access
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        elif hasattr(obj, 'user'):
            return obj.user == request.user
        
        return False


class CanViewProfile(permissions.BasePermission):
    """
    Custom permission to check if user can view another user's profile
    """

    def has_object_permission(self, request, view, obj):
        # User can always view their own profile
        if obj == request.user:
            return True
        
        # Check if users are matched
        from .models import Match
        from django.db.models import Q
        
        matches_exist = Match.objects.filter(
            Q(user1=request.user, user2=obj) | Q(user1=obj, user2=request.user)
        ).exists()
        
        if matches_exist:
            return True
        
        # Allow viewing for discovery (read-only)
        if request.method in permissions.SAFE_METHODS:
            return True
        
        return False