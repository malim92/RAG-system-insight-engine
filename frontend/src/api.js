const TENANT_ID = 'demo'

async function handle(res) {
  const body = await res.json().catch(() => ({}))
  if (!res.ok) {
    // The backend propagates the AI service's error body; surface it as-is.
    throw new Error(body.error || body.detail || `Request failed: ${res.status}`)
  }
  return body
}

export async function uploadDocument(file) {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch('/api/documents/upload', {
    method: 'POST',
    headers: { 'X-Tenant-Id': TENANT_ID },
    body: form,
  })
  return handle(res) // { documentId, status, originalName }
}

export async function getDocumentStatus(documentId) {
  const res = await fetch(`/api/documents/${documentId}`)
  return handle(res) // { documentId, status, originalName, errorMessage }
}

export async function askQuestion(question) {
  const res = await fetch('/api/query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, tenantId: TENANT_ID }),
  })
  return handle(res) // { answer, citations[] }
}
