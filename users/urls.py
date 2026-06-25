from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('resend-verification/', views.resend_verification_view, name='resend_verification'),
    path('logout/', views.logout_view, name='logout'),
    path('verify-email/<str:token>/', views.verify_email_view, name='verify_email'),
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    path('student/organization-location/', views.student_organization_location_view, name='student_organization_location'),
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/students/', views.admin_students_view, name='admin_students'),
    path('admin/supervisors/', views.admin_supervisors_view, name='admin_supervisors'),
    path('admin/students/assign/', views.admin_assign_student_view, name='admin_assign_student'),
    path('admin/students/auto-assign/', views.admin_auto_assign_students_view, name='admin_auto_assign_students'),
    path('admin/users/change-role/', views.change_user_role_view, name='change_user_role'),
    path('admin/assessments/pending/', views.pending_assessments_view, name='pending_assessments'),
    path('admin/assessments/done/', views.done_assessments_view, name='done_assessments'),
    path('supervisor/dashboard/', views.supervisor_dashboard, name='supervisor_dashboard'),
]