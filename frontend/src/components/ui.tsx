/** Shared presentational primitives. Every one carries real state behaviour. */
import {
  createContext, useCallback, useContext, useEffect, useMemo, useRef, useState,
} from 'react'
import type { ReactNode } from 'react'
import { ApiError, type EvidenceStatus } from '../lib/api'
import { IconAlert, IconCheck, IconInfo, IconX } from './icons'

/* ------------------------------------------------------------------ toasts */
type ToastKind = 'info' | 'success' | 'error'
interface Toast { id: number; kind: ToastKind; text: string }
const ToastCtx = createContext<{ push: (text: string, kind?: ToastKind) => void }>({
  push: () => {},
})

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<Toast[]>([])
  const seq = useRef(0)

  const push = useCallback((text: string, kind: ToastKind = 'info') => {
    const id = ++seq.current
    setItems((prev) => [...prev, { id, kind, text }])
    window.setTimeout(() => setItems((prev) => prev.filter((t) => t.id !== id)), 4600)
  }, [])

  const value = useMemo(() => ({ push }), [push])

  return (
    <ToastCtx.Provider value={value}>
      {children}
      <div className="toast-host" role="status" aria-live="polite">
        {items.map((t) => (
          <div key={t.id} className="toast" data-kind={t.kind}>
            {t.kind === 'error' ? <IconAlert size={15} /> : t.kind === 'success' ? <IconCheck size={15} /> : <IconInfo size={15} />}
            <span>{t.text}</span>
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  )
}

export const useToast = () => useContext(ToastCtx)

/* ------------------------------------------------------------------ loading / errors */
export function Spinner({ label }: { label?: string }) {
  return (
    <div className="row gap-8" style={{ padding: '22px 0', justifyContent: 'center' }}>
      <span className="spin" />
      {label ? <span className="small muted">{label}</span> : null}
    </div>
  )
}

export function Skeleton({ h = 16, w = '100%', mb = 8 }: { h?: number; w?: string | number; mb?: number }) {
  return <div className="skeleton" style={{ height: h, width: w, marginBottom: mb }} />
}

export function EmptyState({
  title, children, action, icon,
}: { title: string; children?: ReactNode; action?: ReactNode; icon?: ReactNode }) {
  return (
    <div className="state">
      {icon ?? <div className="ico"><IconInfo size={26} /></div>}
      <h4>{title}</h4>
      {children ? <p>{children}</p> : null}
      {action ? <div className="mt-8">{action}</div> : null}
    </div>
  )
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const status = error instanceof ApiError ? error.status : 0
  const denied = status === 403
  const message = error instanceof Error ? error.message : 'Something went wrong.'
  return (
    <div className="state">
      <div className="ico" style={{ color: denied ? 'var(--ochre)' : 'var(--critical)' }}>
        <IconAlert size={26} />
      </div>
      <h4>{denied ? 'Permission denied' : 'Could not load this'}</h4>
      <p>{message}</p>
      {onRetry && !denied ? (
        <button className="btn btn-sm mt-8" onClick={onRetry}>Try again</button>
      ) : null}
    </div>
  )
}

/* data hook: loading, error, retry, and a stable refetch */
export function useFetch<T>(fn: () => Promise<T>, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [loading, setLoading] = useState(true)
  const [nonce, setNonce] = useState(0)
  const mounted = useRef(true)

  useEffect(() => { mounted.current = true; return () => { mounted.current = false } }, [])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    fn()
      .then((res) => { if (!cancelled && mounted.current) setData(res) })
      .catch((err) => { if (!cancelled && mounted.current) setError(err) })
      .finally(() => { if (!cancelled && mounted.current) setLoading(false) })
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, nonce])

  return { data, error, loading, refetch: () => setNonce((n) => n + 1), setData }
}

/* ------------------------------------------------------------------ badges */
const EVIDENCE_META: Record<EvidenceStatus, { label: string; cls: string; title: string }> = {
  official: {
    label: 'Official',
    cls: 'tag-official',
    title: 'Verified against an official source document identified in the source register.',
  },
  provisional: {
    label: 'Provisional',
    cls: 'tag-provisional',
    title: 'Authored for this prototype from public role descriptions. Not an officially validated framework — requires expert review.',
  },
  demonstration: {
    label: 'Demonstration',
    cls: 'tag-demo',
    title: 'Sample content created for evaluation. Not real government course data.',
  },
}

export function EvidenceTag({ status, compact }: { status: EvidenceStatus; compact?: boolean }) {
  const meta = EVIDENCE_META[status] ?? EVIDENCE_META.provisional
  return (
    <span className={`tag ${meta.cls}`} title={meta.title}>
      {compact ? null : <span aria-hidden>●</span>}
      {meta.label}
    </span>
  )
}

export function Tag({ children, tone = 'neutral' }: { children: ReactNode; tone?: string }) {
  return <span className={`tag tag-${tone}`}>{children}</span>
}

