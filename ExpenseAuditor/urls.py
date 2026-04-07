from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import routers

from .views import (
    home,
    policy_list,
    audit_dashboard,
    audit_detail,
    notification_list,
    register_employee,
    register_admin,
    upload_receipt,
    approve_policy,
)
from audit.views import pre_auth_submit_view, audit_view, audit_detail_view, manage_pre_auth
router = routers.DefaultRouter()

urlpatterns = [
    path('', home, name='home'),
    path('policies/', policy_list, name='policy_list'),
    path('audit/', audit_dashboard, name='audit_dashboard'),
    path('notifications/', notification_list, name='notification_list'),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/login/'), name='logout'),
    path('register/', register_employee, name='register_employee'),
    path('register-admin/', register_admin, name='register_admin'),
    path('upload/', upload_receipt, name='upload_receipt'),
    path('pre-auth/', pre_auth_submit_view, name='pre_auth_submit'),
    path('manage-pre-auth/<int:form_id>/', manage_pre_auth, name='manage_pre_auth'),
    path('approve-policy/<int:policy_id>/', approve_policy, name='approve_policy'),
    path('audit/<int:decision_id>/', audit_detail, name='audit_detail'),
    path('admin/', admin.site.urls),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

