from .models import Notification


def unread_notifications_count(request):
    """
    Inject the count of unread notifications for the logged-in user
    into every template context so the nav badge always stays accurate.
    """
    if request.user.is_authenticated:
        count = Notification.objects.filter(
            recipient=request.user, is_read=False
        ).count()
        return {'unread_notifications_count': count}
    return {'unread_notifications_count': 0}
