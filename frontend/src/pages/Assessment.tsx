import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  api, type Competency, type JobRole, type Level,
  type GapAnalysis,
} from '../lib/api'
import { useAuth } from '../lib/auth'
import {
  Banner, Card, ErrorState, EvidenceTag, Field, Ladder, Skeleton, useFetch, useToast,
} from '../components/ui'
import { IconCheck, IconInfo, IconTarget } from '../components/icons'

type Method = 'self' | 'structured'

export default function Assessment() {
  const { user, refreshUser } = useAuth()
  const { push } = useToast()

  const [tab, setTab] = useState<'pending' | 'history'>('pending')
  const levels = useFetch<Level[]>(() => api.get<Level[]>('/framework/levels'))
  const roles = useFetch<JobRole[]>(() => api.get<JobRole[]>('/framework/job-roles'))
  const competencies = useFetch<Competency[]>(() => api.get<Competency[]>('/framework/competencies'))
  const existing = useFetch<GapAnalysis>(() => api.get<GapAnalysis>('/me/gaps'))

  const role = roles.data?.find((r) => r.id === user?.job_role_id)
  const requiredIds = useMemo(
    () => new Set(role?.requirements.map((r) => r.competency_id) ?? []),
    [role],
  )

  const [scope, setScope] = useState<'role' | 'all'>('role')
  const [method, setMethod] = useState<Method>('self')
  const [levelsByComp, setLevels] = useState<Record<string, number>>({})
  const [confidence, setConfidence] = useState<Record<string, number>>({})
  const [notes, setNotes] = useState<Record<string, string>>({})
  const [title, setTitle] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<GapAnalysis | null>(null)

  const visible = useMemo(() => {
    const all = competencies.data ?? []
    return scope === 'role' && requiredIds.size
      ? all.filter((c) => requiredIds.has(c.id))
      : all
  }, [competencies.data, requiredIds, scope])

  const answered = visible.filter((c) => levelsByComp[c.id]).length
  const reqByComp = useMemo(
    () => new Map((role?.requirements ?? []).map((r) => [r.competency_id, r])),
    [role],
  )

  async function submit() {
    if (answered === 0) {
      setError('Rate at least one competency before submitting.')
      return
    }
    setBusy(true)
    setError(null)
    try {
      const responses = visible
        .filter((c) => levelsByComp[c.id])
        .map((c) => ({
          competency_id: c.id,
          declared_level: levelsByComp[c.id],
          confidence: confidence[c.id] ?? 3,
          evidence_note: notes[c.id]?.trim() || null,
        }))

      await api.post('/assessments', {
        method,
        title: title.trim() || `Assessment ${new Date().toLocaleDateString('en-IN')}`,
        notes: null,
        responses,
      })
      push(`Assessment submitted for ${responses.length} competencies`, 'success')
      const gaps = await api.get<GapAnalysis>('/me/gaps')
      setResult(gaps)
      existing.refetch()
      await refreshUser()
      setTab('history')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not submit the assessment')
    } finally {
      setBusy(false)
    }
  }

  const grouped = useMemo(() => {
    const map = new Map<string, { name: string; code: string; items: Competency[] }>()
    for (const c of visible) {
      const key = c.domain_id
      if (!map.has(key)) map.set(key, { name: c.domain_name ?? '—', code: c.domain_code ?? '', items: [] })
      map.get(key)!.items.push(c)
    }
    return [...map.values()]
  }, [visible])

  if (competencies.loading || levels.loading) return <Skeleton h={380} />
  if (competencies.error) return <ErrorState error={competencies.error} onRetry={competencies.refetch} />

  return (
    <div className="stack gap-20">
      <div className="row gap-12 wrap" style={{ alignItems: 'flex-end' }}>
        <div className="grow">
          <h2 className="display" style={{ fontSize: 26 }}>Competency assessment</h2>
          <p className="small muted" style={{ margin: '4px 0 0' }}>
            Rate your current level against the observable criteria for each level. Be conservative —
            an inflated rating produces a false picture of readiness.
          </p>
        </div>
        <div className="seg" role="group" aria-label="Assessment view">
          <button aria-pressed={tab === 'pending'} onClick={() => setTab('pending')}>New assessment</button>
          <button aria-pressed={tab === 'history'} onClick={() => setTab('history')}>Result</button>
        </div>
      </div>

      {!user?.job_role_id ? (
        <Banner kind="warn">
          <b>No job role assigned.</b> You can still record levels, but gap analysis needs a role to
          compare against. Ask an administrator to set your role in{' '}
          <Link to="/app/admin/users">People &amp; roles</Link>.
        </Banner>
      ) : null}

      {tab === 'history' ? (
        result ? <ResultView gaps={result} /> : (
          <Card>
            {existing.data && existing.data.total_required > 0 ? (
              <ResultView gaps={existing.data} />
            ) : (
              <p className="small muted" style={{ margin: 0 }}>
                No result to show yet. Submit an assessment, or open{' '}
                <Link to="/app/gaps">skill-gap analysis</Link> to see the current comparison.
              </p>
            )}
          </Card>
        )
      ) : (
        <>
          <Card title="Assessment settings">
            <div className="grid-3">
              <Field label="Scope"
                hint={requiredIds.size
                  ? `Your role requires ${requiredIds.size} competencies. Rating all 32 gives a broader profile.`
                  : 'No role assigned, so all competencies are shown.'}>
                <select value={scope} onChange={(e) => setScope(e.target.value as 'role' | 'all')}>
                  <option value="role" disabled={!requiredIds.size}>Required for my role only</option>
                  <option value="all">All competencies in the framework</option>
                </select>
              </Field>
              <Field label="Method"
                hint={method === 'self'
                  ? 'Self-declared. Treated as unverified until an assessor reviews it.'
                  : 'Structured: recorded as a guided assessment, still subject to review.'}>
                <select value={method} onChange={(e) => setMethod(e.target.value as Method)}>
                  <option value="self">Self-assessment</option>
                  <option value="structured">Structured (guided)</option>
                </select>
              </Field>
              <Field label="Title" hint="Optional label for this assessment.">
                <input type="text" value={title} onChange={(e) => setTitle(e.target.value)}
                  placeholder={`Assessment ${new Date().toLocaleDateString('en-IN')}`} />
              </Field>
            </div>

            <div className="row gap-12 mt-8 wrap" style={{
              padding: '10px 12px', background: 'var(--paper-2)', borderRadius: 'var(--r)',
              border: '1px solid var(--rule)',
            }}>
              <span className="tiny">
                <b>{answered}</b> of <b>{visible.length}</b> rated
              </span>
              <div style={{ flex: 1, height: 4, background: 'var(--paper-3)', borderRadius: 99, minWidth: 100 }}>
                <div style={{
                  width: `${visible.length ? (answered / visible.length) * 100 : 0}%`,
                  height: '100%', background: 'var(--teal)', borderRadius: 99,
                  transition: 'width 220ms var(--ease)',
                }} />
              </div>
              <button className="btn btn-ghost btn-sm" onClick={() => { setLevels({}); setConfidence({}); setNotes({}) }}>
                Clear ratings
              </button>
            </div>
          </Card>

          {error ? <Banner kind="bad">{error}</Banner> : null}

          <div className="stack gap-20">
            {grouped.map((group) => (
              <Card key={group.name} title={<>{group.code} · {group.name}</>}>
                <div className="stack gap-16">
                  {group.items.map((c) => {
                    const req = reqByComp.get(c.id)
                    const chosen = levelsByComp[c.id]
                    return (
                      <div key={c.id} style={{ borderTop: '1px solid var(--rule)', paddingTop: 12 }}>
                        <div className="row gap-8 wrap mb-8">
                          <span className="mono tiny muted">{c.code}</span>
                          <b className="small">{c.name}</b>
                          {req ? (
                            <span className="tag tag-neutral" style={{ fontSize: 9.5 }}>
                              role requires {req.required_level}
                            </span>
                          ) : null}
                          {req?.is_critical ? <span className="tag tag-critical" style={{ fontSize: 9.5 }}>critical</span> : null}
                        </div>
                        {c.description ? (
                          <p className="tiny muted" style={{ margin: '0 0 8px' }}>{c.description}</p>
                        ) : null}

                        <div className="row gap-6 wrap mb-8" role="group" aria-label={`Level for ${c.name}`}>
                          {[1, 2, 3, 4, 5].map((lv) => {
                            const meta = levels.data?.find((l) => l.level === lv)
                            return (
                              <button key={lv} type="button"
                                className={`btn btn-sm ${chosen === lv ? 'btn-primary' : ''}`}
                                aria-pressed={chosen === lv}
                                title={meta ? `${meta.label} — ${meta.summary}` : undefined}
                                onClick={() => setLevels((p) => ({ ...p, [c.id]: lv }))}>
                                {lv} · {meta?.label ?? ''}
                              </button>
                            )
                          })}
                          <button type="button" className="btn btn-sm btn-ghost"
                            aria-pressed={!chosen}
                            onClick={() => setLevels((p) => {
                              const next = { ...p }; delete next[c.id]; return next
                            })}>
                            Clear
                          </button>
                        </div>

                        {chosen ? (
                          <div className="row gap-12 wrap" style={{ alignItems: 'flex-start' }}>
                            <div style={{ flex: '0 1 220px' }}>
                              <label className="tiny muted" htmlFor={`conf-${c.id}`}>
                                Confidence in this rating
                              </label>
                              <select id={`conf-${c.id}`} value={confidence[c.id] ?? 3}
                                onChange={(e) => setConfidence((p) => ({ ...p, [c.id]: Number(e.target.value) }))}>
                                <option value={1}>1 — very unsure</option>
                                <option value={2}>2 — unsure</option>
                                <option value={3}>3 — reasonably sure</option>
                                <option value={4}>4 — confident</option>
                                <option value={5}>5 — certain</option>
                              </select>
                            </div>
                            <div style={{ flex: '2 1 260px' }}>
                              <label className="tiny muted" htmlFor={`note-${c.id}`}>
                                Evidence note (optional)
                              </label>
                              <input id={`note-${c.id}`} type="text"
                                value={notes[c.id] ?? ''}
                                placeholder="e.g. Designed the sample for the 2024 urban survey round"
                                onChange={(e) => setNotes((p) => ({ ...p, [c.id]: e.target.value }))} />
                            </div>
                          </div>
                        ) : null}
                      </div>
                    )
                  })}
                </div>
              </Card>
            ))}
          </div>

          <div className="card card-pad row gap-12 wrap" style={{ position: 'sticky', bottom: 12, boxShadow: '0 6px 24px rgba(26,33,48,0.1)' }}>
            <div className="grow">
              <b className="small">{answered} rated</b>
              <p className="tiny muted" style={{ margin: 0 }}>
                Submitting recalculates your gaps and learning plan immediately.
              </p>
            </div>
            <button className="btn btn-primary btn-lg" onClick={submit} disabled={busy || answered === 0}>
              {busy ? <span className="spin" /> : <IconCheck size={15} />}
              Submit assessment
            </button>
          </div>
        </>
      )}
    </div>
  )
}

