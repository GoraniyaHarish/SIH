import { useState } from 'react'
import { api, type Competency, type Domain, type Framework, type JobRole } from '../lib/api'
import {
  Banner, Card, ErrorState, EvidenceTag, Field, Modal, Skeleton, Tabs, useFetch, useToast,
} from '../components/ui'
import { IconPlus } from '../components/icons'

export default function AdminFramework() {
  const { push } = useToast()
  const [tab, setTab] = useState<'domains' | 'roles' | 'add'>('domains')
  const fw = useFetch<Framework>(() => api.get<Framework>('/framework'))
  const domains = useFetch<Domain[]>(() => api.get<Domain[]>('/framework/domains'))
  const competencies = useFetch<Competency[]>(() => api.get<Competency[]>('/framework/competencies?limit=100'))
  const roles = useFetch<JobRole[]>(() => api.get<JobRole[]>('/framework/job-roles'))

  const [openDomain, setOpenDomain] = useState(false)
  const [openComp, setOpenComp] = useState(false)
  const [domainForm, setDomainForm] = useState({ code: '', name: '', description: '', kind: 'functional' })
  const [compForm, setCompForm] = useState({ domain_id: '', code: '', name: '', description: '', rationale: '' })
  const [busy, setBusy] = useState(false)

  async function addDomain() {
    setBusy(true)
    try {
      await api.post('/framework/domains', domainForm)
      push('Domain created', 'success')
      setOpenDomain(false); setDomainForm({ code: '', name: '', description: '', kind: 'functional' })
      domains.refetch()
    } catch (e) { push(e instanceof Error ? e.message : 'Failed', 'error') } finally { setBusy(false) }
  }

  async function addCompetency() {
    setBusy(true)
    try {
      await api.post('/framework/competencies', compForm)
      push('Competency created', 'success')
      setOpenComp(false); setCompForm({ domain_id: '', code: '', name: '', description: '', rationale: '' })
      competencies.refetch(); domains.refetch()
    } catch (e) { push(e instanceof Error ? e.message : 'Failed', 'error') } finally { setBusy(false) }
  }

  async function review(id: string, review_status: string) {
    try {
      await api.patch(`/framework/competencies/${id}`, { review_status })
      push(
        review_status === 'approved'
          ? 'Approved. A provisional competency becomes official on approval.'
          : `Marked ${review_status}`,
        'success',
      )
      competencies.refetch()
    } catch (e) { push(e instanceof Error ? e.message : 'Failed', 'error') }
  }

  if (fw.loading || domains.loading) return <Skeleton h={360} />
  if (domains.error) return <ErrorState error={domains.error} onRetry={domains.refetch} />

  return (
    <div className="stack gap-20">
      <div className="row gap-12 wrap" style={{ alignItems: 'flex-end' }}>
        <div className="grow">
          <h2 className="display" style={{ fontSize: 26 }}>Competency framework</h2>
          <p className="small muted" style={{ margin: '4px 0 0' }}>
            Version <b>{fw.data?.label}</b> · {domains.data?.length} domains ·{' '}
            {competencies.data?.length} competencies · {roles.data?.length} job roles
          </p>
        </div>
        <button className="btn" onClick={() => setOpenDomain(true)}><IconPlus size={14} /> Domain</button>
        <button className="btn btn-primary" onClick={() => setOpenComp(true)}><IconPlus size={14} /> Competency</button>
      </div>

      <Banner kind="warn">
        <b>Framework status: {fw.data?.evidence_status}.</b> {fw.data?.notes} Approving a competency
        is the only path that promotes it from provisional to official, and that decision is recorded
        in the audit trail against your account.
      </Banner>

      <Tabs value={tab} onChange={setTab} tabs={[
        { id: 'domains', label: 'Domains & competencies', count: domains.data?.length },
        { id: 'roles', label: 'Job roles', count: roles.data?.length },
        { id: 'add', label: 'Governance notes' },
      ]} />

      {tab === 'domains' ? (
        <div className="stack gap-16">
          {domains.data?.map((d) => {
            const items = competencies.data?.filter((c) => c.domain_id === d.id) ?? []
            return (
              <Card key={d.id} title={<>{d.code} · {d.name}</>}
                actions={<EvidenceTag status={d.evidence_status} compact />}>
                <p className="tiny muted" style={{ marginTop: 0 }}>{d.description}</p>
                <table className="ledger">
                  <thead><tr><th>Code</th><th>Competency</th><th>Evidence</th><th>Review</th><th /></tr></thead>
                  <tbody>
                    {items.map((c) => (
                      <tr key={c.id}>
                        <td className="mono tiny">{c.code}</td>
                        <td>
                          <b className="small">{c.name}</b>
                          <div className="tiny muted">{c.skills.length} observable skills</div>
                        </td>
                        <td><EvidenceTag status={c.evidence_status} compact /></td>
                        <td>
                          <span className={`tag ${c.review_status === 'approved' ? 'tag-official' : 'tag-pending'}`}
                            style={{ fontSize: 9.5 }}>{c.review_status}</span>
                        </td>
                        <td>
                          {c.review_status !== 'approved' ? (
                            <button className="btn btn-sm" onClick={() => review(c.id, 'approved')}>Approve</button>
                          ) : (
                            <button className="btn btn-sm btn-ghost" onClick={() => review(c.id, 'pending')}>Reopen</button>
                          )}
                        </td>
                      </tr>
                    ))}
                    {items.length === 0 ? (
                      <tr><td colSpan={5} className="tiny muted">No competencies in this domain yet.</td></tr>
                    ) : null}
                  </tbody>
                </table>
              </Card>
            )
          })}
        </div>
      ) : null}

      {tab === 'roles' ? (
        <div className="stack gap-16">
          {roles.data?.map((r) => (
            <Card key={r.id} title={r.title}
              actions={<><span className="tag tag-neutral" style={{ fontSize: 9.5 }}>{r.cadre}</span>
                <EvidenceTag status={r.evidence_status} compact /></>}>
              <p className="tiny muted" style={{ marginTop: 0 }}>{r.description}</p>
              <table className="ledger">
                <thead><tr><th>Competency</th><th>Domain</th><th className="num">Required</th>
                  <th className="num">Importance</th><th>Critical</th></tr></thead>
                <tbody>
                  {r.requirements.map((req) => (
                    <tr key={req.competency_id}>
                      <td><span className="mono tiny muted">{req.competency_code}</span> <b className="small">{req.competency_name}</b></td>
                      <td className="tiny muted">{req.domain_name}</td>
                      <td className="num mono">{req.required_level}</td>
                      <td className="num mono">{req.importance}/5</td>
                      <td>{req.is_critical ? <span className="tag tag-critical" style={{ fontSize: 9.5 }}>critical</span> : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          ))}
        </div>
      ) : null}

      {tab === 'add' ? (
        <Card title="How framework governance works here">
          <ul className="small" style={{ margin: 0, paddingLeft: 18, lineHeight: 1.9 }}>
            <li>Every domain, competency and role mapping carries an <b>evidence status</b>.</li>
            <li>New items default to <b>provisional</b> and are not presented as official.</li>
            <li>An assessor or administrator records a <b>review decision</b>; approval promotes the
              item to <b>official</b> and is audit-logged with the reviewer's identity.</li>
            <li>Required levels per role are editable through the requirements API; replacing them is
              a full substitution so the role's requirement set cannot drift silently.</li>
            <li>Prerequisite edges gate recommendations: a dependent gap is deferred until its
              prerequisite is closed.</li>
          </ul>
        </Card>
      ) : null}

      <Modal open={openDomain} onClose={() => setOpenDomain(false)} title="Add a competency domain"
        footer={<>
          <button className="btn" onClick={() => setOpenDomain(false)}>Cancel</button>
          <button className="btn btn-primary" onClick={addDomain} disabled={busy || !domainForm.code || !domainForm.name}>
            {busy ? <span className="spin" /> : null} Create domain
          </button>
        </>}>
        <div className="grid-2">
          <Field label="Code"><input type="text" value={domainForm.code} placeholder="e.g. SAMP"
            onChange={(e) => setDomainForm({ ...domainForm, code: e.target.value.toUpperCase() })} /></Field>
          <Field label="Kind">
            <select value={domainForm.kind} onChange={(e) => setDomainForm({ ...domainForm, kind: e.target.value })}>
              <option value="functional">Functional</option>
              <option value="domain">Domain</option>
              <option value="behavioural">Behavioural</option>
            </select>
          </Field>
        </div>
        <Field label="Name"><input type="text" value={domainForm.name}
          onChange={(e) => setDomainForm({ ...domainForm, name: e.target.value })} /></Field>
        <Field label="Description"><textarea value={domainForm.description}
          onChange={(e) => setDomainForm({ ...domainForm, description: e.target.value })} /></Field>
        <Banner kind="info">New domains are created as <b>provisional</b> evidence by default.</Banner>
      </Modal>

      <Modal open={openComp} onClose={() => setOpenComp(false)} title="Add a competency"
        footer={<>
          <button className="btn" onClick={() => setOpenComp(false)}>Cancel</button>
          <button className="btn btn-primary" onClick={addCompetency}
            disabled={busy || !compForm.domain_id || !compForm.code || !compForm.name}>
            {busy ? <span className="spin" /> : null} Create competency
          </button>
        </>}>
        <Field label="Domain">
          <select value={compForm.domain_id} onChange={(e) => setCompForm({ ...compForm, domain_id: e.target.value })}>
            <option value="">Select a domain…</option>
            {domains.data?.map((d) => <option key={d.id} value={d.id}>{d.code} · {d.name}</option>)}
          </select>
        </Field>
        <div className="grid-2">
          <Field label="Code"><input type="text" value={compForm.code} placeholder="e.g. SAMP.05"
            onChange={(e) => setCompForm({ ...compForm, code: e.target.value.toUpperCase() })} /></Field>
          <Field label="Name"><input type="text" value={compForm.name}
            onChange={(e) => setCompForm({ ...compForm, name: e.target.value })} /></Field>
        </div>
        <Field label="Description"><textarea value={compForm.description}
          onChange={(e) => setCompForm({ ...compForm, description: e.target.value })} /></Field>
        <Field label="Why it matters" hint="Shown to learners beside the competency.">
          <textarea value={compForm.rationale}
            onChange={(e) => setCompForm({ ...compForm, rationale: e.target.value })} /></Field>
      </Modal>
    </div>
  )
}
