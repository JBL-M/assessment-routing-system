from django.urls import path
from . import views

urlpatterns = [
    path(
        'supervisor-location/',
        views.supervisor_location_view,
        name='supervisor_location'
    ),
    path(
        'assigned-students/',
        views.route_list,
        name='view_assigned_students'
    ),
    path(
        'route-table/',
        views.route_table_view,
        name='supervisor_route_table'
    ),
    path(
        'route-map/',
        views.route_map_view,
        name='supervisor_route_map'
    ),
    path(
        '',
        views.route_list,
        name='routing'
    ),
]