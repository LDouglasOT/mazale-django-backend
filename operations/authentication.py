from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import BaseAuthentication
from rest_framework import exceptions
from .models import User


class CustomJWTAuthentication(JWTAuthentication):
    """
    Custom JWT Authentication that uses the User model
    Extends djangorestframework-simplejwt's JWTAuthentication
    """

    def get_user(self, validated_token):
        """
        Attempts to find and return a user using the given validated token.
        """
        try:
            user_id = validated_token.get('user_id')
        except KeyError:
            raise exceptions.AuthenticationFailed(
                'Token contained no recognizable user identification'
            )

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise exceptions.AuthenticationFailed('User not found')

        if not user.online:
            # Optionally, you can check if user should be online
            pass

        return user


class TokenAuthentication(BaseAuthentication):
    """
    Simple token authentication using the token field in User model
    This is for legacy support or simple token-based auth
    
    Clients should authenticate by passing the token key in the 'Authorization'
    HTTP header, prepended with the string 'Bearer '.  For example:
    
        Authorization: Bearer 401f7ac837da42b97f613d789819ff93537bee6a
    """
    
    keyword = 'Bearer'
    model = User

    def authenticate(self, request):
        """
        Authenticate the request and return a two-tuple of (user, token).
        """
        auth_header = self.get_authorization_header(request)
        
        if not auth_header:
            return None
        
        try:
            token = auth_header.decode('utf-8')
        except UnicodeError:
            raise exceptions.AuthenticationFailed(
                'Invalid token header. Token string should not contain invalid characters.'
            )

        return self.authenticate_credentials(token)

    def get_authorization_header(self, request):
        """
        Extract and return the authorization header from the request.
        """
        auth = request.META.get('HTTP_AUTHORIZATION', b'')
        
        if isinstance(auth, str):
            auth = auth.encode('utf-8')
        
        parts = auth.split()
        
        if not parts or parts[0].lower() != self.keyword.lower().encode():
            return None
        
        if len(parts) == 1:
            raise exceptions.AuthenticationFailed('Invalid token header. No credentials provided.')
        elif len(parts) > 2:
            raise exceptions.AuthenticationFailed('Invalid token header. Token string should not contain spaces.')
        
        return parts[1]

    def authenticate_credentials(self, key):
        """
        Authenticate the token and return the user and token.
        """
        try:
            user = self.model.objects.get(token=key)
        except self.model.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid token.')

        if not user.online:
            # Optional: You might want to set user online when they authenticate
            user.online = True
            user.save(update_fields=['online'])

        return (user, key)

    def authenticate_header(self, request):
        """
        Return a string to be used as the value of the `WWW-Authenticate`
        header in a `401 Unauthenticated` response.
        """
        return self.keyword


class MultiAuthenticationBackend:
    """
    Custom authentication backend that tries multiple authentication methods
    This allows using either JWT or simple token authentication
    """
    
    def authenticate(self, request):
        """
        Try JWT authentication first, then fall back to token authentication
        """
        # Try JWT authentication
        jwt_auth = CustomJWTAuthentication()
        try:
            result = jwt_auth.authenticate(request)
            if result is not None:
                return result
        except exceptions.AuthenticationFailed:
            pass
        
        # Try simple token authentication
        token_auth = TokenAuthentication()
        try:
            result = token_auth.authenticate(request)
            if result is not None:
                return result
        except exceptions.AuthenticationFailed:
            pass
        
        return None


class PhoneNumberAuthenticationBackend:
    """
    Custom authentication backend for phone number + password
    Can be used with Django's authenticate() function
    """
    
    def authenticate(self, request, phone_number=None, password=None, **kwargs):
        """
        Authenticate using phone number and password
        """
        if phone_number is None or password is None:
            return None
        
        try:
            from django.contrib.auth.hashers import check_password
            user = User.objects.get(phone_number=phone_number)
            
            if check_password(password, user.password):
                return user
        except User.DoesNotExist:
            return None
        
        return None
    
    def get_user(self, user_id):
        """
        Get user by ID
        """
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None


class EmailAuthenticationBackend:
    """
    Custom authentication backend for email + password
    Can be used with Django's authenticate() function
    """
    
    def authenticate(self, request, email=None, password=None, **kwargs):
        """
        Authenticate using email and password
        """
        if email is None or password is None:
            return None
        
        try:
            from django.contrib.auth.hashers import check_password
            user = User.objects.get(email=email)
            
            if check_password(password, user.password):
                return user
        except User.DoesNotExist:
            return None
        
        return None
    
    def get_user(self, user_id):
        """
        Get user by ID
        """
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None