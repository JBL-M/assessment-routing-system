from django.urls import path
from . import views

urlpatterns = [
    path(
        'assigned-students/',
        views.route_list,
        name='view_assigned_students'
    ),
    path(
        '',
        views.route_list,
        name='routing'
    ),
]