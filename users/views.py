from django.shortcuts import redirect, render
from .forms import RegisterForm, StudentAttachmentDetailsForm, StudentOrganizationLocationForm
from django.contrib.auth import authenticate, login
from django.contrib.auth import logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core import signing
from django.core.mail import send_mail
from django.db.models import Count, Q
from django.urls import reverse
from .models import Assessment, Profile
from Routing.models import SupervisorStudentAssignment
import time
import logging


logger = logging.getLogger(__name__)


LOGIN_ATTEMPT_LIMIT = 5
LOGIN_LOCK_SECONDS = 5 * 60


def _get_login_attempt_data(request):
    return request.session.get('login_attempts', {})


def _set_login_attempt_data(request, data):
    request.session['login_attempts'] = data
    request.session.modified = True


def _get_lock_seconds_remaining(request, email):
    data = _get_login_attempt_data(request)
    entry = data.get(email, {})
    lock_until = entry.get('lock_until', 0)
    remaining = int(lock_until - time.time())
    return remaining if remaining > 0 else 0


def _register_login_failure(request, email):
    data = _get_login_attempt_data(request)
    entry = data.get(email, {'count': 0, 'lock_until': 0})
    entry['count'] = entry.get('count', 0) + 1

    if entry['count'] >= LOGIN_ATTEMPT_LIMIT:
        entry['lock_until'] = int(time.time()) + LOGIN_LOCK_SECONDS
        entry['count'] = 0

    data[email] = entry
    _set_login_attempt_data(request, data)


def _clear_login_failures(request, email):
    data = _get_login_attempt_data(request)
    if email in data:
        data.pop(email)
        _set_login_attempt_data(request, data)


def _verification_token_for_user(user):
    return signing.dumps({'user_id': user.id, 'email': user.email}, salt='users.email.verify')


def _send_verification_email(request, user):
    token = _verification_token_for_user(user)
    verify_link = request.build_absolute_uri(reverse('verify_email', args=[token]))

    subject = 'Verify your email address'
    message = (
        f'Hi {user.first_name},\n\n'
        f'Please verify your email address by clicking this link:\n{verify_link}\n\n'
        'This link expires in 24 hours.\n\n'
        'If you did not create this account, you can ignore this email.'
    )

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )


def _redirect_for_role(user):
    try:
        role = user.profile.role
    except Exception:
        return 'home'

    role_redirects = {
        'student': 'student_dashboard',
        'admin': 'admin_dashboard',
        'supervisor': 'supervisor_dashboard',
    }

    return role_redirects.get(role, 'home')


def _is_admin_user(user):
    return getattr(getattr(user, 'profile', None), 'role', None) == 'admin'


def _normalize_org_name(value):
    return (value or '').strip().lower()


def _ensure_profiles_for_all_users():
    for user in User.objects.all():
        Profile.objects.get_or_create(user=user, defaults={'role': 'student'})


def _organization_choices():
    return sorted({
        (org or '').strip()
        for org in Profile.objects.filter(role__in=['student', 'supervisor']).values_list('organization_name', flat=True)
        if (org or '').strip()
    })


def _supervisors_with_load(selected_org=''):
    supervisors = User.objects.select_related('profile').filter(profile__role='supervisor')
    if selected_org:
        supervisors = supervisors.filter(profile__organization_name__iexact=selected_org)

    return supervisors.annotate(
        assigned_students_count=Count(
            'assigned_students_links',
            filter=Q(
                assigned_students_links__student__profile__role='student',
                assigned_students_links__student__profile__organization_name__iexact=selected_org
            ) if selected_org else Q(assigned_students_links__student__profile__role='student'),
            distinct=True,
        )
    ).order_by('assigned_students_count', 'first_name', 'last_name', 'email')

def register_view(request):

    if request.method == 'POST':

        form = RegisterForm(request.POST)

        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = True
            user.save()
            Profile.objects.get_or_create(
                user=user,
                defaults={'role': 'student'}
            )

            try:
                _send_verification_email(request, user)
                messages.success(request, 'Registration successful. A verification email has been sent to confirm your address.')
            except Exception as exc:
                logger.exception('Verification email send failed during registration for user %s', user.email)
                if settings.DEBUG:
                    messages.error(request, f'Account created, but verification email could not be sent: {exc}')
                else:
                    messages.error(request, 'Account created, but verification email could not be sent. Contact an administrator.')

            return redirect('login')

        messages.error(request, 'Registration failed. Please correct the highlighted fields.')

    else:
        form = RegisterForm()

    return render(
        request,
        'users/register.html',
        {'form': form}
    )


