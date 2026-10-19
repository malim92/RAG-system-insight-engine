import { useEffect, useRef, useState } from 'react'
import { uploadDocument, getDocumentStatus } from '../api.js'

const STATUS_LABELS = {
  PENDING: 'Queued',
  PROCESSING: 'Processing',
  COMPLETED: 'Ready',
  FAILED: 'Failed',
}

export default function DocumentManager({ onUploaded }) {
  const [jobs, setJobs] = useState([]) // { documentId, originalName, status, errorMessage? }
  const fileInputRef = useRef(null)
  const [uploading, setUploading] = useState(false)

  async function handleFile(e) {
    const file = e.target.files?.[0]
    if (!file) return
    e.target.value = '' // allow re-selecting the same file
    setUploading(true)
    try {
      const { documentId, originalName } = await uploadDocument(file)
      setJobs(prev => [...prev, { documentId, originalName, status: 'PENDING' }])
    } catch (err) {
      setJobs(prev => [...prev, {
        documentId: `local-${Date.now()}`,
        originalName: file.name,
        status: 'FAILED',
        errorMessage: err.message,
      }])
    } finally {
      setUploading(false)
    }
  }

  // Poll statuses of in-flight documents. One interval for all jobs —
  // simpler and kinder to the backend than a timer per document.
  useEffect(() => {
    const inflight = jobs.filter(j =>
      j.status === 'PENDING' || j.status === 'PROCESSING'
    )
    if (inflight.length === 0) return

    const timer = setInterval(async () => {
      for (const job of inflight) {
        try {
          const status = await getDocumentStatus(job.documentId)
          setJobs(prev => prev.map(j =>
            j.documentId === job.documentId
              ? { ...j, status: status.status, errorMessage: status.errorMessage || undefined }
              : j
          ))
          if (status.status === 'COMPLETED') onUploaded()
        } catch {
          // Document may not be visible yet; retry on next tick.
        }
      }
    }, 1500)

    return () => clearInterval(timer)
  }, [jobs, onUploaded])

  return (
    <div className="doc-manager">
      <h2>Documents</h2>

      <label className={`upload-drop ${uploading ? 'disabled' : ''}`}>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.txt,.md"
          onChange={handleFile}
          disabled={uploading}
          hidden
        />
        {uploading ? 'Uploading…' : '⬆ Upload PDF / TXT'}
      </label>

      <ul className="doc-list">
        {jobs.length === 0 && (
          <li className="doc-empty">No documents yet. Upload one to start asking questions.</li>
        )}
        {[...jobs].reverse().map(job => (
          <li key={job.documentId} className={`doc-item status-${job.status.toLowerCase()}`}>
            <div className="doc-name" title={job.originalName}>{job.originalName}</div>
            <div className="doc-status">
              <span className={`badge badge-${job.status.toLowerCase()}`}>
                {STATUS_LABELS[job.status] || job.status}
              </span>
            </div>
            {job.errorMessage && (
              <div className="doc-error" title={job.errorMessage}>
                {job.errorMessage}
              </div>
            )}
          </li>
        ))}
      </ul>
    </div>
  )
}
