import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type Plan } from '../lib/api'
import {
  Banner, Card, EmptyState, ErrorState, Skeleton, useFetch, useToast, formatDuration,
  formatDate,
} from '../components/ui'
import { IconBook, IconCheck, IconQuiz, IconRefresh, IconRoute, IconTarget } from '../components/icons'

const STATUS_ORDER = ['in_progress', 'pending', 'skipped', 'completed'] as const

export default function PlanPage() {
  const { push } = useToast()
  const { data, error, loading, refetch } = useFetch<Plan>(() => api.get<Plan>('/me/plan'))
  const [busy, setBusy] = useState<string | null>(null)
  const [regen, setRegen] = useState(false)

  async function setStatus(itemId: string, status: string) {
    setBusy(itemId)
    try {
      const updated = await api.patch<Plan>(`/me/plan/items/${itemId}`, { status })
      refetch()
      if (status === 'completed') push('Marked complete', 'success')
      if (updated.completed_items === updated.items.length && updated.items.length > 0) {
        push('Every activity in this plan is complete. Re-assess to confirm the gaps are closed.', 'success')
      }
    } catch (e) {
      push(e instanceof Error ? e.message : 'Could not update', 'error')
    } finally {
      setBusy(null)
    }
  }

  async function regenerate() {
    setRegen(true)
    try {
      await api.get<Plan>('/me/plan?regenerate=true')
      refetch()
      push('Plan rebuilt from your current gaps', 'success')
    } catch (e) {
      push(e instanceof Error ? e.message : 'Could not regenerate', 'error')
    } finally {
      setRegen(false)
    }
  }

  if (loading) return <Skeleton h={420} />
  if (error) return <ErrorState error={error} onRetry={refetch} />
  if (!data) return null

  const groups = new Map<string, typeof data.items>()
  for (const item of data.items) {
    const key = item.competency_code ?? 'Other'
    if (!groups.has(key)) groups.set(key, [])
    groups.get(key)!.push(item)
  }

  const pct = data.items.length ? Math.round((data.completed_items / data.items.length) * 100) : 0

  return (
    <div className="stack gap-20">
      <div className="row gap-12 wrap" style={{ alignItems: 'flex-end' }}>
        <div className="grow">
          <h2 className="display" style={{ fontSize: 26 }}>{data.title}</h2>
          <p className="small muted" style={{ margin: '4px 0 0' }}>
            Version {data.version} · generated {formatDate(data.generated_at)} ·{' '}
            {formatDuration(Math.round(data.total_minutes / Math.max(data.items.length, 1) * data.items.length))} of study
          </p>
        </div>
        <button className="btn" onClick={regenerate} disabled={regen}>
          <IconRefresh size={14} /> {regen ? 'Rebuilding…' : 'Rebuild from gaps'}
        </button>
        <Link className="btn btn-primary" to="/app/gaps"><IconTarget size={14} /> Review gaps</Link>
      </div>

      {data.rationale ? <Banner kind="info">{data.rationale}</Banner> : null}

      <div className="stats">
        <div className="stat">
          <div className="k">Activities</div>
          <div className="v">{data.completed_items}<small> / {data.items.length}</small></div>
          <div className="d">{pct}% complete</div>
        </div>
        <div className="stat">
          <div className="k">Remaining study</div>
          <div className="v">
            {formatDuration(data.items.filter((i) => i.status !== 'completed').reduce((s, i) => s + i.estimated_minutes, 0))}
          </div>
          <div className="d">across open activities</div>
        </div>
        <div className="stat">
          <div className="k">Competencies targeted</div>
          <div className="v">{groups.size}</div>
          <div className="d">one block per gap</div>
        </div>
      </div>

      {data.items.length === 0 ? (
        <Card>
          <EmptyState title="Your plan has no activities" icon={<IconRoute size={26} />}
            action={<Link className="btn btn-primary" to="/app/gaps">Check your gaps</Link>}>
            A plan is generated from open competency gaps. If you have no gaps, or no assessment yet,
            there is nothing to schedule.
          </EmptyState>
        </Card>
      ) : (
        <div className="stack gap-20">
          {[...groups.entries()].map(([code, items]) => {
            const sorted = [...items].sort((a, b) => {
              const si = STATUS_ORDER.indexOf(a.status as typeof STATUS_ORDER[number])
              const sj = STATUS_ORDER.indexOf(b.status as typeof STATUS_ORDER[number])
              return si - sj || a.sort_order - b.sort_order
            })
            const lead = sorted[0]
            return (
              <Card key={code} title={<>{code} · {lead.competency_name}</>}
                actions={
                  <span className="tiny muted mono">
                    target level {lead.target_level}
                  </span>
                }>
                <div className="stack gap-8">
                  {sorted.map((item, idx) => (
                    <div key={item.id} className="plan-item" data-status={item.status}>
                      <span className="plan-step">{String(idx + 1).padStart(2, '0')}</span>
                      <div className="grow" style={{ minWidth: 0 }}>
                        <div className="row gap-8 wrap">
                          <span className="t" style={{ fontWeight: 600, fontSize: 13.5 }}>{item.title}</span>
                          <span className="tag tag-neutral" style={{ fontSize: 9.5 }}>
                            {item.activity_type.replace(/_/g, ' ')}
                          </span>
                          {item.status === 'completed'
                            ? <span className="tag tag-official" style={{ fontSize: 9.5 }}>done</span>
                            : item.status === 'in_progress'
                              ? <span className="tag tag-provisional" style={{ fontSize: 9.5 }}>in progress</span>
                              : null}
                        </div>
                        {item.detail ? <p className="tiny muted" style={{ margin: '3px 0 0' }}>{item.detail}</p> : null}
                        <div className="row gap-12 tiny muted mt-4">
                          <span><IconRoute size={11} /> {formatDuration(item.estimated_minutes)}</span>
                          <span className="mono">priority {item.priority.toFixed(2)}</span>
                        </div>
                      </div>
                      <div className="row gap-6">
                        {item.course_id ? (
                          <Link className="btn btn-sm" to={`/app/courses/${item.course_id}`}>
                            <IconBook size={12} /> Course
                          </Link>
                        ) : null}
                        {item.activity_type === 'reassess' ? (
                          <Link className="btn btn-sm" to="/app/assessment"><IconQuiz size={12} /> Assess</Link>
                        ) : null}
                        {item.status !== 'completed' ? (
                          <button className="btn btn-sm" disabled={busy === item.id}
                            onClick={() => setStatus(item.id, item.status === 'in_progress' ? 'completed' : 'in_progress')}>
                            {busy === item.id ? <span className="spin" />
                              : item.status === 'in_progress' ? <IconCheck size={12} /> : null}
                            {item.status === 'in_progress' ? 'Complete' : 'Start'}
                          </button>
                        ) : (
                          <button className="btn btn-sm btn-ghost" disabled={busy === item.id}
                            onClick={() => setStatus(item.id, 'pending')}>
                            Reopen
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}
