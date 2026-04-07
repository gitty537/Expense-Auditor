from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Notification
from django.utils import timezone


@login_required
def notifications_view(request):
    """
    Display notifications for the logged-in user only.
    """
    user = request.user
    notifications = Notification.objects.filter(
        recipient=user
    ).order_by('-created_at')[:50]

    # Mark all as read when user views them
    Notification.objects.filter(
        recipient=user, is_read=False
    ).update(is_read=True, read_at=timezone.now())

    return render(request, 'notifications.html', {
        'notifications': notifications,
        'active_page': 'notifications',
    })


@login_required
def mark_all_read(request):
    """Mark all notifications as read"""
    if request.method == 'POST':
        Notification.objects.filter(
            recipient=request.user, is_read=False
        ).update(is_read=True, read_at=timezone.now())
        messages.success(request, 'All notifications marked as read')
    return redirect('notification_list')


@login_required
def delete_notification(request, notification_id):
    """Delete a specific notification"""
    if request.method == 'POST':
        try:
            notification = Notification.objects.get(
                id=notification_id, recipient=request.user
            )
            notification.delete()
            messages.success(request, 'Notification deleted')
        except Notification.DoesNotExist:
            messages.error(request, 'Notification not found')
    return redirect('notification_list')