/* ------------------------------------------------------------------ proficiency ladder */
export function Ladder({ level, target, large }: { level: number; target?: number; large?: boolean }) {
  const segments = [1, 2, 3, 4, 5]
  return (
    <span className={`ladder${large ? ' ladder-lg' : ''}`} role="img"
      aria-label={`Proficiency ${level} of 5${target ? `, target ${target}` : ''}`}>
      {segments.map((s) => {
        const filled = level >= s
        const half = !filled && level > s - 1
        const isTarget = target === s && !filled
        return (
          <i key={s}
            className={`${filled ? 'on' : ''} ${half ? 'half' : ''} ${isTarget ? 'target' : ''}`} />
        )
      })}
    </span>
  )
}

export function SeverityTag({ severity }: { severity: string }) {
  const tone =
    severity === 'critical' ? 'critical' :
    severity === 'high' ? 'provisional' :
    severity === 'moderate' ? 'neutral' :
    severity === 'low' ? 'neutral' : 'official'
  return <span className={`tag tag-${tone}`}>{severity}</span>
}

/* ------------------------------------------------------------------ components */
export function Card({
  title, children, actions, footer, className = '', reg,
}: {
  title?: ReactNode; children: ReactNode; actions?: ReactNode
  footer?: ReactNode; className?: string; reg?: boolean
}) {
  return (
    <section className={`card ${reg ? 'reg' : ''} ${className}`}>
      {title ? (
        <header className="card-head">
          <h3>{title}</h3>
          <span className="spacer" />
          {actions}
        </header>
      ) : null}
      <div className="card-body">{children}</div>
      {footer ? <footer className="card-foot">{footer}</footer> : null}
    </section>
  )
}

export function Stat({
  label, value, detail, tone, suffix,
}: { label: string; value: ReactNode; detail?: ReactNode; tone?: 'good' | 'warn' | 'bad'; suffix?: string }) {
  return (
    <div className="stat" data-tone={tone}>
      <div className="k">{label}</div>
      <div className="v">{value}{suffix ? <small>{suffix}</small> : null}</div>
      {detail ? <div className="d">{detail}</div> : null}
    </div>
  )
}

export function Banner({
  kind = 'info', children,
}: { kind?: 'info' | 'warn' | 'bad' | 'good'; children: ReactNode }) {
  const icon = kind === 'bad' || kind === 'warn' ? <IconAlert size={15} /> : <IconInfo size={15} />
  return <div className={`banner banner-${kind}`}>{icon}<div>{children}</div></div>
}

/* ------------------------------------------------------------------ modal */
export function Modal({
  open, onClose, title, children, footer, width,
}: {
  open: boolean; onClose: () => void; title: string
  children: ReactNode; footer?: ReactNode; width?: number
}) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
      if (e.key === 'Tab' && ref.current) {
        const focusables = ref.current.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
        )
        if (focusables.length === 0) return
        const first = focusables[0]
        const last = focusables[focusables.length - 1]
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus() }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus() }
      }
    }
    document.addEventListener('keydown', onKey)
    const previouslyFocused = document.activeElement as HTMLElement | null
    ref.current?.querySelector<HTMLElement>('button, input, textarea, select')?.focus()
    return () => {
      document.removeEventListener('keydown', onKey)
      previouslyFocused?.focus?.()
    }
  }, [open, onClose])

  if (!open) return null
  return (
    <div className="overlay" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose() }}>
      <div className="modal" ref={ref} role="dialog" aria-modal="true" aria-label={title}
        style={width ? { maxWidth: width } : undefined}>
        <header className="card-head">
          <h3>{title}</h3>
          <span className="spacer" />
          <button className="btn btn-ghost btn-sm" onClick={onClose} aria-label="Close dialog">
            <IconX size={15} />
          </button>
        </header>
        <div className="card-body">{children}</div>
        {footer ? <footer className="card-foot row gap-8" style={{ justifyContent: 'flex-end' }}>{footer}</footer> : null}
      </div>
    </div>
  )
}

/* ------------------------------------------------------------------ misc */
export function Field({
  label, hint, error, children, htmlFor,
}: { label: string; hint?: string; error?: string; children: ReactNode; htmlFor?: string }) {
  return (
    <div className="field">
      <label htmlFor={htmlFor}>{label}</label>
      {children}
      {error ? <span className="err">{error}</span> : hint ? <span className="hint">{hint}</span> : null}
    </div>
  )
}

export function Tabs<T extends string>({
  tabs, value, onChange,
}: { tabs: { id: T; label: string; count?: number }[]; value: T; onChange: (v: T) => void }) {
  return (
    <div className="tabs" role="tablist">
      {tabs.map((t) => (
        <button key={t.id} role="tab" aria-selected={value === t.id}
          onClick={() => onChange(t.id)}>
          {t.label}{typeof t.count === 'number' ? ` (${t.count})` : ''}
        </button>
      ))}
    </div>
  )
}

export function CopyButton({ text, label = 'Copy' }: { text: string; label?: string }) {
  const { push } = useToast()
  return (
    <button className="btn btn-sm btn-ghost" onClick={async () => {
      try {
        await navigator.clipboard.writeText(text)
        push('Copied to clipboard', 'success')
      } catch {
        push('Clipboard is not available in this browser', 'error')
      }
    }}>{label}</button>
  )
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

export function formatDuration(minutes: number): string {
  if (minutes < 60) return `${minutes} min`
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return m ? `${h}h ${m}m` : `${h}h`
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}
