import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type GapAnalysis, type GapItem } from '../lib/api'
import {
  Card, EmptyState, ErrorState, EvidenceTag, Ladder, Skeleton,
  Stat, useFetch,
} from '../components/ui'
import { IconArrow, IconInfo, IconRoute, IconTarget } from '../components/icons'

const SEVERITY_ORDER = ['critical', 'high', 'moderate', 'low', 'none'] as const

export default function Gaps() {
  const { data, error, loading, refetch } = useFetch<GapAnalysis>(() => api.get<GapAnalysis>('/me/gaps'))
  const [filter, setFilter] = useState<'all' | 'open' | 'critical' | 'met'>('open')
  const [band, setBand] = useState<'all' | 'P1' | 'P2' | 'P3' | 'P4'>('all')
  const [expanded, setExpanded] = useState<string | null>(null)

  const items = useMemo(() => {
    if (!data) return []
    let list = data.items
    if (filter === 'open') list = list.filter((i) => i.deficit > 0)
    if (filter === 'critical') list = list.filter((i) => i.deficit > 0 && i.is_critical)
    if (filter === 'met') list = list.filter((i) => i.deficit <= 0)
    if (band !== 'all') list = list.filter((i) => i.priority_band === band)
    return list
  }, [data, filter, band])

  const domainRollup = useMemo(() => {
    if (!data) return []
    const map = new Map<string, { name: string; code: string; gap: number; total: number; deficit: number }>()
    for (const item of data.items) {
      const key = item.domain_code
      if (!map.has(key)) map.set(key, { name: item.domain_name, code: key, gap: 0, total: 0, deficit: 0 })
      const entry = map.get(key)!
      entry.total += 1
      if (item.deficit > 0) { entry.gap += 1; entry.deficit += item.deficit }
    }
    return [...map.values()].sort((a, b) => b.deficit - a.deficit)
  }, [data])

  if (loading) return <Skeleton h={420} />
  if (error) return <ErrorState error={error} onRetry={refetch} />
  if (!data) return null

  if (!data.job_role_id) {
    return (
      <Card>
        <EmptyState title="No job role assigned" icon={<IconTarget size={26} />}>
          Gap analysis compares your assessed levels against the requirements of a job role.
          Ask an administrator to assign your role in <Link to="/app/settings">settings</Link> or{' '}
          <Link to="/app/admin/users">People &amp; roles</Link>.
        </EmptyState>
      </Card>
    )
  }

  if (data.missing_assessment) {
    return (
      <Card>
        <EmptyState title="No assessment submitted yet" icon={<IconTarget size={26} />}
          action={<Link className="btn btn-primary" to="/app/assessment">Take the baseline assessment</Link>}>
          Required levels for <b>{data.job_role_title}</b> are known, but your current levels are not.
          Until an assessment exists, every required competency would appear as a maximum gap — which
          would be misleading, so no analysis is shown.
        </EmptyState>
      </Card>
    )
  }

  return (
    <div className="stack gap-20">
      <div className="row gap-12 wrap" style={{ alignItems: 'flex-end' }}>
        <div className="grow">
          <h2 className="display" style={{ fontSize: 26 }}>Skill-gap analysis</h2>
          <p className="small muted" style={{ margin: '4px 0 0' }}>
            Assessed against <b>{data.job_role_title}</b> · {data.total_required} required competencies
          </p>
        </div>
        <Link className="btn" to="/app/plan"><IconRoute size={14} /> Learning plan</Link>
        <Link className="btn btn-primary" to="/app/assessment">Re-assess</Link>
      </div>

      <div className="stats">
        <Stat label="Readiness" value={data.overall_readiness_percent.toFixed(1)} suffix="%"
          tone={data.overall_readiness_percent >= 75 ? 'good' : data.overall_readiness_percent >= 50 ? undefined : 'warn'}
          detail="weighted across required levels" />
        <Stat label="Open gaps" value={data.gap_count} tone={data.gap_count ? 'warn' : 'good'}
          detail={`${data.met_count} at or above target`} />
        <Stat label="Critical" value={data.critical_gap_count} tone={data.critical_gap_count ? 'bad' : 'good'}
          detail="flagged critical for the role" />
        <Stat label="P1 priorities" value={data.items.filter((i) => i.priority_band === 'P1').length}
          detail="act first — highest score" />
      </div>

      <div className="split">
        <Card
          title="Gap register"
          actions={
            <div className="row gap-8 wrap">
              <div className="seg" role="group" aria-label="Filter">
                {(['open', 'critical', 'met', 'all'] as const).map((f) => (
                  <button key={f} aria-pressed={filter === f} onClick={() => setFilter(f)}
                    style={{ textTransform: 'capitalize' }}>{f}</button>
                ))}
              </div>
              <select value={band} onChange={(e) => setBand(e.target.value as typeof band)}
                aria-label="Priority band" style={{ width: 'auto' }}>
                <option value="all">All bands</option>
                <option value="P1">P1 only</option>
                <option value="P2">P2 only</option>
                <option value="P3">P3 only</option>
                <option value="P4">P4 only</option>
              </select>
            </div>
          }
        >
          {items.length === 0 ? (
            <EmptyState title="Nothing matches this filter">
              Try “all” or a different priority band.
            </EmptyState>
          ) : (
            <div className="stack gap-8">
              {items.map((item) => (
                <GapRow key={item.competency_id} item={item}
                  open={expanded === item.competency_id}
                  onToggle={() => setExpanded(expanded === item.competency_id ? null : item.competency_id)} />
              ))}
            </div>
          )}
        </Card>

        <div className="stack gap-20">
          <Card title="Gap by domain">
            <div className="stack gap-12">
              {domainRollup.map((d) => {
                const pct = d.total ? (d.gap / d.total) * 100 : 0
                return (
                  <div key={d.code}>
                    <div className="row gap-8" style={{ justifyContent: 'space-between' }}>
                      <span className="small">{d.name}</span>
                      <span className="mono tiny muted">{d.gap}/{d.total}</span>
                    </div>
                    <div style={{ height: 5, background: 'var(--paper-3)', borderRadius: 99, marginTop: 4 }}>
                      <div style={{
                        width: `${pct}%`, height: '100%', borderRadius: 99,
                        background: pct > 66 ? 'var(--critical)' : pct > 33 ? 'var(--ochre)' : 'var(--teal)',
                        transition: 'width 260ms var(--ease)',
                      }} />
                    </div>
                  </div>
                )
              })}
            </div>
          </Card>

          <Card title="How this is calculated">
            <p className="tiny muted" style={{ marginTop: 0 }}>{data.method_note}</p>
            <div className="divider" />
            <pre className="mono tiny" style={{
              margin: 0, whiteSpace: 'pre-wrap', lineHeight: 1.7,
              background: 'var(--paper-2)', padding: 12, borderRadius: 'var(--r)',
              border: '1px solid var(--rule)',
            }}>{`deficit  = max(0, required − current)
priority = deficit
         × (0.6 + 0.4 × importance/5)
         × (1.35 if critical else 1.0)
         × (0.85 + 0.15 × confidence/5)

band: P1 ≥ 2.2 · P2 ≥ 1.4 · P3 ≥ 0.7 · P4 below`}</pre>
            <p className="tiny muted mt-8" style={{ marginBottom: 0 }}>
              <IconInfo size={12} /> Prerequisite gaps are deferred, so foundational competencies are
              fixed before dependent ones.
            </p>
          </Card>

          <Card title="Evidence status">
            <div className="row gap-8 wrap">
              <EvidenceTag status="provisional" />
              <span className="tiny muted">
                Role requirements are authored for this prototype. A level sourced from a self-rating
                is labelled accordingly and is not proof of proficiency.
              </span>
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}

function GapRow({ item, open, onToggle }: { item: GapItem; open: boolean; onToggle: () => void }) {
  const sevIndex = SEVERITY_ORDER.indexOf(item.severity)
  return (
    <article className="gap-item" data-blocked={item.prerequisite_blocked}
      style={{ flexDirection: 'column', gap: 10 }}>
      <div className="row gap-12" style={{ width: '100%', alignItems: 'flex-start' }}>
        <span className="gap-band" data-b={item.priority_band}>{item.priority_band}</span>
        <div className="grow" style={{ minWidth: 0 }}>
          <div className="row gap-8 wrap">
            <b className="small">{item.competency_name}</b>
            <span className="mono tiny muted">{item.competency_code}</span>
            {item.is_critical ? <span className="tag tag-critical" style={{ fontSize: 9.5 }}>critical</span> : null}
            {item.prerequisite_blocked
              ? <span className="tag tag-pending" style={{ fontSize: 9.5 }}>prerequisite first</span>
              : null}
          </div>
          <div className="row gap-10 mt-4 wrap">
            <span className="row gap-6">
              <span className="tiny muted">now</span>
              <Ladder level={item.current_level} target={item.target_level} />
              <span className="mono tiny">{item.current_level}</span>
            </span>
            <span className="tiny muted">→</span>
            <span className="row gap-4">
              <span className="tiny muted">target</span>
              <span className="mono tiny"><b>{item.target_level}</b></span>
            </span>
            <span className={`tag ${item.deficit === 0 ? 'tag-official' : 'tag-neutral'}`} style={{ fontSize: 9.5 }}>
              gap {item.deficit.toFixed(1)}
            </span>
            {item.severity !== 'none'
              ? <span className="tag tag-neutral" style={{ fontSize: 9.5 }}>{item.severity}</span>
              : null}
          </div>
        </div>
        <div className="stack gap-4" style={{ alignItems: 'flex-end' }}>
          <span className="mono tiny muted" title="Deterministic priority score">
            {item.priority_score.toFixed(2)}
          </span>
          <button className="btn btn-sm btn-ghost" onClick={onToggle}
            aria-expanded={open} aria-label="Show explanation">
            {open ? 'Hide' : 'Why?'}
          </button>
        </div>
      </div>

      {open ? (
        <div style={{
          width: '100%', padding: '10px 12px', background: 'var(--paper-2)',
          borderRadius: 'var(--r)', border: '1px solid var(--rule)',
        }}>
          <p className="small" style={{ margin: '0 0 8px' }}>{item.explanation}</p>
          <div className="row gap-16 wrap tiny muted">
            <span>Domain: <b>{item.domain_name}</b></span>
            <span>Importance: <b className="mono">{item.importance}/5</b></span>
            <span>Level source: <b>{item.current_level_source.replace(/_/g, ' ')}</b></span>
            <span className="row gap-4">
              <EvidenceTag status={item.evidence_status} compact />
            </span>
          </div>
          <div className="row gap-8 mt-8">
            <Link className="btn btn-sm" to={`/app/courses?competency=${item.competency_code}`}>
              Find material <IconArrow size={12} />
            </Link>
            <Link className="btn btn-sm btn-ghost" to="/app/plan">Add to plan</Link>
          </div>
        </div>
      ) : null}
      {sevIndex < 3 && item.deficit > 0 ? null : null}
    </article>
  )
}
