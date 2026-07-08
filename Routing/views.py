from math import radians, sin, cos, sqrt, atan2
import json
from urllib.error import URLError
from urllib.request import urlopen

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse

from .models import SupervisorStudentAssignment


WORK_BASED_ATTACHMENT_TYPES = {'work_based'}
SERVICE_BASED_ATTACHMENT_TYPES = {'service_based'}
OSRM_TABLE_ENDPOINT = 'https://router.project-osrm.org/table/v1/driving/'
OSRM_ROUTE_ENDPOINT = 'https://router.project-osrm.org/route/v1/driving/'


def _learning_mode_from_attachment(attachment_type):
    value = (attachment_type or '').strip().lower()
    if value in WORK_BASED_ATTACHMENT_TYPES:
        return 'work_based'
    if value in SERVICE_BASED_ATTACHMENT_TYPES:
        return 'service_based'
    return ''


def _organization_student_counts(students):
    counts = {}
    for student in students:
        organization = (student.profile.organization_name or '').strip()
        if not organization:
            continue
        counts[organization] = counts.get(organization, 0) + 1
    return counts


def _students_with_coordinates(students):
    return [
        s for s in students
        if s.profile.organization_latitude is not None and s.profile.organization_longitude is not None
    ]


def _build_map_points(students):
    return [
        {
            'name': f"{student.first_name} {student.last_name}".strip() or student.email,
            'organization': student.profile.organization_name or 'Organization not set',
            'location': student.profile.organization_location or 'Location not set',
            'lat': student.profile.organization_latitude,
            'lng': student.profile.organization_longitude,
        }
        for student in _students_with_coordinates(students)
    ]


def _build_optimized_map_points(route_rows):
    return [
        {
            'name': row['student'].get_full_name().strip() or row['student'].email,
            'organization': row['student'].profile.organization_name or 'Organization not set',
            'location': row['student'].profile.organization_location or 'Location not set',
            'school_id': row['student'].profile.school_id or 'N/A',
            'course': row['student'].profile.course or 'N/A',
            'attachment_type': row['student'].profile.get_attachment_type_display() or 'Not set',
            'main_road': row['student'].profile.organization_main_road or 'Road not set',
            'lat': row['student'].profile.organization_latitude,
            'lng': row['student'].profile.organization_longitude,
            'stop_order': row['order'],
            'direct_time_label': row['direct_time_label'],
            'eta_time_label': row['eta_time_label'],
        }
        for row in route_rows
    ]


def _build_organization_summaries(students):
    grouped = {}

    for student in students:
        profile = student.profile
        organization_name = (profile.organization_name or '').strip() or 'Organization not set'

        if organization_name not in grouped:
            grouped[organization_name] = {
                'organization_name': organization_name,
                'organization_location': profile.organization_location or 'Location not set',
                'organization_main_road': profile.organization_main_road or 'Road not set',
                'attachment_types': set(),
                'students': [],
            }

        attachment_label = profile.get_attachment_type_display() if profile.attachment_type else 'Not set'
        grouped[organization_name]['attachment_types'].add(attachment_label)
        grouped[organization_name]['students'].append(
            {
                'full_name': student.get_full_name().strip() or student.email,
                'school_id': profile.school_id or 'N/A',
                'course': profile.course or 'N/A',
            }
        )

    summaries = []
    for _, data in sorted(grouped.items(), key=lambda item: item[0].lower()):
        data['students'].sort(key=lambda s: s['full_name'].lower())
        data['attachment_types'] = ', '.join(sorted(data['attachment_types']))
        data['students_count'] = len(data['students'])
        summaries.append(data)

    return summaries


def _haversine_km(lat1, lon1, lat2, lon2):
    earth_radius_km = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return earth_radius_km * c


def _estimate_travel_minutes(distance_km, average_speed_kmh=30):
    if average_speed_kmh <= 0:
        return 0.0
    return (distance_km / average_speed_kmh) * 60


def _format_minutes(minutes):
    rounded = int(round(minutes))
    hours = rounded // 60
    remaining = rounded % 60
    if hours > 0:
        return f"{hours}h {remaining}m"
    return f"{remaining}m"


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


def _osrm_table_matrix(points):
    coords = ';'.join([f"{point['lng']:.6f},{point['lat']:.6f}" for point in points])
    url = f"{OSRM_TABLE_ENDPOINT}{coords}?annotations=duration,distance"

    try:
        with urlopen(url, timeout=10) as response:
            payload = json.loads(response.read().decode('utf-8'))
    except (URLError, TimeoutError, ValueError):
        return None

    if payload.get('code') != 'Ok':
        return None

    return {
        'durations': payload.get('durations') or [],
        'distances': payload.get('distances') or [],
    }


