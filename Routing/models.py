from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class Location(models.Model):
    name = models.CharField(max_length=100)
    latitude = models.FloatField()
    longitude = models.FloatField()

class Route(models.Model):

    route_name = models.CharField(
        max_length=100
    )

    def __str__(self):
        return self.route_name


class SupervisorStudentAssignment(models.Model):
    supervisor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='assigned_students_links'
    )
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='assigned_supervisors_links'
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['supervisor', 'student'],
                name='unique_supervisor_student_assignment'
            )
        ]

    def __str__(self):
        return f"{self.supervisor.email} -> {self.student.email}"