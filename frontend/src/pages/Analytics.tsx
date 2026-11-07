import { useState } from 'react'
import { api, type ManagerAnalytics } from '../lib/api'
import { useAuth } from '../lib/auth'
import {
  Banner, Card, EmptyState, ErrorState, Skeleton, Stat, useFetch, useToast, formatDateTime,
} from '../components/ui'
import { IconChart, IconDownload, IconInfo } from '../components/icons'

export default function Analytics() {
  const { user } = useAuth()
  const { push } = useToast()
  const { data, error, loading, refetch } = useFetch<ManagerAnalytics>(
    () => api.get<ManagerAnalytics>('/manager/analytics'),
  )
  const [exporting, setExporting] = useState(false)

  async function exportCsv() {
    setExporting(true)
    try {
      const res = await api.get<{ filename: string; csv: string }>('/manager/analytics/export')
      const blob = new Blob([res.csv], { type: 'text/csv;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = res.filename
      document.body.appendChild(link)
      link.click()
      link.remove()
      URL.revokeObjectURL(url)
      push(`Exported ${res.filename}`, 'success')
    } catch (e) {
      push(e instanceof Error ? e.message : 'Export failed', 'error')
    } finally {
      setExporting(false)
    }
  }

  if (loading) return <Skeleton h={420} />
  if (error) return <ErrorState error={error} onRetry={refetch} />
  if (!data) return null

  const empty = data.headcount_considered === 0

  return (
    <div className="stack gap-20">
      <div className="row gap-12 wrap" style={{ alignItems: 'flex-end' }}>
        <div className="grow">
          <h2 className="display" style={{ fontSize: 26 }}>Training intelligence</h2>
          <p className="small muted" style={{ margin: '4px 0 0' }}>
            Aggregate competency position for your scope · as of {formatDateTime(data.as_of)}
          </p>
        </div>
        <button className="btn" onClick={exportCsv} disabled={exporting}>
          <IconDownload size={14} /> {exporting ? 'Exporting…' : 'Export CSV'}
        </button>
      </div>

      <Banner kind="info">
        <b>Scope: {data.scope}.</b>{' '}
        {user?.role === 'manager'
          ? 'As a training manager you see only your own department. Individual learner records are never exposed here.'
          : 'As an administrator you see the whole organisation; filter scope from the admin workspace.'}
      </Banner>

      {data.suppression_applied ? (
        <Banner kind="warn">
          <b>Small-group suppression is active.</b> Any figure derived from fewer than{' '}
          {data.suppression_threshold} learners is hidden, so an individual's competency position
          cannot be inferred from an aggregate.
        </Banner>
      ) : null}

      {empty ? (
        <Card>
          <EmptyState title="No learners in scope" icon={<IconChart size={26} />}>
            Analytics are computed from persisted assessment and enrolment records. Once learners in
            your scope have been assessed, this view populates.
          </EmptyState>
        </Card>
      ) : (
        <>
          <div className="stats">
            <Stat label="Learners in scope" value={data.headcount_considered}
              detail={`${data.assessed_learners} have submitted an assessment`} />
            <Stat label="Average readiness"
              value={data.average_readiness_percent === null ? '—' : data.average_readiness_percent.toFixed(1)}
              suffix={data.average_readiness_percent === null ? undefined : '%'}
              tone={data.average_readiness_percent === null ? undefined : data.average_readiness_percent >= 70 ? 'good' : 'warn'}
              detail={data.average_readiness_percent === null
                ? `hidden — under ${data.suppression_threshold} assessed learners`
                : 'mean of assessed learners'} />
            <Stat label="Learners with critical gaps"
              value={data.critical_gap_learners === null ? '—' : data.critical_gap_learners}
              tone={data.critical_gap_learners ? 'bad' : undefined}
              detail="at least one critical competency below target" />
            <Stat label="Domain gaps" value={data.domain_gaps.length}
              detail="domains with an open deficit" />
          </div>

          <Card title="Competency gaps by domain">
            {data.domain_gaps.length === 0 ? (
              <p className="small muted" style={{ margin: 0 }}>No domain-level deficits recorded in scope.</p>
            ) : (
              <table className="ledger">
                <thead>
                  <tr><th>Domain</th><th className="num">Competencies</th>
                    <th className="num">Avg deficit</th><th className="num">Learners affected</th></tr>
                </thead>
                <tbody>
                  {data.domain_gaps.map((d) => (
                    <tr key={d.domain_code}>
                      <td>
                        <span className="mono tiny muted">{d.domain_code}</span>{' '}
                        <b className="small">{d.domain_name}</b>
                      </td>
                      <td className="num">{d.competency_count}</td>
                      <td className="num">
                        {d.average_deficit === null
                          ? <span className="tiny muted" title="Suppressed">hidden</span>
                          : d.average_deficit.toFixed(2)}
                      </td>
                      <td className="num">
                        {d.learners_with_gap === null
                          ? <span className="tiny muted" title="Suppressed">hidden</span>
                          : d.learners_with_gap}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            <p className="tiny muted mt-8" style={{ marginBottom: 0 }}>
              <IconInfo size={12} /> Sorted by largest average deficit. Use this to target the next
              capacity-building intervention.
            </p>
          </Card>

          <div className="grid-2">
            <Card title="Course completion">
              {data.course_completion.length === 0 ? (
                <p className="small muted" style={{ margin: 0 }}>No enrolments in scope yet.</p>
              ) : (
                <table className="ledger">
                  <thead><tr><th>Course</th><th className="num">Enrolled</th><th className="num">Done</th><th className="num">Avg %</th></tr></thead>
                  <tbody>
                    {data.course_completion.map((c) => (
                      <tr key={c.course}>
                        <td className="small">{c.course}</td>
                        <td className="num">{c.enrolled}</td>
                        <td className="num">{c.completed}</td>
                        <td className="num">{c.average_progress === null ? '—' : `${c.average_progress}%`}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </Card>

            <Card title="Assessment outcomes">
              {data.assessment_outcomes.length === 0 ? (
                <p className="small muted" style={{ margin: 0 }}>No assessments submitted in scope.</p>
              ) : (
                <table className="ledger">
                  <thead><tr><th>Method</th><th className="num">Count</th></tr></thead>
                  <tbody>
                    {data.assessment_outcomes.map((a) => (
                      <tr key={a.method}>
                        <td className="small" style={{ textTransform: 'capitalize' }}>
                          {a.method.replace(/_/g, ' ')}
                        </td>
                        <td className="num">{a.suppressed ? <span className="tiny muted">hidden</span> : a.count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </Card>
          </div>

          <Card title="Quiz performance">
            {data.quiz_performance.length === 0 ? (
              <p className="small muted" style={{ margin: 0 }}>No quiz attempts in scope.</p>
            ) : (
              <table className="ledger">
                <thead><tr><th>Assessment</th><th className="num">Attempts</th><th className="num">Average</th></tr></thead>
                <tbody>
                  {data.quiz_performance.map((q) => (
                    <tr key={q.quiz}>
                      <td className="small">{q.quiz}</td>
                      <td className="num">{q.attempts}</td>
                      <td className="num">
                        {q.average_score === null ? <span className="tiny muted">hidden</span> : `${q.average_score}%`}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>
        </>
      )}
    </div>
  )
}