def login_view(request):

    if request.method == 'POST':

        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        selected_role = request.POST.get('role', '').strip().lower()

        if not email or not password or not selected_role:
            messages.error(request, 'Please enter email, password, and select your role.')
            return render(request, 'users/login.html')

        allowed_roles = {'student', 'admin', 'supervisor'}
        if selected_role not in allowed_roles:
            messages.error(request, 'Invalid role selected.')
            return render(request, 'users/login.html')

        domain = email.split('@')[-1] if '@' in email else ''
        allowed_domains = getattr(settings, 'ORG_EMAIL_DOMAINS', ['strathmore.edu'])
        if domain not in allowed_domains:
            messages.error(request, f"Use your organizational email address ({', '.join(allowed_domains)}).")
            return render(request, 'users/login.html')

        lock_seconds = _get_lock_seconds_remaining(request, email)
        if lock_seconds > 0:
            messages.error(request, f'Too many failed login attempts. Try again in {lock_seconds} seconds.')
            return render(request, 'users/login.html')

        matched_user = User.objects.filter(username__iexact=email).first()

        if not matched_user:
            _register_login_failure(request, email)
            messages.error(request, 'No account was found with that email address.')
            return render(request, 'users/login.html')

        user = authenticate(
            request,
            username=matched_user.username,
            password=password
        )

        if user is not None:

            profile, _ = Profile.objects.get_or_create(
                user=user,
                defaults={'role': 'student'}
            )

            if profile.role != selected_role:
                messages.error(request, f"This account is registered as {profile.get_role_display()}. Select the correct role to continue.")
                return render(request, 'users/login.html')

            if not profile.email_verified:
                try:
                    _send_verification_email(request, user)
                    messages.error(request, 'Your email is not verified yet. A new verification email has been sent.')
                except Exception as exc:
                    logger.exception('Verification email resend failed during login for user %s', user.email)
                    if settings.DEBUG:
                        messages.error(request, f'Your email is not verified. Verification email could not be resent: {exc}')
                    else:
                        messages.error(request, 'Your email is not verified. Verification email could not be resent. Try again later.')
                return render(request, 'users/login.html')

            _clear_login_failures(request, email)
            login(request, user)
            messages.success(request, 'Login successful.')

            return redirect(_redirect_for_role(user))

        _register_login_failure(request, email)
        messages.error(request, 'Incorrect password. Please try again.')

    return render(
        request,
        'users/login.html'
    )


def logout_view(request):

    logout(request)

    return redirect('login')


def resend_verification_view(request):
    if request.method != 'POST':
        return redirect('login')

    email = request.POST.get('email', '').strip().lower()
    if not email:
        messages.error(request, 'Enter your email to resend verification.')
        return redirect('login')

    domain = email.split('@')[-1] if '@' in email else ''
    allowed_domains = getattr(settings, 'ORG_EMAIL_DOMAINS', ['strathmore.edu'])
    if domain not in allowed_domains:
        messages.error(request, f"Use your organizational email address ({', '.join(allowed_domains)}).")
        return redirect('login')

    user = User.objects.filter(username__iexact=email).first()
    if not user:
        messages.error(request, 'No account was found with that email address.')
        return redirect('login')

    profile, _ = Profile.objects.get_or_create(
        user=user,
        defaults={'role': 'student'}
    )

    if profile.email_verified:
        messages.success(request, 'This email is already verified. You can log in now.')
        return redirect('login')

    try:
        _send_verification_email(request, user)
        messages.success(request, 'A new verification email has been sent. Check your inbox.')
    except Exception as exc:
        logger.exception('Verification email resend failed for user %s', user.email)
        if settings.DEBUG:
            messages.error(request, f'Verification email could not be sent: {exc}')
        else:
            messages.error(request, 'Verification email could not be sent. Please try again later.')

    return redirect('login')