def _build_road_network_route(students, start_lat, start_lng):
    candidates = _students_with_coordinates(students)
    if not candidates:
        return {
            'students': [],
            'route_rows': [],
            'used_road_network': False,
        }

    points = [{'lat': start_lat, 'lng': start_lng}] + [
        {
            'lat': student.profile.organization_latitude,
            'lng': student.profile.organization_longitude,
        }
        for student in candidates
    ]

    matrix = _osrm_table_matrix(points)
    if matrix is None:
        return {
            'students': _nearest_neighbor_route(candidates, start_lat, start_lng),
            'route_rows': [],
            'used_road_network': False,
        }

    durations = matrix['durations']
    distances = matrix['distances']
    if not durations or not distances:
        return {
            'students': _nearest_neighbor_route(candidates, start_lat, start_lng),
            'route_rows': [],
            'used_road_network': False,
        }

    ordered_point_indexes = []
    unvisited = set(range(1, len(points)))
    current = 0

    while unvisited:
        next_index = min(
            unvisited,
            key=lambda idx: durations[current][idx] if durations[current][idx] is not None else float('inf')
        )

        if durations[current][next_index] is None:
            break

        ordered_point_indexes.append(next_index)
        unvisited.remove(next_index)
        current = next_index

    if unvisited:
        remaining_students = [candidates[index - 1] for index in sorted(unvisited)]
        fallback_order = _nearest_neighbor_route(remaining_students, start_lat, start_lng)
        ordered_students = [candidates[index - 1] for index in ordered_point_indexes] + fallback_order
    else:
        ordered_students = [candidates[index - 1] for index in ordered_point_indexes]

    rows = []
    cumulative_minutes = 0.0
    previous_index = 0

    for order, point_index in enumerate(ordered_point_indexes, start=1):
        student = candidates[point_index - 1]

        leg_seconds = durations[previous_index][point_index]
        direct_seconds = durations[0][point_index]
        leg_distance_meters = distances[previous_index][point_index]

        if leg_seconds is None or direct_seconds is None or leg_distance_meters is None:
            student_lat = student.profile.organization_latitude
            student_lng = student.profile.organization_longitude
            previous_lat = points[previous_index]['lat']
            previous_lng = points[previous_index]['lng']

            leg_distance_km = _haversine_km(previous_lat, previous_lng, student_lat, student_lng)
            direct_distance_km = _haversine_km(start_lat, start_lng, student_lat, student_lng)
            leg_minutes = _estimate_travel_minutes(leg_distance_km)
            direct_minutes = _estimate_travel_minutes(direct_distance_km)
        else:
            leg_distance_km = leg_distance_meters / 1000.0
            leg_minutes = leg_seconds / 60.0
            direct_minutes = direct_seconds / 60.0

        cumulative_minutes += leg_minutes

        rows.append(
            {
                'order': order,
                'student': student,
                'leg_distance_km': round(leg_distance_km, 2),
                'leg_time_label': _format_minutes(leg_minutes),
                'direct_time_label': _format_minutes(direct_minutes),
                'eta_time_label': _format_minutes(cumulative_minutes),
                'eta_minutes': int(round(cumulative_minutes)),
            }
        )

        previous_index = point_index

    return {
        'students': ordered_students,
        'route_rows': rows,
        'used_road_network': True,
    }


def _osrm_route_geometry(points):
    if len(points) < 2:
        return []

    coords = ';'.join([f"{point['lng']:.6f},{point['lat']:.6f}" for point in points])
    url = f"{OSRM_ROUTE_ENDPOINT}{coords}?overview=full&geometries=geojson"

    try:
        with urlopen(url, timeout=10) as response:
            payload = json.loads(response.read().decode('utf-8'))
    except (URLError, TimeoutError, ValueError):
        return []

    if payload.get('code') != 'Ok' or not payload.get('routes'):
        return []

    geometry = payload['routes'][0].get('geometry', {})
    coordinates = geometry.get('coordinates') or []
    return [[coord[1], coord[0]] for coord in coordinates if len(coord) >= 2]


