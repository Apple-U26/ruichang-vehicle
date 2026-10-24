export function normalizeDriverName(value) {
  return typeof value === 'string' ? value.trim() : ''
}

function storageKey(user) {
  if (user?.id != null && user.id !== '') return `lastDriverName:v2:id:${user.id}`
  if (user?.username) return `lastDriverName:v2:username:${encodeURIComponent(user.username)}`
  return null
}

export function getRememberedDriverName(user) {
  try {
    const key = storageKey(user)
    const name = key ? normalizeDriverName(localStorage.getItem(key)) : ''
    return name.length <= 50 ? name : ''
  } catch {
    return ''
  }
}

export function rememberDriverName(user, value) {
  const name = normalizeDriverName(value)
  if (!name || name.length > 50) return
  try {
    const key = storageKey(user)
    if (key) localStorage.setItem(key, name)
  } catch {
    // Browser storage must never turn a successful trip registration into a failure.
  }
}