def verify_email_view(request, token):
    try:
        payload = signing.loads(token, salt='users.email.verify', max_age=60 * 60 * 24)
    except signing.SignatureExpired:
        return render(
            request,
            'users/verify_email_result.html',
            {
                'success': False,
                'heading': 'Verification Link Expired',
                'message': 'This verification link has expired. Please register again to receive a new link.',
                'action_url': reverse('register'),
                'action_text': 'Back to Register',
            },
        )
    except signing.BadSignature:
        return render(
            request,
            'users/verify_email_result.html',
            {
                'success': False,
                'heading': 'Invalid Verification Link',
                'message': 'This verification link is invalid. Please use the latest email link.',
                'action_url': reverse('login'),
                'action_text': 'Go to Login',
            },
        )

    user = User.objects.filter(
        id=payload.get('user_id'),
        email__iexact=payload.get('email', ''),
    ).first()

    if not user:
        return render(
            request,
            'users/verify_email_result.html',
            {
                'success': False,
                'heading': 'Account Not Found',
                'message': 'Verification failed because this account does not exist anymore.',
                'action_url': reverse('register'),
                'action_text': 'Create New Account',
            },
        )

    profile, _ = Profile.objects.get_or_create(
        user=user,
        defaults={'role': 'student'}
    )

    if profile.email_verified:
        return render(
            request,
            'users/verify_email_result.html',
            {
                'success': True,
                'heading': 'Email Already Verified',
                'message': 'Your email is already verified. You can log in now.',
                'action_url': reverse('login'),
                'action_text': 'Go to Login',
            },
        )

    profile.email_verified = True
    profile.save(update_fields=['email_verified'])
    return render(
        request,
        'users/verify_email_result.html',
        {
            'success': True,
            'heading': 'Email Verified Successfully',
            'message': 'Your account is now active. You can log in with your email and password.',
            'action_url': reverse('login'),
            'action_text': 'Continue to Login',
        },
    )


@login_required
def student_dashboard(request):
    role = getattr(getattr(request.user, 'profile', None), 'role', None)
    if role != 'student':
        messages.error(request, 'You are not allowed to access the student page.')
        return redirect(_redirect_for_role(request.user))

    profile, _ = Profile.objects.get_or_create(
        user=request.user,
        defaults={'role': 'student'}
    )

    if request.method == 'POST':
        form = StudentAttachmentDetailsForm(
            request.POST,
            instance=profile,
            user=request.user
        )
        if form.is_valid():
            form.save()
            messages.success(request, 'Your attachment details have been saved.')
            return redirect('student_dashboard')
        messages.error(request, 'Please correct the highlighted fields.')
    else:
        form = StudentAttachmentDetailsForm(instance=profile, user=request.user)

    return render(
        request,
        'users/student_dashboard.html',
        {'form': form, 'profile': profile}
    )


@login_required
def student_organization_location_view(request):
    role = getattr(getattr(request.user, 'profile', None), 'role', None)
    if role != 'student':
        messages.error(request, 'You are not allowed to access this page.')
        return redirect(_redirect_for_role(request.user))

    profile, _ = Profile.objects.get_or_create(
        user=request.user,
        defaults={'role': 'student'}
    )

    if request.method == 'POST':
        form = StudentOrganizationLocationForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Organization location details have been saved.')
            return redirect('student_dashboard')
        messages.error(request, 'Please correct the highlighted location fields.')
    else:
        form = StudentOrganizationLocationForm(instance=profile)

    return render(
        request,
        'users/student_organization_location.html',
        {'form': form, 'profile': profile}
    )


@login_required
def admin_dashboard(request):
    if not _is_admin_user(request.user):
        messages.error(request, 'You are not allowed to access the administrator page.')
        return redirect(_redirect_for_role(request.user))

    _ensure_profiles_for_all_users()

    students = User.objects.filter(profile__role='student').order_by('-date_joined')
    supervisors = User.objects.filter(profile__role='supervisor').order_by('-date_joined')
    manageable_users = User.objects.select_related('profile').order_by('email')

    context = {
        'students': students,
        'supervisors': supervisors,
        'manageable_users': manageable_users,
        'total_students': students.count(),
        'total_supervisors': supervisors.count(),
        'pending_assessments': Assessment.objects.filter(status='pending').count(),
        'done_assessments': Assessment.objects.filter(status='done').count(),
    }

    return render(request, 'users/admin_dashboard.html', context)


