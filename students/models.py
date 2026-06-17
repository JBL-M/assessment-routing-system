from django.db import models

# Create your models here.

class Student(models.Model):
    name = models.CharField(max_length=100)
    reg_number = models.CharField(max_length=50)
    company = models.CharField(max_length=100)
    
    latitude = models.FloatField()
    longitude = models.FloatField()

    def __str__(self):
        return self.name