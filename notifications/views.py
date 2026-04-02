from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Notification
from django.db.models import Q
from django.utils import timezone

@login_required
def notifications_view(request):
    """
    Display notifications for the logged-in user.
    Shows all notifications (read and unread).
    """
    user = request.user
    
    # Fetch all notifications for this user
    notifications = Notification.objects.filter(
        user=user
    ).order_by('-created_at')
    
    # Mark all as read when user views them
    Notification.objects.filter(user=user, is_read=False).update(is_read=True)
    
    context = {
        'notifications': notifications,
        'active_page': 'notifications',
    }
    
    return render(request, 'notifications.html', context)

@login_required
def mark_all_read(request):
    """Mark all notifications as read"""
    if request.method == 'POST':
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        messages.success(request, 'All notifications marked as read')
    return redirect('notifications')

@login_required
def delete_notification(request, notification_id):
    """Delete a specific notification"""
    if request.method == 'POST':
        try:
            notification = Notification.objects.get(id=notification_id, user=request.user)
            notification.delete()
            messages.success(request, 'Notification deleted')
        except Notification.DoesNotExist:
            messages.error(request, 'Notification not found')
    return redirect('notifications')
