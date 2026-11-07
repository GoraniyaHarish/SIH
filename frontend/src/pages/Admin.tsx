import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type AdminOverview, type AuditEvent } from '../lib/api'
import {
  Banner, Card, ErrorState, Skeleton, Stat, useFetch, formatDateTime,
} from '../components/ui'
import { IconDownload, IconPlug, IconShield, IconUsers } from '../components/icons'

const STATUS_TONE: Record<string, string> = {
  ok: 'tag-official', not_configured: 'tag-pending', unreachable: 'tag-critical',
  auth_failed: 'tag-critical', degraded: 'tag-provisional',
}

export default function Admin() {
  const overview = useFetch<AdminOverview>(() => api.get<AdminOverview>('/admin/overview'))
  const audit = useFetch<AuditEvent[]>(() => api.get<AuditEvent[]>('/admin/audit?limit=14'))
  const [exporting, setExporting] = useState(false)

  async function exportAudit() {
    setExporting(true)
    try {
      const rows = await api.get<AuditEvent[]>('/admin/audit?limit=100')
      const header = 'timestamp,actor_role,action,resource_type,resource_id,outcome\n'
      const body = rows.map((r) =>
        [r.created_at, r.actor_role ?? '', r.action, r.resource_type ?? '', r.resource_id ?? '', r.outcome]
          .map((v) => `"${String(v).replace(/"/g, '""')}"`).join(','),
      ).join('\n')
      const blob = new Blob([header + body], { type: 'text/csv;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `audit-log-${new Date().toISOString().slice(0, 10)}.csv`
      link.click()
      URL.revokeObjectURL(url)
    } finally { setExporting(false) }
  }

  if (overview.loading) return <Skeleton h={380} />
  if (overview.error) return <ErrorState error={overview.error} onRetry={overview.refetch} />
  if (!overview.data) return null
  const o = overview.data

  return (
    <div className="stack gap-20">
      <div>
        <h2 className="display" style={{ fontSize: 26 }}>Admin workspace</h2>
        <p className="small muted" style={{ margin: '4px 0 0' }}>
          People, framework, AI configuration and integration status — all derived from live records.
        </p>
      </div>

      <div className="stats">
        <Stat label="Active users" value={o.active_users}
          detail={Object.entries(o.users_by_role).map(([r, n]) => `${n} ${r}`).join(' · ')} />
        <Stat label="Courses" value={o.courses_total}
          detail={`${o.quizzes_total} assessments · ${o.attempts_total} attempts`} />
        <Stat label="Documents" value={Object.values(o.documents_by_status).reduce((a, b) => a + b, 0)}
          detail={Object.entries(o.documents_by_status).map(([s, n]) => `${n} ${s}`).join(' · ') || 'none uploaded'} />
        <Stat label="AI calls (24h)" value={o.ai_calls_24h}
          tone={o.ai_error_rate_24h && o.ai_error_rate_24h > 20 ? 'bad' : undefined}
          detail={o.ai_error_rate_24h === null ? 'no calls recorded' : `${o.ai_error_rate_24h}% error rate`} />
      </div>

      <div className="grid-2">
        <Card title="Integration status"
          actions={<Link className="btn btn-sm btn-ghost" to="/app/admin/integrations"><IconPlug size={12} /> Manage</Link>}>
          <div className="stack gap-8">
            {o.integrations.map((i) => (
              <div key={i.provider} className="doc-row">
                <div className="grow" style={{ minWidth: 0 }}>
                  <div className="row gap-8 wrap">
                    <b className="small">{i.provider.replace(/_/g, ' ')}</b>
                    <span className={`tag ${STATUS_TONE[i.status] ?? 'tag-neutral'}`} style={{ fontSize: 9.5 }}>
                      {i.status.replace(/_/g, ' ')}
                    </span>
                  </div>
                  <div className="tiny muted">
                    {i.configured ? `configured · ${i.base_url_host}` : 'no credentials configured'}
                    {i.checked_at ? ` · checked ${formatDateTime(i.checked_at)}` : ' · never probed'}
                  </div>
                </div>
              </div>
            ))}
          </div>
          <Banner kind="warn">
            <b>Honest status.</b> No public iGOT Karmayogi or NSSTA API was found during research, so
            these adapters remain inactive until an authorised operator supplies credentials. Nothing
            here is simulated.
          </Banner>
        </Card>

        <Card title="Quick actions">
          <div className="stack gap-8">
            <Link className="btn btn-block" to="/app/admin/users" style={{ justifyContent: 'flex-start' }}>
              <IconUsers size={14} /> Manage people &amp; roles
            </Link>
            <Link className="btn btn-block" to="/app/admin/framework" style={{ justifyContent: 'flex-start' }}>
              <IconShield size={14} /> Competency framework
            </Link>
            <Link className="btn btn-block" to="/app/admin/integrations" style={{ justifyContent: 'flex-start' }}>
              <IconPlug size={14} /> Integrations &amp; system health
            </Link>
            <button className="btn btn-block" onClick={exportAudit} disabled={exporting}
              style={{ justifyContent: 'flex-start' }}>
              <IconDownload size={14} /> {exporting ? 'Exporting…' : 'Export audit log (CSV)'}
            </button>
          </div>
          <div className="divider" />
          <p className="tiny muted" style={{ margin: 0 }}>
            {o.audit_events_24h} audit events recorded in the last 24 hours. Audit rows are written in
            the same transaction as the action they describe.
          </p>
        </Card>
      </div>

      <Card title="Recent audit trail"
        actions={<span className="tiny muted">append-only · no document content or secrets</span>}>
        {audit.loading ? <Skeleton h={120} /> :
        audit.error ? <ErrorState error={audit.error} onRetry={audit.refetch} /> : (
          <table className="ledger">
            <thead><tr><th>When</th><th>Actor</th><th>Action</th><th>Resource</th><th>Outcome</th></tr></thead>
            <tbody>
              {(audit.data ?? []).map((e) => (
                <tr key={e.id}>
                  <td className="tiny mono nowrap">{formatDateTime(e.created_at)}</td>
                  <td className="tiny">{e.actor_role ?? 'system'}</td>
                  <td className="tiny mono">{e.action}</td>
                  <td className="tiny muted">{e.resource_type ?? '—'}{e.detail ? ` · ${e.detail.slice(0, 46)}` : ''}</td>
                  <td>
                    <span className={`tag ${e.outcome === 'success' ? 'tag-official' : 'tag-critical'}`}
                      style={{ fontSize: 9.5 }}>{e.outcome}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  )
}
