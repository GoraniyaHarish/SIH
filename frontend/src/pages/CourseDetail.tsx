import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, type CourseDetail, type Doc } from '../lib/api'
import {
  Banner, Card, ErrorState, EvidenceTag, Skeleton, useFetch, useToast, formatDuration,
} from '../components/ui'
import { IconCheck, IconDoc, IconQuiz } from '../components/icons'

const KIND_LABEL: Record<string, string> = {
  reading: 'Reading',
  worked_example: 'Worked example',
  quiz: 'Knowledge check',
  video: 'Video',
  exercise: 'Exercise',
}

export default function CourseDetailPage() {
  const { courseId } = useParams()
  const navigate = useNavigate()
  const { push } = useToast()
  const [busy, setBusy] = useState(false)

  const course = useFetch<CourseDetail>(() => api.get<CourseDetail>(`/courses/${courseId}`), [courseId])
  const materials = useFetch<Doc[]>(
    () => api.get<Doc[]>(`/documents?course_id=${courseId}&limit=50`),
    [courseId],
  )

  async function enrol() {
    setBusy(true)
    try {
      await api.post(`/courses/${courseId}/enrol`)
      push('Enrolled. Progress is tracked as you mark items complete.', 'success')
      course.refetch()
    } catch (e) {
      push(e instanceof Error ? e.message : 'Could not enrol', 'error')
    } finally {
      setBusy(false)
    }
  }

  async function toggleMaterial(materialId: string, completed: boolean) {
    try {
      await api.post(`/courses/${courseId}/progress`, { material_id: materialId, completed })
      course.refetch()
    } catch (e) {
      push(e instanceof Error ? e.message : 'Could not update progress', 'error')
    }
  }

  if (course.loading) return <Skeleton h={420} />
  if (course.error) return <ErrorState error={course.error} onRetry={course.refetch} />
  if (!course.data) return null

  const c = course.data
  const enrolled = c.enrolment
  const done = new Set(enrolled?.completed_material_ids ?? [])

  return (
    <div className="stack gap-20">
      <Link to="/app/courses" className="tiny muted">← Back to catalogue</Link>

      <div className="split">
        <div className="stack gap-20">
          <Card>
            <div className="row gap-8 wrap mb-12">
              <span className="tag tag-neutral" style={{ textTransform: 'uppercase', fontSize: 9.5 }}>{c.level}</span>
              <EvidenceTag status={c.evidence_status} />
              <span className="mono tiny muted">{c.code}</span>
              <span className="grow" />
              <span className="mono tiny muted">{formatDuration(c.duration_minutes)}</span>
            </div>
            <h2 className="display" style={{ fontSize: 27, marginBottom: 8 }}>{c.title}</h2>
            <p className="small muted" style={{ marginTop: 0 }}>{c.description ?? c.summary}</p>

            <div className="row gap-12 wrap mt-12">
              <div>
                <div className="eyebrow">Provider</div>
                <div className="small">{c.provider}</div>
              </div>
              {c.provider_url ? (
                <div>
                  <div className="eyebrow">Source</div>
                  <a className="small" href={c.provider_url} target="_blank" rel="noreferrer noopener">
                    Open provider page ↗
                  </a>
                </div>
              ) : (
                <div>
                  <div className="eyebrow">Source</div>
                  <span className="small muted">No verified URL — demonstration content</span>
                </div>
              )}
            </div>

            {c.objectives.length ? (
              <>
                <div className="divider" />
                <div className="eyebrow mb-8">Learning objectives</div>
                <ul className="small" style={{ margin: 0, paddingLeft: 17 }}>
                  {c.objectives.map((o) => <li key={o} style={{ marginBottom: 4 }}>{o}</li>)}
                </ul>
              </>
            ) : null}

            {c.competency_names.length ? (
              <>
                <div className="divider" />
                <div className="eyebrow mb-8">Develops these competencies</div>
                <div className="row gap-6 wrap">
                  {c.competency_names.map((n) => (
                    <span key={n} className="tag tag-neutral">{n}</span>
                  ))}
                </div>
              </>
            ) : null}
        </Card>

          <Card title={`Materials (${c.materials.length})`}>
            <div className="stack gap-8">
              {c.materials.map((m, i) => {
                const isDone = done.has(m.id)
                return (
                  <div key={m.id} className="doc-row">
                    <span className="plan-step">{String(i + 1).padStart(2, '0')}</span>
                    <div className="grow" style={{ minWidth: 0 }}>
                      <div className="row gap-8 wrap">
                        <b className="small">{m.title}</b>
                        <span className="tag tag-neutral" style={{ fontSize: 9.5 }}>
                          {KIND_LABEL[m.kind] ?? m.kind}
                        </span>
                      </div>
                      <div className="tiny muted">
                        {formatDuration(m.duration_minutes)}
                        {m.description ? ` · ${m.description}` : ''}
                      </div>
                    </div>
                    {enrolled ? (
                      <button
                        className={`btn btn-sm ${isDone ? 'btn-primary' : ''}`}
                        onClick={() => toggleMaterial(m.id, !isDone)}
                        aria-pressed={isDone}>
                        {isDone ? <IconCheck size={13} /> : null}
                        {isDone ? 'Done' : 'Mark done'}
                      </button>
                    ) : null}
                  </div>
                )
              })}
              {c.materials.length === 0 ? (
                <p className="small muted" style={{ margin: 0 }}>No materials catalogued for this course.</p>
              ) : null}
            </div>
          </Card>

          <Card
            title="Attached learning material"
            actions={<Link className="btn btn-sm btn-ghost" to="/app/documents">Manage <IconDoc size={12} /></Link>}
          >
            {materials.loading ? <Skeleton h={50} /> : (materials.data?.length ?? 0) === 0 ? (
              <p className="small muted" style={{ margin: 0 }}>
                No documents attached. Upload study material and attach it to this course to enable
                the grounded assistant and quiz generation.
              </p>
            ) : (
              <div className="stack gap-8">
                {materials.data!.map((d) => (
                  <div key={d.id} className="doc-row">
                    <div className="doc-ico">{d.mime_type.includes('pdf') ? 'PDF' : d.mime_type.includes('word') ? 'DOC' : 'TXT'}</div>
                    <div className="grow" style={{ minWidth: 0 }}>
                      <b className="small">{d.title}</b>
                      <div className="tiny muted">
                        {d.status === 'completed'
                          ? `${d.page_count} page${d.page_count === 1 ? '' : 's'} · ${d.chunk_count} chunks indexed`
                          : d.status}
                      </div>
                    </div>
                    {d.status === 'completed' ? (
                      <Link className="btn btn-sm" to={`/app/assistant?doc=${d.id}`}>Ask about it</Link>
                    ) : null}
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>

        <div className="stack gap-20">
          <Card title="Your progress">
            {enrolled ? (
              <div className="stack gap-12">
                <div>
                  <div className="row" style={{ justifyContent: 'space-between' }}>
                    <span className="small">Progress</span>
                    <span className="mono small"><b>{enrolled.progress_percent}%</b></span>
                  </div>
                  <div style={{ height: 7, background: 'var(--paper-3)', borderRadius: 99, marginTop: 5 }}>
                    <div style={{
                      width: `${enrolled.progress_percent}%`, height: '100%', borderRadius: 99,
                      background: enrolled.progress_percent >= 100 ? 'var(--met)' : 'var(--teal)',
                      transition: 'width 260ms var(--ease)',
                    }} />
                  </div>
                </div>
                <div className="row gap-8">
                  <span className={`tag ${enrolled.status === 'completed' ? 'tag-official' : 'tag-neutral'}`}>
                    {enrolled.status}
                  </span>
                  <span className="tiny muted">
                    {done.size} of {c.materials.length} items complete
                  </span>
                </div>
                <Link className="btn btn-block" to="/app/quizzes"><IconQuiz size={14} /> Take an assessment</Link>
              </div>
            ) : (
              <div className="stack gap-10">
                <p className="small muted" style={{ margin: 0 }}>
                  Enrol to track completion and see this course in your learning plan.
                </p>
                <button className="btn btn-primary btn-block" onClick={enrol} disabled={busy}>
                  {busy ? <span className="spin" /> : null} Enrol in this course
                </button>
              </div>
            )}
          </Card>

          {c.prerequisites.length ? (
            <Card title="Prerequisites">
              <ul className="small" style={{ margin: 0, paddingLeft: 17 }}>
                {c.prerequisites.map((p) => <li key={p}>{p}</li>)}
              </ul>
            </Card>
          ) : null}

          <Card title="Provenance">
            <Banner kind="warn">
              This course record is <b>{c.evidence_status}</b>. It was created for the prototype
              catalogue and is not a real published course.
            </Banner>
            <div className="mt-12">
              <button className="btn btn-sm btn-block" onClick={() => navigate('/app/plan')}>
                Open my learning plan
              </button>
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}
