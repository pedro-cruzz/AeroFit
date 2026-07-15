from hashlib import sha256

from django.db import DatabaseError

from .models import UserActivityLog


class UserActivityLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        self._log_activity(request, response)
        return response

    def _log_activity(self, request, response):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return

        if request.path.startswith("/static/"):
            return

        try:
            UserActivityLog.objects.create(
                user=user,
                path=request.path[:220],
                method=request.method[:10],
                status_code=getattr(response, "status_code", 0),
                ip_hash=self._ip_hash(request),
                user_agent=request.META.get("HTTP_USER_AGENT", "")[:220],
            )
        except DatabaseError:
            return

    def _ip_hash(self, request):
        raw_ip = request.META.get("REMOTE_ADDR", "")
        if not raw_ip:
            return ""
        return sha256(raw_ip.encode()).hexdigest()