def _build_route_plan_rows(students, start_lat, start_lng, organization_counts):
    rows = []
    current_lat = start_lat
    current_lng = start_lng
    cumulative_minutes = 0.0

    for index, student in enumerate(students, start=1):
        student_lat = student.profile.organization_latitude
        student_lng = student.profile.organization_longitude

        leg_distance_km = _haversine_km(current_lat, current_lng, student_lat, student_lng)
        leg_minutes = _estimate_travel_minutes(leg_distance_km)
        cumulative_minutes += leg_minutes

        direct_distance_km = _haversine_km(start_lat, start_lng, student_lat, student_lng)
        direct_minutes = _estimate_travel_minutes(direct_distance_km)

        rows.append(
            {
                'order': index,
                'student': student,
                'organization_count': organization_counts.get((student.profile.organization_name or '').strip(), 0),
                'leg_distance_km': round(leg_distance_km, 2),
                'leg_time_label': _format_minutes(leg_minutes),
                'direct_time_label': _format_minutes(direct_minutes),
                'eta_time_label': _format_minutes(cumulative_minutes),
                'eta_minutes': int(round(cumulative_minutes)),
            }
        )

        current_lat = student_lat
        current_lng = student_lng

    return rows


def _route_context(request, force_generate=False):
    assignments = SupervisorStudentAssignment.objects.select_related('student__profile').filter(
        supervisor=request.user,
        student__profile__role='student'
    )

    assigned_students = [assignment.student for assignment in assignments]

    learning_mode = request.GET.get('learning_mode', '').strip()
    visit_location = request.GET.get('visit_location', '').strip()
    road = request.GET.get('road', '').strip()
    search = request.GET.get('search', '').strip()
    current_location = request.GET.get('current_location', '').strip()

    saved_start_point = request.session.get('supervisor_start_point', {})
    if not current_location:
        current_location = saved_start_point.get('label', '') or ''

    filtered_students = assigned_students

    if learning_mode:
        filtered_students = [
            student for student in filtered_students
            if _learning_mode_from_attachment(student.profile.attachment_type) == learning_mode
        ]

    if visit_location:
        filtered_students = [
            student for student in filtered_students
            if (student.profile.organization_location or '').strip().lower() == visit_location.lower()
        ]

    if road:
        filtered_students = [
            student for student in filtered_students
            if road.lower() in (student.profile.organization_main_road or '').lower()
        ]

    if search:
        search_value = search.lower()
        filtered_students = [
            student for student in filtered_students
            if search_value in (f"{student.first_name} {student.last_name}".strip().lower())
            or search_value in (student.email or '').lower()
            or search_value in (student.profile.school_id or '').lower()
            or search_value in (student.profile.organization_name or '').lower()
            or search_value in (student.profile.organization_location or '').lower()
        ]

    generate_route = force_generate or request.GET.get('generate_route') == '1'
    start_lat = saved_start_point.get('lat')
    start_lng = saved_start_point.get('lng')

    optimized_students = []
    optimized_route_rows = []
    used_road_network = False
    if generate_route:
        missing_requirements = []

        if not current_location:
            missing_requirements.append('current location')
        if learning_mode not in {'service_based', 'work_based'}:
            missing_requirements.append('type of attachment (Service-Based Learning or Work-Based Learning)')
        if not visit_location:
            missing_requirements.append('location of visit')
        if start_lat is None or start_lng is None:
            missing_requirements.append('supervisor map location (set on the Supervisor Location page)')

        if missing_requirements:
            messages.error(
                request,
                'To generate an optimized route, provide: ' + ', '.join(missing_requirements) + '.'
            )
            generate_route = False
        else:
            road_route = _build_road_network_route(filtered_students, start_lat, start_lng)
            optimized_students = road_route['students']
            used_road_network = road_route['used_road_network']

            if road_route['route_rows']:
                optimized_route_rows = road_route['route_rows']

            if not optimized_students:
                messages.info(request, 'Could not generate a route. Ensure assigned students have saved map coordinates.')
            elif not used_road_network:
                messages.warning(request, 'Road network routing service was unavailable. Route used straight-line approximation.')

    organization_counts = _organization_student_counts(filtered_students)

    grouped_students = sorted(
        filtered_students,
        key=lambda student: (
            (student.profile.organization_name or '').strip().lower(),
            (student.first_name or '').strip().lower(),
            (student.last_name or '').strip().lower(),
            (student.email or '').strip().lower(),
        ),
    )

    filtered_student_rows = []
    previous_org = None
    for student in grouped_students:
        org_name = (student.profile.organization_name or '').strip()
        filtered_student_rows.append(
            {
                'student': student,
                'learning_mode': _learning_mode_from_attachment(student.profile.attachment_type),
                'organization_count': organization_counts.get(org_name, 0),
                'show_org_group': org_name != previous_org,
                'org_rowspan': organization_counts.get(org_name, 0),
            }
        )
        previous_org = org_name

    if not optimized_route_rows and optimized_students and start_lat is not None and start_lng is not None:
        optimized_route_rows = _build_route_plan_rows(
            optimized_students,
            start_lat,
            start_lng,
            organization_counts,
        )

    for row in optimized_route_rows:
        row['organization_count'] = organization_counts.get((row['student'].profile.organization_name or '').strip(), 0)

    seen_organizations = set()
    for row in optimized_route_rows:
        org_name = (row['student'].profile.organization_name or '').strip()
        row['show_org_summary'] = org_name not in seen_organizations
        seen_organizations.add(org_name)

    filtered_map_points = _build_map_points(filtered_students)
    optimized_map_points = _build_optimized_map_points(optimized_route_rows)
    organization_summaries = _build_organization_summaries(optimized_students or filtered_students)

    route_path_points = []
    if optimized_route_rows and start_lat is not None and start_lng is not None:
        route_points = [{'lat': start_lat, 'lng': start_lng}] + [
            {
                'lat': row['student'].profile.organization_latitude,
                'lng': row['student'].profile.organization_longitude,
            }
            for row in optimized_route_rows
            if row['student'].profile.organization_latitude is not None
            and row['student'].profile.organization_longitude is not None
        ]
        route_path_points = _osrm_route_geometry(route_points)

    visit_location_options = sorted({
        (student.profile.organization_location or '').strip()
        for student in assigned_students
        if (student.profile.organization_location or '').strip()
    })

    query_values = {
        'learning_mode': learning_mode,
        'visit_location': visit_location,
        'road': road,
        'search': search,
        'current_location': current_location,
        'generate_route': '1',
    }

    return {
        'generate_route': generate_route,
        'selected_learning_mode': learning_mode,
        'selected_visit_location': visit_location,
        'selected_road': road,
        'selected_search': search,
        'current_location': current_location,
        'visit_location_options': visit_location_options,
        'filtered_students_count': len(filtered_students),
        'filtered_student_rows': filtered_student_rows,
        'optimized_route_rows': optimized_route_rows,
        'first_assessment_student': optimized_students[0] if optimized_students else None,
        'last_assessment_student': optimized_students[-1] if optimized_students else None,
        'filtered_map_points': filtered_map_points,
        'optimized_map_points': optimized_map_points,
        'organization_summaries': organization_summaries,
        'route_path_points': route_path_points,
        'used_road_network': used_road_network,
        'route_start_point': {
            'lat': start_lat,
            'lng': start_lng,
            'label': current_location,
        },
        'table_url': reverse('supervisor_route_table'),
        'map_url': reverse('supervisor_route_map'),
        'query_values': query_values,
    }


