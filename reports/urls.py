from django.urls import path

from . import views

urlpatterns = [
    path('assessments/', views.assessment_reports_home, name='assessment_reports_home'),
    path('assessments/download/csv/<str:status>/', views.download_assessments_csv, name='download_assessments_csv'),
    path('assessments/download/pdf/<str:status>/', views.download_assessments_pdf, name='download_assessments_pdf'),
]
