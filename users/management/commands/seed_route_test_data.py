from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from Routing.models import SupervisorStudentAssignment
from users.models import Assessment, Profile


class Command(BaseCommand):
    help = (
        "Seed supervisor/student data for route optimization tests with clustered "
        "students in the same area."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--supervisor-email",
            default="supervisor.route@test.local",
            help="Supervisor email/username to create or reuse.",
        )
        parser.add_argument(
            "--password",
            default="TestPass123!",
            help="Password to set for created users.",
        )
        parser.add_argument(
            "--clear-existing-test-students",
            action="store_true",
            help="Delete previously seeded students with email domain @route-test.local.",
        )

    def handle(self, *args, **options):
        supervisor_email = options["supervisor_email"].strip().lower()
        password = options["password"]
        clear_existing = options["clear_existing_test_students"]

        if clear_existing:
            self._clear_existing_seeded_students()

        supervisor = self._create_or_update_supervisor(supervisor_email, password)

        shared_location = "Westlands, Nairobi"

        clusters = [
            {
                "label": "Westlands A",
                "location": shared_location,
                "road": "Ngong Road",
                "center": (-1.2645, 36.8047),
                "organization": "Westlands Innovation Hub",
                "attachment_type": "work_based",
                "course": "Computer Science",
                "year": 4,
                "count": 5,
            },
            {
                "label": "Westlands B",
                "location": shared_location,
                "road": "Waiyaki Way",
                "center": (-1.2645, 36.8047),
                "organization": "Metro Health Services",
                "attachment_type": "service_based",
                "course": "Information Technology",
                "year": 3,
                "count": 5,
            },
            {
                "label": "Westlands C",
                "location": shared_location,
                "road": "Argwings Kodhek Road",
                "center": (-1.2645, 36.8047),
                "organization": "Summit Research Partners",
                "attachment_type": "service_based",
                "course": "Software Engineering",
                "year": 2,
                "count": 4,
            },
        ]

        created_students = 0
        reused_students = 0
        created_assignments = 0

        student_index = 1
        for cluster in clusters:
            for i in range(cluster["count"]):
                lat, lng = self._jitter_point(cluster["center"], i)
                email = f"student{student_index:02d}@route-test.local"

                student, created = self._create_or_update_student(
                    email=email,
                    password=password,
                    first_name=f"Test{student_index:02d}",
                    last_name=cluster["label"].replace(" ", ""),
                    school_id=f"SC{2026}{student_index:03d}",
                    course=cluster["course"],
                    year_of_study=cluster["year"],
                    organization_name=cluster["organization"],
                    organization_location=cluster["location"],
                    organization_main_road=cluster["road"],
                    organization_latitude=lat,
                    organization_longitude=lng,
                    attachment_type=cluster["attachment_type"],
                )

                if created:
                    created_students += 1
                else:
                    reused_students += 1

                _, assignment_created = SupervisorStudentAssignment.objects.get_or_create(
                    supervisor=supervisor,
                    student=student,
                )
                if assignment_created:
                    created_assignments += 1

                Assessment.objects.get_or_create(
                    student=student,
                    title=f"{cluster['label']} assessment",
                    defaults={"status": "pending"},
                )

                student_index += 1

        total_assigned = SupervisorStudentAssignment.objects.filter(supervisor=supervisor).count()

        self.stdout.write(self.style.SUCCESS("Route optimization test data ready."))
        self.stdout.write(f"Supervisor: {supervisor.email}")
        self.stdout.write(f"Created students: {created_students}")
        self.stdout.write(f"Reused students: {reused_students}")
        self.stdout.write(f"New assignments: {created_assignments}")
        self.stdout.write(f"Total students assigned to supervisor: {total_assigned}")
        self.stdout.write("Areas seeded: Westlands with multiple organizations")

    def _create_or_update_supervisor(self, email, password):
        user, _ = User.objects.get_or_create(
            username=email,
            defaults={
                "email": email,
                "first_name": "Route",
                "last_name": "Supervisor",
            },
        )

        user.email = email
        user.first_name = user.first_name or "Route"
        user.last_name = user.last_name or "Supervisor"
        user.set_password(password)
        user.save(update_fields=["email", "first_name", "last_name", "password"])

        Profile.objects.update_or_create(
            user=user,
            defaults={
                "role": "supervisor",
                "email_verified": True,
            },
        )

        return user

    def _create_or_update_student(self, **student_data):
        email = student_data.pop("email")
        password = student_data.pop("password")
        first_name = student_data.pop("first_name")
        last_name = student_data.pop("last_name")

        user, created = User.objects.get_or_create(
            username=email,
            defaults={
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
            },
        )

        user.email = email
        user.first_name = first_name
        user.last_name = last_name
        user.set_password(password)
        user.save(update_fields=["email", "first_name", "last_name", "password"])

        Profile.objects.update_or_create(
            user=user,
            defaults={
                "role": "student",
                "email_verified": True,
                **student_data,
            },
        )

        return user, created

    def _clear_existing_seeded_students(self):
        seeded_students = User.objects.filter(username__iendswith="@route-test.local")
        if not seeded_students.exists():
            return

        Assessment.objects.filter(student__in=seeded_students).delete()
        SupervisorStudentAssignment.objects.filter(student__in=seeded_students).delete()
        Profile.objects.filter(user__in=seeded_students).delete()
        seeded_students.delete()

    def _jitter_point(self, center, index):
        lat, lng = center
        offsets = [
            (0.0, 0.0),
            (0.0012, 0.0010),
            (-0.0011, 0.0008),
            (0.0009, -0.0011),
            (-0.0008, -0.0010),
            (0.0014, -0.0006),
        ]
        off_lat, off_lng = offsets[index % len(offsets)]
        return round(lat + off_lat, 6), round(lng + off_lng, 6)
