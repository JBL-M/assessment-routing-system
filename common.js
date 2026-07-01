(() => {
  const $ = id => document.getElementById(id)

  const getStorageJson = (key, fallback) => {
    try {
      const parsed = JSON.parse(localStorage.getItem(key) || 'null')
      return parsed ?? fallback
    } catch {
      return fallback
    }
  }

  const setStorageJson = (key, value) => {
    localStorage.setItem(key, JSON.stringify(value))
  }

  const navigateTo = path => {
    window.location.href = path
  }

  const showTemporarily = (element, duration = 3000, display = 'block') => {
    if (!element) {
      return
    }
    element.style.display = display
    setTimeout(() => {
      element.style.display = 'none'
    }, duration)
  }

  const toggleClassTemporarily = (element, className, duration = 3000) => {
    if (!element) {
      return
    }
    element.classList.add(className)
    setTimeout(() => {
      element.classList.remove(className)
    }, duration)
  }

  const toDisplayName = email =>
    (email.split('@')[0] || 'Student')
      .split(/[._-]+/)
      .filter(Boolean)
      .map(part => part[0].toUpperCase() + part.slice(1).toLowerCase())
      .join(' ')

  window.AppUtils = {
    $,
    getStorageJson,
    setStorageJson,
    toDisplayName,
    navigateTo,
    showTemporarily,
    toggleClassTemporarily
  }
})()
