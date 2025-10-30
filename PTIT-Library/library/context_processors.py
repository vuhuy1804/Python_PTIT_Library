from .models import Notification

def unread_notifications_count(request):
    if request.user.is_authenticated:
        return {
            'unread_notifications': Notification.objects.filter(user=request.user, is_read=False).count()
        }
    return {'unread_notifications': 0}
