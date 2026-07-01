(() => {
  const setValue = (id, value) => {
    const el = document.getElementById(id)
    if (el) {
      el.textContent = String(value)
    }
  }

  const renderTable = () => {
    const tbody = document.querySelector('#applicationsTable tbody')
    if (!tbody) {
      return
    }

    tbody.innerHTML = '<tr><td colspan="6" class="text-center empty-state">Backend integration pending: student applications will appear here once API storage is enabled.</td></tr>'
  }

  setValue('totalAppliedCount', 0)
  setValue('pendingAssessmentCount', 0)
  setValue('completedAssessmentCount', 0)
  renderTable()
})()
