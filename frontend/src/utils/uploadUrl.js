export function resolveUploadUrl(value) {
  const token = localStorage.getItem('token') || ''
  if (typeof value === 'string' && value.startsWith('/uploads/')) {
    const name = value.slice('/uploads/'.length)
    return `/api/uploads/${encodeURIComponent(name)}?token=${encodeURIComponent(token)}`
  }
  return value
}

export function resolveUploadUrls(values) {
  return (values || []).map(resolveUploadUrl)
}
