from django.contrib import admin
from django.urls import path
from rest_framework import routers

from .views import (
    home,
    receipt_list,
    policy_list,
    audit_dashboard,
    notification_list,
)

router = routers.DefaultRouter()

urlpatterns = [
    path('', home, name='home'),
    path('receipts/', receipt_list, name='receipt_list'),
    path('policies/', policy_list, name='policy_list'),
    path('audit/', audit_dashboard, name='audit_dashboard'),
    path('notifications/', notification_list, name='notification_list'),
    path('admin/', admin.site.urls),
]