@login_required
def admin_students_view(request):
    if not _is_admin_user(request.user):
        messages.error(request, 'You are not allowed to access student management.')
        return redirect(_redirect_for_role(request.user))

    _ensure_profiles_for_all_users()

    selected_org = request.GET.get('organization', '').strip()
    students = User.objects.select_related('profile').filter(profile__role='student')
    if selected_org:
        students = students.filter(profile__organization_name__iexact=selected_org)
    students = students.order_by('first_name', 'last_name', 'email')

    assignments = SupervisorStudentAssignment.objects.select_related('supervisor').filter(student__in=students)
    assignment_map = {}
    for assignment in assignments:
        assignment_map.setdefault(assignment.student_id, assignment.supervisor)

    supervisors = list(_supervisors_with_load(selected_org))

    student_rows = [
        {
            'student': student,
            'assigned_supervisor': assignment_map.get(student.id),
        }
        for student in students
    ]

    context = {
        'student_rows': student_rows,
        'supervisor_options': supervisors,
        'organization_options': _organization_choices(),
        'selected_organization': selected_org,
    }

    return render(request, 'users/admin_students.html', context)


@login_required
def admin_supervisors_view(request):
    if not _is_admin_user(request.user):
        messages.error(request, 'You are not allowed to access supervisor management.')
        return redirect(_redirect_for_role(request.user))

    _ensure_profiles_for_all_users()

    selected_org = request.GET.get('organization', '').strip()
    supervisors = _supervisors_with_load(selected_org)

    context = {
        'supervisors': supervisors,
        'organization_options': _organization_choices(),
        'selected_organization': selected_org,
    }

    return render(request, 'users/admin_supervisors.html', context)


@login_required
def admin_assign_student_view(request):
    if not _is_admin_user(request.user):
        messages.error(request, 'You are not allowed to perform this action.')
        return redirect(_redirect_for_role(request.user))

    if request.method != 'POST':
        return redirect('admin_students')

    student_id = request.POST.get('student_id', '').strip()
    supervisor_id = request.POST.get('supervisor_id', '').strip()
    selected_org = request.POST.get('organization', '').strip()

    student = User.objects.select_related('profile').filter(id=student_id, profile__role='student').first()
    supervisor = User.objects.select_related('profile').filter(id=supervisor_id, profile__role='supervisor').first()

    if not student or not supervisor:
        messages.error(request, 'Invalid student or supervisor selection.')
        return redirect(f"{reverse('admin_students')}?organization={selected_org}") if selected_org else redirect('admin_students')

    student_org = _normalize_org_name(getattr(student.profile, 'organization_name', ''))
    supervisor_org = _normalize_org_name(getattr(supervisor.profile, 'organization_name', ''))

    if student_org != supervisor_org:
        messages.error(request, 'Student and supervisor must belong to the same organization.')
        return redirect(f"{reverse('admin_students')}?organization={selected_org}") if selected_org else redirect('admin_students')

    SupervisorStudentAssignment.objects.filter(student=student).exclude(supervisor=supervisor).delete()
    SupervisorStudentAssignment.objects.get_or_create(supervisor=supervisor, student=student)
    messages.success(request, f'{student.email} assigned to {supervisor.email}.')

    return redirect(f"{reverse('admin_students')}?organization={selected_org}") if selected_org else redirect('admin_students')


