import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type Competency, type Domain, type Framework, type Level } from '../lib/api'
import {
  Banner, Card, EmptyState, ErrorState, EvidenceTag, Ladder, Skeleton, Tabs, useFetch,
  formatDate,
} from '../components/ui'
import { IconInfo, IconLock, IconTarget } from '../components/icons'

interface StateRow {
  competency_id: string
  competency_code: string
  competency_name: string
  domain_code: string
  domain_name: string
  level: number
  method: string
  confidence: number
  assessed_at: string
  quiz_evidence: number | null
  is_verified: boolean
}

const METHOD_LABEL: Record<string, string> = {
  self: 'Self-declared',
  structured: 'Structured',
  assessor_reviewed: 'Assessor-verified',
  quiz_only: 'Quiz evidence only',
  'self+quiz': 'Self + quiz evidence',
}

export default function Profile() {
  const [tab, setTab] = useState<'profile' | 'framework' | 'levels'>('profile')
  const profile = useFetch<StateRow[]>(() => api.get<StateRow[]>('/me/competency-profile'))
  const framework = useFetch<Framework>(() => api.get<Framework>('/framework'))
  const domains = useFetch<Domain[]>(() => api.get<Domain[]>('/framework/domains'))
  const competencies = useFetch<Competency[]>(() => api.get<Competency[]>('/framework/competencies'))
  const levels = useFetch<Level[]>(() => api.get<Level[]>('/framework/levels'))

  return (
    <div className="stack gap-20">
      <div className="row gap-12 wrap" style={{ alignItems: 'flex-end' }}>
        <div className="grow">
          <h2 className="display" style={{ fontSize: 26 }}>Competency profile</h2>
          <p className="small muted" style={{ margin: '4px 0 0' }}>
            {framework.data
              ? <>Framework <b>{framework.data.label}</b> · {profile.data?.length ?? 0} competencies assessed</>
              : 'Loading framework…'}
          </p>
        </div>
        <Link className="btn" to="/app/gaps"><IconTarget size={14} /> Compare to role</Link>
        <Link className="btn btn-primary" to="/app/assessment">Update assessment</Link>
      </div>

      {framework.data ? (
        <Banner kind={framework.data.evidence_status === 'official' ? 'good' : 'warn'}>
          {framework.data.evidence_status === 'official'
            ? <>This framework is marked <b>official</b>. {framework.data.notes}</>
            : <>
                <b>This competency framework is provisional.</b> {framework.data.notes}{' '}
                Required levels per role are an authored design artefact, not a gazetted MoSPI
                standard. Treat role-readiness as diagnostic, not authoritative.
              </>}
        </Banner>
      ) : null}

      <Tabs
        value={tab}
        onChange={setTab}
        tabs={[
          { id: 'profile', label: 'My assessed levels', count: profile.data?.length },
          { id: 'levels', label: 'Proficiency scale', count: levels.data?.length },
          { id: 'framework', label: 'Competency dictionary', count: competencies.data?.length },
        ]}
      />

      {tab === 'profile' ? (
        profile.loading ? <Skeleton h={220} /> :
        profile.error ? <ErrorState error={profile.error} onRetry={profile.refetch} /> :
        (profile.data?.length ?? 0) === 0 ? (
          <Card>
            <EmptyState title="No competency levels recorded" icon={<IconLock size={26} />}
              action={<Link className="btn btn-primary" to="/app/assessment">Take your first assessment</Link>}>
              Levels appear here after you submit an assessment. A self-declared level is labelled as
              such — it is not treated as verified until an assessor reviews it.
            </EmptyState>
          </Card>
        ) : (
          <Card title="Assessed competencies"
            actions={<span className="tiny muted">{profile.data!.filter((r) => r.is_verified).length} assessor-verified</span>}>
            <table className="ledger">
              <thead>
                <tr>
                  <th>Competency</th><th>Domain</th><th>Level</th>
                  <th>Source</th><th className="num">Confidence</th><th>Assessed</th>
                </tr>
              </thead>
              <tbody>
                {profile.data!.map((row) => (
                  <tr key={row.competency_id}>
                    <td>
                      <div className="row gap-8">
                        <span className="mono tiny muted">{row.competency_code}</span>
                        <b className="small">{row.competency_name}</b>
                      </div>
                    </td>
                    <td className="tiny muted">{row.domain_name}</td>
                    <td>
                      <div className="row gap-8">
                        <Ladder level={row.level} />
                        <span className="mono tiny">{row.level}</span>
                      </div>
                    </td>
                    <td>
                      <span className={`tag ${row.is_verified ? 'tag-official' : 'tag-pending'}`}
                        style={{ fontSize: 9.5 }}>
                        {METHOD_LABEL[row.method] ?? row.method}
                      </span>
                    </td>
                    <td className="num tiny">{row.confidence}/5</td>
                    <td className="tiny muted nowrap">{formatDate(row.assessed_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        )
      ) : null}

      {tab === 'levels' ? (
        levels.loading ? <Skeleton h={200} /> :
        levels.error ? <ErrorState error={levels.error} onRetry={levels.refetch} /> : (
          <div className="stack gap-12">
            {levels.data?.map((lv) => (
              <article key={lv.level} className="card card-pad row gap-16" style={{ alignItems: 'flex-start' }}>
                <div style={{
                  fontFamily: 'var(--mono)', fontSize: 22, color: 'var(--teal)',
                  width: 34, flex: '0 0 34px', paddingTop: 2,
                }}>{lv.level}</div>
                <div className="grow">
                  <div className="row gap-8 wrap">
                    <b>{lv.label}</b>
                    <EvidenceTag status={lv.evidence_status} compact />
                  </div>
                  <p className="small muted" style={{ margin: '3px 0 8px' }}>{lv.summary}</p>
                  <ul className="tiny muted" style={{ margin: 0, paddingLeft: 17 }}>
                    {lv.criteria.map((c, i) => <li key={i}>{c}</li>)}
                  </ul>
                </div>
                <Ladder level={lv.level} large />
              </article>
            ))}
            <p className="tiny muted">
              <IconInfo size={12} /> Proficiency is a discrete 1–5 scale with stated observable
              criteria. It is deliberately not expressed as a percentage, because a percentage would
              imply a precision the underlying judgements do not have.
            </p>
          </div>
        )
      ) : null}

      {tab === 'framework' ? (
        competencies.loading ? <Skeleton h={300} /> :
        competencies.error ? <ErrorState error={competencies.error} onRetry={competencies.refetch} /> : (
          <div className="stack gap-20">
            {domains.data?.map((domain) => {
              const items = competencies.data?.filter((c) => c.domain_id === domain.id) ?? []
              if (!items.length) return null
              return (
                <Card key={domain.id}
                  title={<>{domain.code} · {domain.name}</>}
                  actions={<EvidenceTag status={domain.evidence_status} compact />}>
                  <p className="tiny muted" style={{ marginTop: 0 }}>{domain.description}</p>
                  <div className="stack gap-12">
                    {items.map((c) => (
                      <details key={c.id} style={{ borderTop: '1px solid var(--rule)', paddingTop: 10 }}>
                        <summary style={{ cursor: 'pointer', listStyle: 'none' }}>
                          <span className="row gap-8 wrap">
                            <span className="mono tiny muted">{c.code}</span>
                            <b className="small">{c.name}</b>
                            <span className="grow" />
                            <span className={`tag ${c.review_status === 'approved' ? 'tag-official' : 'tag-pending'}`}
                              style={{ fontSize: 9.5 }}>{c.review_status}</span>
                          </span>
                        </summary>
                        <div className="mt-8" style={{ paddingLeft: 4 }}>
                          <p className="small" style={{ margin: '0 0 6px' }}>{c.description}</p>
                          {c.rationale ? (
                            <p className="tiny muted" style={{ margin: '0 0 8px' }}>
                              <b>Why it matters: </b>{c.rationale}
                            </p>
                          ) : null}
                          {c.skills.length ? (
                            <ul className="tiny muted" style={{ margin: 0, paddingLeft: 17 }}>
                              {c.skills.map((s) => <li key={s.id}>{s.statement}</li>)}
                            </ul>
                          ) : null}
                          {c.source_ref ? (
                            <p className="tiny muted" style={{ marginTop: 8 }}>
                              <b>Source: </b>{c.source_ref}
                            </p>
                          ) : null}
                        </div>
                      </details>
                    ))}
                  </div>
                </Card>
              )
            })}
          </div>
        )
      ) : null}
    </div>
  )
}
