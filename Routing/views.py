from math import radians, sin, cos, sqrt, atan2

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .models import SupervisorStudentAssignment


def _haversine_km(lat1, lon1, lat2, lon2):
    earth_radius_km = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return earth_radius_km * c


def _nearest_neighbor_route(students, start_lat=None, start_lng=None):
    if not students:
        return []

    unvisited = [s for s in students if s.profile.organization_latitude is not None and s.profile.organization_longitude is not None]
    if not unvisited:
        return []

    ordered = []

    if start_lat is None or start_lng is None:
        current = unvisited.pop(0)
        ordered.append(current)
        current_lat = current.profile.organization_latitude
        current_lng = current.profile.organization_longitude
    else:
        current_lat = start_lat
        current_lng = start_lng

    while unvisited:
        next_student = min(
            unvisited,
            key=lambda s: _haversine_km(
                current_lat,
                current_lng,
                s.profile.organization_latitude,
                s.profile.organization_longitude
            )
        )
        ordered.append(next_student)
        unvisited.remove(next_student)
        current_lat = next_student.profile.organization_latitude
        current_lng = next_student.profile.organization_longitude

    return ordered


@login_required
def route_list(request):
    role = getattr(getattr(request.user, 'profile', None), 'role', None)
    if role != 'supervisor':
        messages.error(request, 'Only supervisors can access assigned student routes.')
        return redirect('home')

    assignments = SupervisorStudentAssignment.objects.select_related('student__profile').filter(
        supervisor=request.user,
        student__profile__role='student'
    )

    assigned_students = [assignment.student for assignment in assignments]

    course = request.GET.get('course', '').strip()
    attachment_type = request.GET.get('attachment_type', '').strip()
    year_of_study = request.GET.get('year_of_study', '').strip()
    road = request.GET.get('road', '').strip()
    search = request.GET.get('search', '').strip()

    filtered_students = assigned_students
    if course:
        filtered_students = [s for s in filtered_students if (s.profile.course or '').lower() == course.lower()]
    if attachment_type:
        filtered_students = [s for s in filtered_students if s.profile.attachment_type == attachment_type]
    if year_of_study:
        try:
            year_value = int(year_of_study)
            filtered_students = [s for s in filtered_students if s.profile.year_of_study == year_value]
        except ValueError:
            filtered_students = []
    if road:
        filtered_students = [
            s for s in filtered_students
            if road.lower() in (s.profile.organization_main_road or '').lower()
        ]
    if search:
        search_value = search.lower()
        filtered_students = [
            s for s in filtered_students
            if search_value in (f"{s.first_name} {s.last_name}".strip().lower())
            or search_value in (s.email or '').lower()
            or search_value in (s.profile.school_id or '').lower()
            or search_value in (s.profile.organization_name or '').lower()
            or search_value in (s.profile.organization_location or '').lower()
        ]

    generate_route = request.GET.get('generate_route') == '1'
    start_lat_input = request.GET.get('start_lat', '').strip()
    start_lng_input = request.GET.get('start_lng', '').strip()
    start_lat = None
    start_lng = None
    if start_lat_input and start_lng_input:
        try:
            start_lat = float(start_lat_input)
            start_lng = float(start_lng_input)
        except ValueError:
            messages.error(request, 'Invalid start coordinates. Route was generated without a custom start point.')

    optimized_students = []
    if generate_route:
        optimized_students = _nearest_neighbor_route(filtered_students, start_lat, start_lng)
        if not optimized_students:
            messages.info(request, 'Could not generate a route. Ensure assigned students have saved map coordinates.')

    unique_courses = sorted({(s.profile.course or '').strip() for s in assigned_students if (s.profile.course or '').strip()})
    unique_years = sorted({s.profile.year_of_study for s in assigned_students if s.profile.year_of_study is not None})

    context = {
        'students': filtered_students,
        'optimized_students': optimized_students,
        'generate_route': generate_route,
        'course_options': unique_courses,
        'year_options': unique_years,
        'attachment_choices': [
            ('industrial', 'Industrial Attachment'),
            ('internship', 'Internship'),
            ('research', 'Research Attachment'),
            ('fieldwork', 'Field Work'),
            ('other', 'Other'),
        ],
        'selected_course': course,
        'selected_attachment_type': attachment_type,
        'selected_year': year_of_study,
        'selected_road': road,
        'selected_search': search,
        'start_lat': start_lat_input,
        'start_lng': start_lng_input,
    }

    return render(
        request,
        'routes/list.html',
        context
    )