@login_required
def admin_auto_assign_students_view(request):
    if not _is_admin_user(request.user):
        messages.error(request, 'You are not allowed to perform this action.')
        return redirect(_redirect_for_role(request.user))

    if request.method != 'POST':
        return redirect('admin_students')

    selected_org = request.POST.get('organization', '').strip()
    if not selected_org:
        messages.error(request, 'Select an organization before auto-assigning students.')
        return redirect('admin_students')

    students = list(User.objects.filter(
        profile__role='student',
        profile__organization_name__iexact=selected_org,
    ).order_by('first_name', 'last_name', 'email'))

    if not students:
        messages.info(request, 'No students found for the selected organization.')
        return redirect(f"{reverse('admin_students')}?organization={selected_org}")

    supervisors = list(_supervisors_with_load(selected_org))
    if not supervisors:
        messages.error(request, 'No supervisors found for the selected organization.')
        return redirect(f"{reverse('admin_students')}?organization={selected_org}")

    assigned_student_ids = set(
        SupervisorStudentAssignment.objects.filter(student__in=students).values_list('student_id', flat=True)
    )
    unassigned_students = [student for student in students if student.id not in assigned_student_ids]

    if not unassigned_students:
        messages.info(request, 'All students in this organization are already assigned.')
        return redirect(f"{reverse('admin_students')}?organization={selected_org}")

    supervisor_load = [
        {
            'supervisor': supervisor,
            'count': supervisor.assigned_students_count,
        }
        for supervisor in supervisors
    ]

    for student in unassigned_students:
        supervisor_load.sort(key=lambda item: (item['count'], item['supervisor'].id))
        selected = supervisor_load[0]
        SupervisorStudentAssignment.objects.get_or_create(
            supervisor=selected['supervisor'],
            student=student,
        )
        selected['count'] += 1

    messages.success(request, f'Assigned {len(unassigned_students)} students for organization {selected_org}.')
    return redirect(f"{reverse('admin_students')}?organization={selected_org}")


@login_required
def change_user_role_view(request):
    if not _is_admin_user(request.user):
        messages.error(request, 'You are not allowed to perform this action.')
        return redirect(_redirect_for_role(request.user))

    if request.method != 'POST':
        messages.error(request, 'Invalid request method for role change.')
        return redirect('admin_dashboard')

    user_id = request.POST.get('user_id', '').strip()
    new_role = request.POST.get('role', '').strip().lower()
    allowed_roles = {'student', 'supervisor', 'admin'}

    if new_role not in allowed_roles:
        messages.error(request, 'Invalid role selected.')
        return redirect('admin_dashboard')

    target_user = User.objects.filter(id=user_id).first()
    if not target_user:
        messages.error(request, 'Selected user was not found.')
        return redirect('admin_dashboard')

    target_profile, _ = Profile.objects.get_or_create(
        user=target_user,
        defaults={'role': 'student'}
    )

    if target_user.id == request.user.id and new_role != 'admin':
        messages.error(request, 'You cannot remove your own administrator role.')
        return redirect('admin_dashboard')

    if new_role in {'supervisor', 'admin'} and not target_profile.email_verified:
        messages.error(request, 'Only email-verified users can be promoted to supervisor or administrator.')
        return redirect('admin_dashboard')

    target_profile.role = new_role
    target_profile.save(update_fields=['role'])
    messages.success(request, f"{target_user.email} role updated to {target_profile.get_role_display()}.")
    return redirect('admin_dashboard')


@login_required
def pending_assessments_view(request):
    if not _is_admin_user(request.user):
        messages.error(request, 'You are not allowed to access pending assessments.')
        return redirect(_redirect_for_role(request.user))

    assessments = Assessment.objects.select_related('student').filter(
        status='pending',
        student__profile__role='student'
    ).order_by('-created_at')

    return render(
        request,
        'users/assessment_list.html',
        {
            'title': 'Pending Assessments',
            'assessments': assessments,
            'empty_message': 'No pending assessments found for students.',
        }
    )


@login_required
def done_assessments_view(request):
    if not _is_admin_user(request.user):
        messages.error(request, 'You are not allowed to access completed assessments.')
        return redirect(_redirect_for_role(request.user))

    assessments = Assessment.objects.select_related('student').filter(
        status='done',
        student__profile__role='student'
    ).order_by('-updated_at')

    return render(
        request,
        'users/assessment_list.html',
        {
            'title': 'Completed Assessments',
            'assessments': assessments,
            'empty_message': 'No completed assessments found for students.',
        }
    )


@login_required
def supervisor_dashboard(request):
    role = getattr(getattr(request.user, 'profile', None), 'role', None)
    if role != 'supervisor':
        messages.error(request, 'You are not allowed to access the supervisor page.')
        return redirect(_redirect_for_role(request.user))

    return render(request, 'users/supervisor_dashboard.html')