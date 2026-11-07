import { Link } from 'react-router-dom'
import { api, type Dashboard as Dash } from '../lib/api'
import { useAuth } from '../lib/auth'
import {
  Banner, Card, EmptyState, ErrorState, EvidenceTag, Ladder, Skeleton, Stat, useFetch,
  formatDuration,
} from '../components/ui'
import {
  IconAlert, IconArrow, IconBook, IconQuiz, IconRoute, IconTarget,
} from '../components/icons'

export default function Dashboard() {
  const { user } = useAuth()
  const { data, error, loading, refetch } = useFetch<Dash>(() => api.get<Dash>('/me/dashboard'))

  if (loading) return <DashSkeleton />
  if (error) return <ErrorState error={error} onRetry={refetch} />
  if (!data) return null

  const noRole = data.total_required === 0 && data.missing_assessment

  return (
    <div className="stack gap-20">
      <section className="row gap-16 wrap" style={{ alignItems: 'flex-end' }}>
        <div className="grow">
          <h2 className="display" style={{ fontSize: 27 }}>
            {greeting()}, {user?.full_name.split(' ')[0]}
          </h2>
          <p className="small muted" style={{ margin: '4px 0 0' }}>
            {user?.job_role_title
              ? <>Assessed against <b>{user.job_role_title}</b> · {data.total_required} required competencies</>
              : 'No job role assigned yet — gap analysis needs one.'}
          </p>
        </div>
        <Link className="btn btn-primary" to="/app/assessment">
          <IconTarget size={15} /> Take assessment
        </Link>
      </section>

      {data.missing_assessment ? (
        <Banner kind="warn">
          <b>No assessment on record.</b> Gaps cannot be computed until you submit a baseline
          assessment. Your first assessment takes about 10 minutes and can be reviewed later by an
          assessor, which raises its evidentiary weight.{' '}
          <Link to="/app/assessment">Start the baseline assessment →</Link>
        </Banner>
      ) : null}

      {noRole && !data.missing_assessment ? (
        <Banner kind="info">
          <b>No job role assigned.</b> Ask an administrator to set your job role so required
          proficiency levels can be applied. <Link to="/app/settings">Open settings →</Link>
        </Banner>
      ) : null}

      <div className="stats">
        <Stat label="Role readiness" value={data.readiness_percent.toFixed(1)} suffix="%"
          tone={data.readiness_percent >= 75 ? 'good' : data.readiness_percent >= 50 ? undefined : 'warn'}
          detail={`${data.assessed_competencies} of ${data.total_required} competencies at target`} />
        <Stat label="Open gaps" value={data.gap_count}
          tone={data.gap_count === 0 ? 'good' : 'warn'}
          detail={`${data.critical_gap_count} marked critical for the role`} />
        <Stat label="Plan progress" value={`${data.plan_completed}/${data.plan_items}`}
          detail={data.plan_minutes_remaining > 0
            ? `${formatDuration(data.plan_minutes_remaining)} remaining`
            : 'Nothing outstanding'} />
        <Stat label="Assessment average" value={data.quiz_average === null ? '—' : data.quiz_average.toFixed(0)}
          suffix={data.quiz_average === null ? undefined : '%'}
          detail={`${data.quiz_attempts} submitted attempt${data.quiz_attempts === 1 ? '' : 's'}`} />
      </div>

      <div className="split">
        <div className="stack gap-20">
          <Card
            title="Highest-priority gaps"
            actions={<Link className="btn btn-sm btn-ghost" to="/app/gaps">Full analysis <IconArrow size={13} /></Link>}
          >
            {data.top_gaps.length === 0 ? (
              <EmptyState title="No open gaps"
                icon={<IconTarget size={26} />}>
                {data.missing_assessment
                  ? 'Submit an assessment to compute your gaps.'
                  : 'You meet the required level for every competency in your role. Re-assess periodically to keep this current.'}
              </EmptyState>
            ) : (
              <div className="stack gap-8">
                {data.top_gaps.map((g) => (
                  <div key={g.competency_code} className="gap-item">
                    <span className="gap-band" data-b={g.priority_band}>{g.priority_band}</span>
                    <div className="grow" style={{ minWidth: 0 }}>
                      <div className="row gap-8 wrap">
                        <b className="small">{g.competency_name}</b>
                        <span className="mono tiny muted">{g.competency_code}</span>
                      </div>
                      <div className="row gap-8 mt-4">
                        <Ladder level={g.current_level} target={g.target_level} />
                        <span className="tiny muted mono">
                          {g.current_level.toFixed(1)} → {g.target_level}
                        </span>
                      </div>
                    </div>
                    <Link className="btn btn-sm" to={`/app/courses?competency=${g.competency_code}`}>
                      Learn
                    </Link>
                  </div>
                ))}
              </div>
            )}
          </Card>

          <Card title="Recommended next">
            {data.recommendations.length === 0 ? (
              <EmptyState title="Nothing to recommend yet" icon={<IconRoute size={26} />}>
                Recommendations appear once an assessment produces competency gaps.
              </EmptyState>
            ) : (
              <div className="stack gap-12">
                {data.recommendations.map((r, i) => (
                  <article key={`${r.kind}-${r.ref_id ?? i}`} className="stack gap-4"
                    style={{ paddingBottom: 12, borderBottom: i === data.recommendations.length - 1 ? 'none' : '1px solid var(--rule)' }}>
                    <div className="row gap-8 wrap">
                      <span className="tag tag-neutral" style={{ textTransform: 'uppercase', fontSize: 9.5 }}>
                        {r.kind === 'course' ? <IconBook size={11} /> : r.kind === 'quiz' ? <IconQuiz size={11} /> : <IconTarget size={11} />}
                        {r.kind}
                      </span>
                      {r.evidence_status ? <EvidenceTag status={r.evidence_status} compact /> : null}
                      <span className="grow" />
                      {r.duration_minutes ? <span className="mono tiny muted">{formatDuration(r.duration_minutes)}</span> : null}
                    </div>
                    <b className="small">{r.title}</b>
                    {r.subtitle ? <span className="tiny muted">{r.subtitle}</span> : null}
                    <ul style={{ margin: '4px 0 0', paddingLeft: 16, listStyle: 'none' }}>
                      {r.reasons.slice(0, 2).map((reason, idx) => (
                        <li key={idx} className="tiny muted" style={{ position: 'relative', paddingLeft: 10 }}>
                          <span style={{ position: 'absolute', left: 0, color: 'var(--ochre)' }}>–</span>
                          {reason}
                        </li>
                      ))}
                    </ul>
                    <div className="row gap-8 mt-4">
                      {r.kind === 'course' && r.ref_id
                        ? <Link className="btn btn-sm" to={`/app/courses/${r.ref_id}`}>Open course</Link>
                        : r.kind === 'quiz' && r.ref_id
                          ? <Link className="btn btn-sm" to={`/app/quizzes/${r.ref_id}`}>Start quiz</Link>
                          : r.kind === 'assessment'
                            ? <Link className="btn btn-sm btn-primary" to="/app/assessment">Assess now</Link>
                            : null}
                      <span className="mono tiny muted" title="Deterministic priority score">
                        score {r.score.toFixed(2)}
                      </span>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </Card>
        </div>

        <div className="stack gap-20">
          <Card title="Learning snapshot">
            <table className="ledger">
              <tbody>
                <tr><td>Active courses</td><td className="num">{data.active_courses}</td></tr>
                <tr><td>Completed courses</td><td className="num">{data.completed_courses}</td></tr>
                <tr><td>Quiz attempts</td><td className="num">{data.quiz_attempts}</td></tr>
                <tr><td>Critical gaps</td><td className="num" style={{ color: data.critical_gap_count ? 'var(--critical)' : undefined }}>
                  {data.critical_gap_count}
                </td></tr>
              </tbody>
            </table>
            <div className="mt-12">
              <Link className="btn btn-sm btn-block" to="/app/plan">Open learning plan</Link>
            </div>
          </Card>

          <Card title="Assessment history">
            {data.assessment_history.length === 0 ? (
              <p className="small muted" style={{ margin: 0 }}>No assessments submitted yet.</p>
            ) : (
              <table className="ledger">
                <thead><tr><th>Date</th><th>Method</th><th>Status</th></tr></thead>
                <tbody>
                  {data.assessment_history.slice(0, 6).map((h, i) => (
                    <tr key={i}>
                      <td className="mono tiny">{h.date}</td>
                      <td className="tiny" style={{ textTransform: 'capitalize' }}>{h.method.replace(/_/g, ' ')}</td>
                      <td><span className="tag tag-neutral" style={{ fontSize: 9.5 }}>{h.status}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>

          <Card title="A note on evidence">
            <div className="row gap-8" style={{ alignItems: 'flex-start' }}>
              <span style={{ color: 'var(--ochre)', paddingTop: 1 }}><IconAlert size={15} /></span>
              <p className="tiny muted" style={{ margin: 0 }}>
                A self-rating is <b>not</b> proof of proficiency. Levels carry their assessment
                method — self, structured or assessor-reviewed — and a confidence value. Quiz
                evidence adjusts a level by at most ±0.5.
              </p>
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}

function greeting(): string {
  const h = new Date().getHours()
  if (h < 12) return 'Good morning'
  if (h < 17) return 'Good afternoon'
  return 'Good evening'
}

function DashSkeleton() {
  return (
    <div className="stack gap-20">
      <Skeleton h={34} w="34%" />
      <div className="stats">
        {[0, 1, 2, 3].map((i) => <div className="stat" key={i}><Skeleton h={10} w="52%" /><Skeleton h={26} w="38%" mb={0} /></div>)}
      </div>
      <div className="split">
        <div className="stack gap-20">
          <div className="card card-pad"><Skeleton h={18} w="40%" /><Skeleton h={54} /><Skeleton h={54} /><Skeleton h={54} /></div>
          <div className="card card-pad"><Skeleton h={18} w="32%" /><Skeleton h={70} /><Skeleton h={70} /></div>
        </div>
        <div className="card card-pad"><Skeleton h={18} w="50%" /><Skeleton h={120} /></div>
      </div>
    </div>
  )
}