def _ensure_supervisor_user(request):
    role = getattr(getattr(request.user, 'profile', None), 'role', None)
    if role != 'supervisor':
        messages.error(request, 'Only supervisors can access this page.')
        return False
    return True


@login_required
def supervisor_location_view(request):
    if not _ensure_supervisor_user(request):
        return redirect('home')

    if request.method == 'POST':
        current_location = request.POST.get('current_location', '').strip()
        current_lat_raw = request.POST.get('current_lat', '').strip()
        current_lng_raw = request.POST.get('current_lng', '').strip()

        if not current_lat_raw or not current_lng_raw:
            messages.error(request, 'Please pick your current location on the map before saving.')
            return redirect('supervisor_location')

        try:
            current_lat = float(current_lat_raw)
            current_lng = float(current_lng_raw)
        except ValueError:
            messages.error(request, 'The selected map coordinates are invalid. Please select again.')
            return redirect('supervisor_location')

        request.session['supervisor_start_point'] = {
            'label': current_location,
            'lat': current_lat,
            'lng': current_lng,
        }
        request.session.modified = True
        messages.success(request, 'Supervisor location saved and ready for route optimization.')
        return redirect('view_assigned_students')

    saved_point = request.session.get('supervisor_start_point', {})
    return render(
        request,
        'routes/supervisor_location.html',
        {
            'saved_current_location': saved_point.get('label', ''),
            'saved_current_lat': saved_point.get('lat', ''),
            'saved_current_lng': saved_point.get('lng', ''),
        }
    )


@login_required
def route_list(request):
    if not _ensure_supervisor_user(request):
        return redirect('home')
    context = _route_context(request, force_generate=False)
    return render(request, 'routes/list.html', context)


@login_required
def route_table_view(request):
    if not _ensure_supervisor_user(request):
        return redirect('home')

    context = _route_context(request, force_generate=True)
    return render(request, 'routes/route_table.html', context)


@login_required
def route_map_view(request):
    if not _ensure_supervisor_user(request):
        return redirect('home')

    context = _route_context(request, force_generate=True)
    return render(request, 'routes/route_map.html', context)
