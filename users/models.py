from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Profile(models.Model):

    ROLE_CHOICES = [
        ('student', 'Student'),
        ('admin', 'Administrator'),
        ('supervisor', 'Supervisor'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES
    )

    email_verified = models.BooleanField(default=False)

    school_id = models.CharField(max_length=50, blank=True)
    course = models.CharField(max_length=150, blank=True)
    year_of_study = models.PositiveSmallIntegerField(null=True, blank=True)

    organization_name = models.CharField(max_length=200, blank=True)
    organization_location = models.CharField(max_length=200, blank=True)
    organization_main_road = models.CharField(max_length=200, blank=True)
    organization_latitude = models.FloatField(null=True, blank=True)
    organization_longitude = models.FloatField(null=True, blank=True)

    ATTACHMENT_TYPE_CHOICES = [
        ('service_based', 'Service-Based Learning'),
        ('work_based', 'Work-Based Learning'),
    ]

    attachment_type = models.CharField(
        max_length=30,
        choices=ATTACHMENT_TYPE_CHOICES,
        blank=True
    )

    def __str__(self):
        return f"{self.user.username} - {self.role}"


class Assessment(models.Model):

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('done', 'Done'),
    ]

    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='assessments'
    )

    title = models.CharField(max_length=150)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.student.username} - {self.title} ({self.status})"