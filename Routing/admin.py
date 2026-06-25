from django.contrib import admin
from .models import Location, Route, SupervisorStudentAssignment

# Register your models here.
@admin.register(SupervisorStudentAssignment)
class SupervisorStudentAssignmentAdmin(admin.ModelAdmin):
	list_display = ('supervisor', 'student', 'assigned_at')
	list_filter = ('assigned_at',)
	search_fields = ('supervisor__email', 'student__email', 'student__first_name', 'student__last_name')


admin.site.register(Route)
admin.site.register(Location)
