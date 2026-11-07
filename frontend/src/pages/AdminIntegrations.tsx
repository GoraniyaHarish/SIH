import { useState } from 'react'
import { api, type Integration } from '../lib/api'
import {
  Banner, Card, ErrorState, Skeleton, useFetch, useToast, formatDateTime,
} from '../components/ui'
import { IconPlug, IconRefresh } from '../components/icons'

const TONE: Record<string, string> = {
  ok: 'tag-official', degraded: 'tag-provisional',
  not_configured: 'tag-pending', unreachable: 'tag-critical', auth_failed: 'tag-critical',
}

interface SystemInfo {
  ai: {
    configured: boolean; reachable: boolean; message: string; provider: string
    chat_model: string; embedding_model: string; embedding_dim: number
    external_documents_enabled: boolean
    operations: { operation: string; calls: number; avg_latency_ms: number }[]
  }
  security: {
    warnings: string[]; cors_origins: string[]; access_token_minutes: number
    refresh_token_days: number; login_max_attempts: number; lockout_threshold: number
  }
  storage: { max_upload_mb: number; allowed_mime: string[]; upload_dir: string }
}

export default function AdminIntegrations() {
  const { push } = useToast()
  const integ = useFetch<Integration[]>(() => api.get<Integration[]>('/admin/integrations'))
  const system = useFetch<SystemInfo>(() => api.get<SystemInfo>('/admin/system'))
  const [probing, setProbing] = useState(false)

  async function probe() {
    setProbing(true)
    try {
      const results = await api.post<Integration[]>('/admin/integrations/probe')
      const summary = results.map((r) => `${r.provider}: ${r.status}`).join(', ')
      push(`Probe complete — ${summary}`, results.every((r) => r.status === 'ok') ? 'success' : 'info')
      integ.refetch(); system.refetch()
    } catch (e) {
      push(e instanceof Error ? e.message : 'Probe failed', 'error')
    } finally { setProbing(false) }
  }

  if (integ.loading || system.loading) return <Skeleton h={380} />
  if (integ.error) return <ErrorState error={integ.error} onRetry={integ.refetch} />

  const s = system.data

  return (
    <div className="stack gap-20">
      <div className="row gap-12 wrap" style={{ alignItems: 'flex-end' }}>
        <div className="grow">
          <h2 className="display" style={{ fontSize: 26 }}>Integrations &amp; system</h2>
          <p className="small muted" style={{ margin: '4px 0 0' }}>
            Connection probes perform real HTTP requests. A status is only “ok” when an endpoint
            actually responded.
          </p>
        </div>
        <button className="btn btn-primary" onClick={probe} disabled={probing}>
          <IconRefresh size={14} /> {probing ? 'Probing…' : 'Run connectivity check'}
        </button>
      </div>

      <Banner kind="warn">
        <b>Research finding.</b> No publicly documented, lawfully accessible iGOT Karmayogi or NSSTA
        API was located. These adapters are complete boundaries that activate only when an authorised
        operator supplies credentials. No external records are fabricated, and the seeded catalogue is
        labelled demonstration content — never attributed to a live government API.
      </Banner>

      <div className="stack gap-16">
        {integ.data?.map((i) => (
          <Card key={i.provider} title={i.provider.replace(/_/g, ' ').toUpperCase()}
            actions={<span className={`tag ${TONE[i.status] ?? 'tag-neutral'}`}>{i.status.replace(/_/g, ' ')}</span>}>
            <div className="grid-3 mb-12">
              <div>
                <div className="eyebrow">Configured</div>
                <div className="small">{i.configured ? 'Yes' : 'No credentials'}</div>
              </div>
              <div>
                <div className="eyebrow">Host</div>
                <div className="small mono">{i.base_url_host ?? '—'}</div>
              </div>
              <div>
                <div className="eyebrow">Last check</div>
                <div className="small">{i.checked_at ? formatDateTime(i.checked_at) : 'Never probed'}</div>
              </div>
            </div>
            <Banner kind={i.status === 'ok' ? 'good' : i.status === 'not_configured' ? 'info' : 'bad'}>
              {i.detail}
            </Banner>
            <p className="tiny muted mt-12" style={{ marginBottom: 0 }}>{i.notes}</p>
            <div className="row gap-6 mt-8 wrap">
              <span className="tiny muted">Capabilities:</span>
              {i.capabilities.map((c) => (
                <span key={c} className="tag tag-neutral" style={{ fontSize: 9.5 }}>{c}</span>
              ))}
            </div>
            <div className="divider" />
            <p className="tiny muted" style={{ margin: 0 }}>
              <IconPlug size={12} /> To activate: set the provider's base URL and token in the
              environment, then run the connectivity check. The same adapter code then makes real
              requests — no code change required.
            </p>
          </Card>
        ))}
      </div>

      {s ? (
        <>
          <Card title="AI provider">
            <div className="row gap-12 wrap mb-12">
              <span className={`tag ${s.ai.configured && s.ai.reachable ? 'tag-official' : s.ai.configured ? 'tag-critical' : 'tag-pending'}`}>
                {s.ai.configured ? (s.ai.reachable ? 'reachable' : 'unreachable') : 'not configured'}
              </span>
              <span className="small muted">{s.ai.message}</span>
            </div>
            <table className="ledger">
              <tbody>
                <tr><td>Provider</td><td className="mono tiny">{s.ai.provider}</td></tr>
                <tr><td>Chat model</td><td className="mono tiny">{s.ai.chat_model}</td></tr>
                <tr><td>Embedding model</td><td className="mono tiny">{s.ai.embedding_model} ({s.ai.embedding_dim}d)</td></tr>
                <tr><td>Outbound document text</td>
                  <td className="tiny">{s.ai.external_documents_enabled ? 'permitted' : 'blocked by policy'}</td></tr>
              </tbody>
            </table>
            {s.ai.operations.length ? (
              <>
                <div className="eyebrow mt-16 mb-8">Recorded operations</div>
                <table className="ledger">
                  <thead><tr><th>Operation</th><th className="num">Calls</th><th className="num">Avg latency</th></tr></thead>
                  <tbody>
                    {s.ai.operations.map((o) => (
                      <tr key={o.operation}>
                        <td className="tiny mono">{o.operation}</td>
                        <td className="num">{o.calls}</td>
                        <td className="num">{o.avg_latency_ms} ms</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </>
            ) : <p className="tiny muted mt-12">No AI calls recorded yet.</p>}
          </Card>

          <div className="grid-2">
            <Card title="Security configuration">
              {s.security.warnings.length ? (
                <div className="stack gap-8 mb-12">
                  {s.security.warnings.map((w) => (
                    <Banner key={w} kind="warn">{w}</Banner>
                  ))}
                </div>
              ) : (
                <Banner kind="good">No configuration warnings for this environment.</Banner>
              )}
              <table className="ledger">
                <tbody>
                  <tr><td>Access token lifetime</td><td className="num mono">{s.security.access_token_minutes} min</td></tr>
                  <tr><td>Refresh token lifetime</td><td className="num mono">{s.security.refresh_token_days} days</td></tr>
                  <tr><td>Login attempts / window</td><td className="num mono">{s.security.login_max_attempts}</td></tr>
                  <tr><td>Lockout threshold</td><td className="num mono">{s.security.lockout_threshold}</td></tr>
                  <tr><td>Allowed origins</td><td className="tiny mono">{s.security.cors_origins.join(', ')}</td></tr>
                </tbody>
              </table>
            </Card>

            <Card title="Upload policy">
              <table className="ledger">
                <tbody>
                  <tr><td>Maximum size</td><td className="num mono">{s.storage.max_upload_mb} MB</td></tr>
                  <tr><td>Accepted types</td><td className="tiny mono">{s.storage.allowed_mime.join(', ')}</td></tr>
                  <tr><td>Storage root</td><td className="tiny mono">{s.storage.upload_dir}</td></tr>
                </tbody>
              </table>
              <p className="tiny muted mt-12" style={{ marginBottom: 0 }}>
                Files are validated by magic bytes rather than extension, named with a generated
                UUID, and stored outside any web-served directory. Access is only through authorised
                endpoints.
              </p>
            </Card>
          </div>
        </>
      ) : null}
    </div>
  )
}
