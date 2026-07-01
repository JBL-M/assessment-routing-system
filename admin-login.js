const { $, toDisplayName, navigateTo, showTemporarily } = window.AppUtils
const validEmail = 'admin@strathmore.edu'
const validPassword = 'admin123'

$('adminLoginForm').addEventListener('submit', e => {
  e.preventDefault()

  const email = $('adminEmail').value
  const password = $('adminPassword').value
  const error = $('errorMessage')

  if (email === validEmail && password === validPassword) {
    localStorage.setItem('currentAdminName', toDisplayName(email))
    localStorage.setItem('currentAdminEmail', email)
    navigateTo('admin-dashboard.html')
    return
  }

  showTemporarily(error)
})

$('backHomeBtn').addEventListener('click', () => {
  navigateTo('index.html')
})
