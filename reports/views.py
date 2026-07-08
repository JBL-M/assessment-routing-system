import csv
from io import BytesIO

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from users.models import Assessment


def _is_admin_user(user):
	return getattr(getattr(user, 'profile', None), 'role', None) == 'admin'


def _assessment_status_details(status):
	status_map = {
		'pending': {'label': 'Pending', 'filename': 'pending_assessments'},
		'done': {'label': 'Completed', 'filename': 'completed_assessments'},
	}
	return status_map.get(status)


def _assessment_queryset(status):
	order_by = '-created_at' if status == 'pending' else '-updated_at'
	return Assessment.objects.select_related('student', 'student__profile').filter(
		status=status,
		student__profile__role='student',
	).order_by(order_by)


@login_required
def assessment_reports_home(request):
	if not _is_admin_user(request.user):
		messages.error(request, 'You are not allowed to access reports.')
		return redirect('home')

	context = {
		'pending_count': _assessment_queryset('pending').count(),
		'done_count': _assessment_queryset('done').count(),
	}
	return render(request, 'reports/assessment_reports.html', context)


@login_required
def download_assessments_csv(request, status):
	if not _is_admin_user(request.user):
		messages.error(request, 'You are not allowed to download reports.')
		return redirect('home')

	status_details = _assessment_status_details(status)
	if not status_details:
		messages.error(request, 'Invalid assessment status selected for report download.')
		return redirect('assessment_reports_home')

	now = timezone.localtime().strftime('%Y%m%d_%H%M%S')
	filename = f"{status_details['filename']}_{now}.csv"

	response = HttpResponse(content_type='text/csv')
	response['Content-Disposition'] = f'attachment; filename="{filename}"'

	writer = csv.writer(response)
	writer.writerow([
		'Student Name',
		'Student Email',
		'Assessment Title',
		'Course',
		'Attachment Type',
		'Status',
		'Last Updated',
	])

	for assessment in _assessment_queryset(status):
		full_name = assessment.student.get_full_name().strip() or assessment.student.email
		profile = getattr(assessment.student, 'profile', None)
		course = getattr(profile, 'course', '') or 'N/A'
		attachment_type = profile.get_attachment_type_display() if profile and profile.attachment_type else 'Not set'
		writer.writerow([
			full_name,
			assessment.student.email,
			assessment.title,
			course,
			attachment_type,
			assessment.get_status_display(),
			timezone.localtime(assessment.updated_at).strftime('%Y-%m-%d %H:%M:%S'),
		])

	return response


@login_required
def download_assessments_pdf(request, status):
	if not _is_admin_user(request.user):
		messages.error(request, 'You are not allowed to download reports.')
		return redirect('home')

	status_details = _assessment_status_details(status)
	if not status_details:
		messages.error(request, 'Invalid assessment status selected for report download.')
		return redirect('assessment_reports_home')

	rows = []
	for assessment in _assessment_queryset(status):
		full_name = assessment.student.get_full_name().strip() or assessment.student.email
		rows.append({
			'student_name': full_name,
			'email': assessment.student.email,
			'title': assessment.title,
			'status': assessment.get_status_display(),
			'updated': timezone.localtime(assessment.updated_at).strftime('%Y-%m-%d %H:%M'),
		})

	buffer = BytesIO()
	pdf = canvas.Canvas(buffer, pagesize=A4)
	page_width, page_height = A4
	margin_left = 35
	y = page_height - 40

	now_label = timezone.localtime().strftime('%Y-%m-%d %H:%M:%S')
	pdf.setFont('Helvetica-Bold', 14)
	pdf.drawString(margin_left, y, f"{status_details['label']} Assessments Report")
	y -= 20
	pdf.setFont('Helvetica', 10)
	pdf.drawString(margin_left, y, f"Generated: {now_label}")
	y -= 22

	headers = ['Student', 'Email', 'Assessment', 'Status', 'Updated']
	pdf.setFont('Helvetica-Bold', 9)
	pdf.drawString(35, y, headers[0])
	pdf.drawString(140, y, headers[1])
	pdf.drawString(265, y, headers[2])
	pdf.drawString(420, y, headers[3])
	pdf.drawString(485, y, headers[4])
	y -= 14
	pdf.setFont('Helvetica', 8)

	if not rows:
		pdf.drawString(margin_left, y, 'No records found.')
	else:
		for row in rows:
			if y < 40:
				pdf.showPage()
				y = page_height - 40
				pdf.setFont('Helvetica-Bold', 9)
				pdf.drawString(35, y, headers[0])
				pdf.drawString(140, y, headers[1])
				pdf.drawString(265, y, headers[2])
				pdf.drawString(420, y, headers[3])
				pdf.drawString(485, y, headers[4])
				y -= 14
				pdf.setFont('Helvetica', 8)

			pdf.drawString(35, y, str(row['student_name'])[:20])
			pdf.drawString(140, y, str(row['email'])[:22])
			pdf.drawString(265, y, str(row['title'])[:28])
			pdf.drawString(420, y, str(row['status'])[:10])
			pdf.drawString(485, y, str(row['updated'])[:16])
			y -= 12

	pdf.save()
	buffer.seek(0)

	now = timezone.localtime().strftime('%Y%m%d_%H%M%S')
	filename = f"{status_details['filename']}_{now}.pdf"
	response = HttpResponse(buffer.read(), content_type='application/pdf')
	response['Content-Disposition'] = f'attachment; filename="{filename}"'
	return response
