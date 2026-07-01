const { $, toggleClassTemporarily } = window.AppUtils
const runtimeApps = []
const runtimeReports = []
const getApps = () => runtimeApps
const setApps = apps => {
  runtimeApps.length = 0
  runtimeApps.push(...apps)
}
const getReports = () => runtimeReports
const setReports = reports => {
  runtimeReports.length = 0
  runtimeReports.push(...reports)
}

function showSection(name) {
  document.querySelectorAll('.page-section').forEach(section => section.classList.remove('active'))
  document.querySelectorAll('.sidebar-menu a').forEach(link => link.classList.remove('active'))

  $(name + 'Section')?.classList.add('active')
  document.querySelector(`[data-section="${name}"]`)?.classList.add('active')
}

function renderCurrentStudent() {
  const name = (localStorage.getItem('currentStudentName') || '').trim() || 'Student'
  const email = (localStorage.getItem('currentStudentEmail') || '').trim()
  const initials =
    name
      .split(' ')
      .filter(Boolean)
      .slice(0, 2)
      .map(part => part[0].toUpperCase())
      .join('') || 'S'

  if ($('studentName')) {
    $('studentName').textContent = name
  }

  if ($('studentEmailDisplay')) {
    $('studentEmailDisplay').textContent = email
  }

  if ($('studentAvatar')) {
    $('studentAvatar').textContent = initials
  }
}

function renderAttachments() {
  const apps = getApps()
  $('attachmentList').innerHTML = apps.length
    ? apps
        .map(
          app =>
            `<div class="attachment-item"><b>${app.type} - ${app.organisation}</b><p>${app.startPeriod} to ${app.endPeriod}</p><p>Status: Successful</p></div>`
        )
        .join('')
    : '<p>No successful applications yet.</p>'
}

function buildSupervisorVisitDate(startPeriod) {
  if (!startPeriod) {
    return 'Date to be confirmed by your supervisor.'
  }

  const startDate = new Date(startPeriod)
  if (Number.isNaN(startDate.getTime())) {
    return 'Date to be confirmed by your supervisor.'
  }

  startDate.setDate(startDate.getDate() + 14)
  return startDate.toLocaleDateString()
}

function renderNotifications() {
  const apps = getApps()
  const notificationList = $('notificationList')

  if (!notificationList) {
    return
  }

  if (!apps.length) {
    notificationList.innerHTML = '<p class="notification-empty">No notifications yet. You will see updates after your attachment is reviewed.</p>'
    return
  }

  notificationList.innerHTML = apps
    .map(app => {
      const organisation = app.organisation || 'your selected organization'
      const supervisorName = app.supervisorName || 'Assigned Supervisor'
      const visitDate = buildSupervisorVisitDate(app.startPeriod)

      return `
        <article class="notification-card accepted">
          <h4>Attachment Accepted</h4>
          <p>Your ${app.type || 'attachment'} application at <strong>${organisation}</strong> has been accepted.</p>
        </article>
        <article class="notification-card visit">
          <h4>Supervisor Visit Update</h4>
          <p>${supervisorName} is expected to visit on <strong>${visitDate}</strong>.</p>
        </article>
      `
    })
    .join('')
}

function attachSidebarHandlers() {
  document.querySelectorAll('.sidebar-menu a[data-section]').forEach(link => {
    link.addEventListener('click', event => {
      event.preventDefault()
      showSection(link.dataset.section)
    })
  })
}

function attachFormHandler() {
  $('attachmentForm').addEventListener('submit', e => {
    e.preventDefault()

    if (new Date($('startPeriod').value) >= new Date($('endPeriod').value)) {
      alert('End date must be after start date')
      return
    }

    const newApplication = {
      studentName: (localStorage.getItem('currentStudentName') || 'Student').trim() || 'Student',
      studentEmail: (localStorage.getItem('currentStudentEmail') || '').trim(),
      status: 'pending',
      type: $('attachmentType').value,
      organisation: $('organisation').value,
      organisationLocation: $('organisationLocation').value,
      supervisorName: $('supervisorName')?.value || '',
      supervisorEmail: $('supervisorEmail')?.value || '',
      courseName: $('courseName')?.value || '',
      studentNumber: $('studentNumber')?.value || '',
      startPeriod: $('startPeriod').value,
      endPeriod: $('endPeriod').value
    }

    setApps([newApplication, ...getApps()])
    renderAttachments()
    renderNotifications()

    $('message').textContent = `Submitted for ${newApplication.organisation}. Not persisted until backend is connected.`
    toggleClassTemporarily($('successMessage'), 'show')

    e.target.reset()
  })
}

function attachAssessmentReportHandler() {
  const reportForm = $('assessmentReportForm')
  if (!reportForm) {
    return
  }

  reportForm.addEventListener('submit', e => {
    e.preventDefault()

    const reportDate = $('reportDate').value
    if (!reportDate) {
      alert('Please provide the assessment date')
      return
    }

    const reportEntry = {
      studentName: (localStorage.getItem('currentStudentName') || 'Student').trim() || 'Student',
      studentEmail: (localStorage.getItem('currentStudentEmail') || '').trim(),
      studentNumber: ($('studentNumber')?.value || '').trim(),
      organisation: $('reportOrganisation').value,
      assessed: $('reportAssessed').value,
      assessmentDate: reportDate,
      remarks: $('reportRemarks').value,
      submittedAt: new Date().toISOString()
    }

    setReports([reportEntry, ...getReports()])
    $('reportMessage').textContent = `Report submitted for ${reportEntry.organisation}. Not persisted until backend is connected.`
    toggleClassTemporarily($('reportSuccessMessage'), 'show')
    reportForm.reset()
  })
}

attachSidebarHandlers()
attachFormHandler()
attachAssessmentReportHandler()
renderCurrentStudent()
renderAttachments()
renderNotifications()
