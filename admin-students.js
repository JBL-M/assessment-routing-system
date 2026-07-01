(() => {
  const renderQueue = () => {
    const tbody = document.querySelector('#studentsQueueTable tbody')
    if (!tbody) {
      return
    }

    tbody.innerHTML = '<tr><td colspan="7" class="text-center empty-state">Backend integration pending: student applications will appear here once API storage is enabled.</td></tr>'
  }

  renderQueue()
})()
