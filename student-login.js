const { $, toDisplayName, navigateTo, showTemporarily } = window.AppUtils
const validEmail = 'student@strathmore.edu'
const validPassword = 'student123'

$('studentLoginForm').addEventListener('submit', e => {
  e.preventDefault()
  const email = $('studentEmail').value
  const password = $('studentPassword').value
  const error = $('errorMessage')

  if (email === validEmail && password === validPassword) {
    localStorage.setItem('currentStudentName', toDisplayName(email))
    localStorage.setItem('currentStudentEmail', email)
    navigateTo('student-dashboard.html')
    return
  }

  showTemporarily(error)
})

$('backHomeBtn').addEventListener('click', () => {
  navigateTo('index.html')
})
