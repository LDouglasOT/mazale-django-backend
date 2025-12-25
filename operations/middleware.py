from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin
from .models import User


class UpdateLastActivityMiddleware(MiddlewareMixin):
    """
    Middleware to update user's last activity timestamp
    """
    
    def process_request(self, request):
        if request.user.is_authenticated:
            # Update last activity
            try:
                user = User.objects.get(id=request.user.id)
                user.updated = timezone.now()
                user.save(update_fields=['updated'])
            except User.DoesNotExist:
                pass
        return None


class SetOnlineStatusMiddleware(MiddlewareMixin):
    """
    Middleware to automatically set user online status
    """
    
    def process_request(self, request):
        if request.user.is_authenticated:
            try:
                user = User.objects.get(id=request.user.id)
                if not user.online:
                    user.online = True
                    user.save(update_fields=['online'])
            except User.DoesNotExist:
                pass
        return None


class APILoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log API requests for analytics
    """
    
    def process_request(self, request):
        # Log request details
        import logging
        logger = logging.getLogger('api')
        
        log_data = {
            'method': request.method,
            'path': request.path,
            'user': str(request.user) if request.user.is_authenticated else 'Anonymous',
            'ip': self.get_client_ip(request),
            'timestamp': timezone.now().isoformat()
        }
        
        logger.info(f"API Request: {log_data}")
        
        return None
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class CORSMiddleware(MiddlewareMixin):
    """
    Custom CORS middleware for more control
    """
    
    def process_response(self, request, response):
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response["Access-Control-Max-Age"] = "3600"
        
        return response


class RateLimitMiddleware(MiddlewareMixin):
    """
    Simple rate limiting middleware
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.rate_limit_cache = {}
    
    def __call__(self, request):
        # Check rate limit
        ip = self.get_client_ip(request)
        current_time = timezone.now()
        
        # Clean old entries (older than 1 minute)
        self.rate_limit_cache = {
            k: v for k, v in self.rate_limit_cache.items() 
            if (current_time - v['first_request']).seconds < 60
        }
        
        if ip in self.rate_limit_cache:
            data = self.rate_limit_cache[ip]
            data['count'] += 1
            
            # Allow 100 requests per minute
            if data['count'] > 100:
                from django.http import JsonResponse
                return JsonResponse(
                    {'error': 'Rate limit exceeded. Try again later.'},
                    status=429
                )
        else:
            self.rate_limit_cache[ip] = {
                'count': 1,
                'first_request': current_time
            }
        
        response = self.get_response(request)
        return response
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class RequestTimingMiddleware(MiddlewareMixin):
    """
    Middleware to track request timing for performance monitoring
    """
    
    def process_request(self, request):
        request.start_time = timezone.now()
        return None
    
    def process_response(self, request, response):
        if hasattr(request, 'start_time'):
            duration = (timezone.now() - request.start_time).total_seconds()
            response['X-Request-Duration'] = str(duration)
            
            # Log slow requests (> 2 seconds)
            if duration > 2:
                import logging
                logger = logging.getLogger('performance')
                logger.warning(
                    f"Slow request: {request.method} {request.path} took {duration}s"
                )
        
        return response


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Middleware to add security headers to responses
    """
    
    def process_response(self, request, response):
        # Add security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        return response


class UserAgentMiddleware(MiddlewareMixin):
    """
    Middleware to parse and store user agent information
    """
    
    def process_request(self, request):
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Parse user agent
        request.is_mobile = self.is_mobile_device(user_agent)
        request.is_tablet = self.is_tablet_device(user_agent)
        request.is_desktop = not (request.is_mobile or request.is_tablet)
        
        return None
    
    def is_mobile_device(self, user_agent):
        """Check if user agent is from mobile device"""
        mobile_keywords = ['Mobile', 'Android', 'iPhone', 'iPod', 'BlackBerry', 'Windows Phone']
        return any(keyword in user_agent for keyword in mobile_keywords)
    
    def is_tablet_device(self, user_agent):
        """Check if user agent is from tablet device"""
        tablet_keywords = ['iPad', 'Android']
        return 'iPad' in user_agent or ('Android' in user_agent and 'Mobile' not in user_agent)