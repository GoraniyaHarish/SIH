import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type ChunkPreview, type Doc } from '../lib/api'
import {
  Banner, Card, EmptyState, ErrorState, Modal, Skeleton, useFetch, useToast,
  formatBytes, formatDateTime,
} from '../components/ui'
import { IconChat, IconDoc, IconQuiz, IconRefresh, IconTrash, IconUpload } from '../components/icons'

const STATUS_TONE: Record<string, string> = {
  completed: 'tag-official',
  processing: 'tag-provisional',
  queued: 'tag-pending',
  failed: 'tag-critical',
}

export default function Documents() {
  const { push } = useToast()
  const inputRef = useRef<HTMLInputElement>(null)
  const docs = useFetch<Doc[]>(() => api.get<Doc[]>('/documents?limit=60'))
  const [uploading, setUploading] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<Doc | null>(null)
  const [inspect, setInspect] = useState<Doc | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [visibility, setVisibility] = useState('private')
  const [busyId, setBusyId] = useState<string | null>(null)

  async function upload(file: File) {
    setUploading(true)
    setError(null)
    const form = new FormData()
    form.append('file', file)
    form.append('title', file.name.replace(/\.[^.]+$/, ''))
    form.append('visibility', visibility)
    try {
      const doc = await api.upload<Doc>('/documents', form)
      push(
        doc.status === 'completed'
          ? `Indexed "${doc.title}" — ${doc.chunk_count} passages ready`
          : `Uploaded, but processing ${doc.status}: ${doc.error_detail ?? doc.error_code}`,
        doc.status === 'completed' ? 'success' : 'error',
      )
      docs.refetch()
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Upload failed'
      setError(msg)
      push(msg, 'error')
    } finally {
      setUploading(false)
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  async function confirmDelete() {
    if (!deleteTarget) return
    setBusyId(deleteTarget.id)
    try {
      await api.del(`/documents/${deleteTarget.id}`)
      push(`Deleted "${deleteTarget.title}" and its indexed passages`, 'success')
      setDeleteTarget(null)
      docs.refetch()
    } catch (e) {
      push(e instanceof Error ? e.message : 'Could not delete', 'error')
    } finally {
      setBusyId(null)
    }
  }

  async function reprocess(doc: Doc) {
    setBusyId(doc.id)
    try {
      const updated = await api.post<Doc>(`/documents/${doc.id}/reprocess`)
      push(
        updated.status === 'completed' ? 'Reprocessed and indexed' : `Still ${updated.status}: ${updated.error_code}`,
        updated.status === 'completed' ? 'success' : 'error',
      )
      docs.refetch()
    } catch (e) {
      push(e instanceof Error ? e.message : 'Could not reprocess', 'error')
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div className="stack gap-20">
      <div className="row gap-12 wrap" style={{ alignItems: 'flex-end' }}>
        <div className="grow">
          <h2 className="display" style={{ fontSize: 26 }}>Learning material</h2>
          <p className="small muted" style={{ margin: '4px 0 0' }}>
            Upload PDF, DOCX or UTF-8 text. Files are validated by signature, stored outside the
            web root, and readable only through authorised endpoints.
          </p>
        </div>
        <select value={visibility} onChange={(e) => setVisibility(e.target.value)}
          aria-label="Upload visibility" style={{ width: 'auto' }}>
          <option value="private">Private to me</option>
          <option value="organisation">Organisation-wide</option>
        </select>
        <button className="btn btn-primary" onClick={() => inputRef.current?.click()} disabled={uploading}>
          {uploading ? <span className="spin" /> : <IconUpload size={14} />}
          {uploading ? 'Processing…' : 'Upload material'}
        </button>
        <input ref={inputRef} type="file" accept=".pdf,.docx,.txt" hidden
          onChange={(e) => { const f = e.target.files?.[0]; if (f) upload(f) }} />
      </div>

      {error ? <Banner kind="bad">{error}</Banner> : null}

      <Banner kind="info">
        <b>Processing is real, not simulated.</b> A document moves queued → processing → completed
        or failed. Scanned PDFs without a text layer fail with an explicit “no extractable text”
        reason rather than silently producing empty passages.
      </Banner>

      <Card title={`Your material (${docs.data?.length ?? 0})`}>
        {docs.loading ? <Skeleton h={140} /> :
        docs.error ? <ErrorState error={docs.error} onRetry={docs.refetch} /> :
        (docs.data?.length ?? 0) === 0 ? (
          <EmptyState title="No material uploaded" icon={<IconDoc size={26} />}
            action={<button className="btn btn-primary" onClick={() => inputRef.current?.click()}>
              Upload your first document
            </button>}>
            Upload a methodology note, training chapter or circular. It becomes searchable by the
            assistant and usable as a source for generated assessments.
          </EmptyState>
        ) : (
          <div className="stack gap-8">
            {docs.data!.map((d) => (
              <div key={d.id} className="doc-row">
                <div className="doc-ico">
                  {d.mime_type.includes('pdf') ? 'PDF' : d.mime_type.includes('word') ? 'DOC' : 'TXT'}
                </div>
                <div className="grow" style={{ minWidth: 0 }}>
                  <div className="row gap-8 wrap">
                    <b className="small">{d.title}</b>
                    <span className={`tag ${STATUS_TONE[d.status] ?? 'tag-neutral'}`} style={{ fontSize: 9.5 }}>
                      {d.status}
                    </span>
                    <span className="tag tag-neutral" style={{ fontSize: 9.5 }}>{d.visibility}</span>
                  </div>
                  <div className="tiny muted">
                    {formatBytes(d.size_bytes)}
                    {d.status === 'completed'
                      ? ` · ${d.page_count} page${d.page_count === 1 ? '' : 's'} · ${d.chunk_count} indexed passages`
                      : ''}
                    {d.embedding_model ? ` · ${d.embedding_model}` : d.status === 'completed' ? ' · keyword search only' : ''}
                    {' · uploaded '}{formatDateTime(d.created_at)}
                  </div>
                  {d.error_detail ? (
                    <div className="tiny" style={{ color: 'var(--critical)', marginTop: 3 }}>
                      {d.error_code}: {d.error_detail}
                    </div>
                  ) : null}
                </div>
                <div className="row gap-6">
                  {d.status === 'completed' ? (
                    <>
                      <button className="btn btn-sm btn-ghost" onClick={() => setInspect(d)}
                        title="Inspect indexed passages">Inspect</button>
                      <Link className="btn btn-sm" to={`/app/assistant?doc=${d.id}`}>
                        <IconChat size={12} /> Ask
                      </Link>
                      <Link className="btn btn-sm" to={`/app/quizzes?doc=${d.id}`}>
                        <IconQuiz size={12} /> Quiz
                      </Link>
                    </>
                  ) : null}
                  {d.status === 'failed' ? (
                    <button className="btn btn-sm" onClick={() => reprocess(d)} disabled={busyId === d.id}>
                      <IconRefresh size={12} /> Retry
                    </button>
                  ) : null}
                  <button className="btn btn-sm btn-danger" onClick={() => setDeleteTarget(d)}
                    aria-label={`Delete ${d.title}`}>
                    <IconTrash size={12} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      <Modal open={!!deleteTarget} onClose={() => setDeleteTarget(null)} title="Delete this material?">
        <p className="small">
          <b>{deleteTarget?.title}</b> and its {deleteTarget?.chunk_count ?? 0} indexed passages will
          be permanently removed, and the stored file will be deleted from disk.
        </p>
        <p className="small muted">
          Assessments already generated from this document are kept, but their link to the source is
          cleared so no citation points at deleted content.
        </p>
        <Banner kind="bad">This cannot be undone.</Banner>
        <div className="row gap-8 mt-16" style={{ justifyContent: 'flex-end' }}>
          <button className="btn" onClick={() => setDeleteTarget(null)}>Cancel</button>
          <button className="btn btn-danger" onClick={confirmDelete} disabled={busyId === deleteTarget?.id}>
            {busyId ? <span className="spin" /> : <IconTrash size={13} />} Delete permanently
          </button>
        </div>
      </Modal>

      <ChunkInspector doc={inspect} onClose={() => setInspect(null)} />
    </div>
  )
}

function ChunkInspector({ doc, onClose }: { doc: Doc | null; onClose: () => void }) {
  const chunks = useFetch<ChunkPreview[]>(
    () => doc ? api.get<ChunkPreview[]>(`/documents/${doc.id}/chunks?limit=12`) : Promise.resolve([]),
    [doc?.id],
  )
  return (
    <Modal open={!!doc} onClose={onClose} title={doc ? `Indexed passages · ${doc.title}` : ''} width={720}>
      {chunks.loading ? <Skeleton h={140} /> : (
        <div className="stack gap-8">
          <p className="tiny muted" style={{ marginTop: 0 }}>
            These are the exact passages the assistant can retrieve. Each carries a page anchor used
            in citations.
          </p>
          {(chunks.data ?? []).map((c) => (
            <div key={c.ordinal} style={{
              border: '1px solid var(--rule)', borderRadius: 'var(--r)', padding: '9px 11px',
              background: 'var(--paper-2)',
            }}>
              <div className="row gap-8 tiny muted" style={{ justifyContent: 'space-between' }}>
                <span className="mono">
                  #{c.ordinal} · p.{c.page_from}{c.page_to !== c.page_from ? `–${c.page_to}` : ''}
                  {c.section ? ` · ${c.section}` : ''}
                </span>
                <span className="mono">{c.has_embedding ? 'vector ✓' : 'no vector'}</span>
              </div>
              <p className="tiny" style={{ margin: '5px 0 0' }}>{c.preview}…</p>
            </div>
          ))}
          {(chunks.data ?? []).length === 0 ? (
            <p className="small muted">No passages indexed for this document.</p>
          ) : null}
        </div>
      )}
    </Modal>
  )
}