function ResultView({ gaps }: { gaps: GapAnalysis }) {
  return (
    <div className="stack gap-16">
      <div className="stats">
        <div className="stat">
          <div className="k">Readiness</div>
          <div className="v">{gaps.overall_readiness_percent.toFixed(1)}<small>%</small></div>
          <div className="d">of required proficiency achieved</div>
        </div>
        <div className="stat" data-tone={gaps.gap_count ? 'warn' : 'good'}>
          <div className="k">Open gaps</div>
          <div className="v">{gaps.gap_count}</div>
          <div className="d">of {gaps.total_required} required</div>
        </div>
        <div className="stat" data-tone={gaps.critical_gap_count ? 'bad' : 'good'}>
          <div className="k">Critical gaps</div>
          <div className="v">{gaps.critical_gap_count}</div>
          <div className="d">flagged critical for the role</div>
        </div>
        <div className="stat">
          <div className="k">At target</div>
          <div className="v">{gaps.met_count}</div>
          <div className="d">competencies meeting the requirement</div>
        </div>
      </div>

      {gaps.items.length === 0 ? (
        <Banner kind="good">
          <IconTarget size={14} /> Every required competency for{' '}
          <b>{gaps.job_role_title}</b> now meets its target level.
        </Banner>
      ) : (
        <>
          <table className="ledger">
            <thead>
              <tr>
                <th>Band</th><th>Competency</th><th>Current</th>
                <th className="num">Target</th><th className="num">Gap</th><th>Severity</th>
              </tr>
            </thead>
            <tbody>
              {gaps.items.slice(0, 14).map((item) => (
                <tr key={item.competency_id}>
                  <td><span className="gap-band" data-b={item.priority_band}>{item.priority_band}</span></td>
                  <td>
                    <span className="mono tiny muted">{item.competency_code}</span>{' '}
                    <b className="small">{item.competency_name}</b>
                  </td>
                  <td><Ladder level={item.current_level} /></td>
                  <td className="num mono">{item.target_level}</td>
                  <td className="num mono" style={{ color: 'var(--critical)' }}>{item.deficit.toFixed(1)}</td>
                  <td><span className="tag tag-neutral" style={{ fontSize: 9.5 }}>{item.severity}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="row gap-8 wrap">
            <Link className="btn btn-primary" to="/app/gaps">Open full gap analysis</Link>
            <Link className="btn" to="/app/plan">See updated learning plan</Link>
          </div>
        </>
      )}

      <p className="tiny muted" style={{ margin: 0 }}>
        <IconInfo size={12} /> {gaps.method_note}
      </p>
      <div className="row gap-8">
        <span className="tiny muted">Framework:</span>
        <EvidenceTag status="provisional" compact />
      </div>
    </div>
  )
}
