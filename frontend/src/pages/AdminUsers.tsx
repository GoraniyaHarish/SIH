import { useMemo, useState } from 'react'
import { api, type JobRole, type Role, type User } from '../lib/api'
import {
  Banner, Card, EmptyState, ErrorState, Field, Modal, Skeleton, Tag, useFetch, useToast,
  formatDateTime,
} from '../components/ui'
import { IconPlus, IconSearch, IconUsers } from '../components/icons'

export default function AdminUsers() {
  const { push } = useToast()
  const [q, setQ] = useState('')
  const [roleFilter, setRoleFilter] = useState('')
  const users = useFetch<User[]>(() => api.get<User[]>('/admin/users?limit=100'))
  const departments = useFetch<{ id: string; name: string }[]>(() => api.get('/departments'))
  const roles = useFetch<JobRole[]>(() => api.get<JobRole[]>('/framework/job-roles'))
  const [showCreate, setShowCreate] = useState(false)
  const [editing, setEditing] = useState<User | null>(null)

  const filtered = useMemo(() => {
    let list = users.data ?? []
    if (q.trim()) {
      const needle = q.trim().toLowerCase()
      list = list.filter((u) =>
        u.full_name.toLowerCase().includes(needle) || u.email.toLowerCase().includes(needle))
    }
    if (roleFilter) list = list.filter((u) => u.role === roleFilter)
    return list
  }, [users.data, q, roleFilter])

  return (
    <div className="stack gap-20">
      <div className="row gap-12 wrap" style={{ alignItems: 'flex-end' }}>
        <div className="grow">
          <h2 className="display" style={{ fontSize: 26 }}>People &amp; roles</h2>
          <p className="small muted" style={{ margin: '4px 0 0' }}>
            Roles are enforced by the backend on every request. A role change revokes existing sessions.
          </p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
          <IconPlus size={14} /> Add person
        </button>
      </div>

      <Banner kind="info">
        Self-registration always creates a <b>learner</b>. Elevated roles can only be granted here, so
        privilege escalation is not possible from the public signup form.
      </Banner>

      <div className="toolbar">
        <div className="row gap-8">
          <IconSearch size={15} />
          <input type="search" placeholder="Search name or email…" value={q}
            onChange={(e) => setQ(e.target.value)} aria-label="Search people" />
        </div>
        <select value={roleFilter} onChange={(e) => setRoleFilter(e.target.value)} aria-label="Filter by role">
          <option value="">All roles</option>
          <option value="learner">Learners</option>
          <option value="manager">Managers</option>
          <option value="assessor">Assessors</option>
          <option value="admin">Administrators</option>
        </select>
        <span className="grow" />
        <span className="mono tiny muted">{filtered.length} shown</span>
      </div>

      <Card>
        {users.loading ? <Skeleton h={180} /> :
        users.error ? <ErrorState error={users.error} onRetry={users.refetch} /> :
        filtered.length === 0 ? (
          <EmptyState title="No people match" icon={<IconUsers size={26} />}>
            Adjust the search or role filter.
          </EmptyState>
        ) : (
          <table className="ledger">
            <thead>
              <tr><th>Name</th><th>Role</th><th>Department</th><th>Job role</th>
                <th>Status</th><th>Last sign-in</th><th /></tr>
            </thead>
            <tbody>
              {filtered.map((u) => (
                <tr key={u.id}>
                  <td>
                    <b className="small">{u.full_name}</b>
                    <div className="tiny muted">{u.email}</div>
                  </td>
                  <td><Tag tone={u.role === 'admin' ? 'critical' : u.role === 'learner' ? 'neutral' : 'provisional'}>{u.role}</Tag></td>
                  <td className="tiny muted">{u.department_name ?? '—'}</td>
                  <td className="tiny muted">{u.job_role_title ?? '—'}</td>
                  <td>
                    <span className={`tag ${u.is_active ? 'tag-official' : 'tag-pending'}`} style={{ fontSize: 9.5 }}>
                      {u.is_active ? 'active' : 'inactive'}
                    </span>
                  </td>
                  <td className="tiny mono nowrap muted">{u.last_login_at ? formatDateTime(u.last_login_at) : 'never'}</td>
                  <td>
                    <button className="btn btn-sm" onClick={() => setEditing(u)}>Manage</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      <CreateUserModal
        open={showCreate} onClose={() => setShowCreate(false)}
        departments={departments.data ?? []} roles={roles.data ?? []}
        onCreated={() => { setShowCreate(false); users.refetch() }}
      />

      <ManageUserModal
        user={editing} onClose={() => setEditing(null)}
        departments={departments.data ?? []} roles={roles.data ?? []}
        onSaved={() => { setEditing(null); users.refetch() }}
        push={push}
      />
    </div>
  )
}

function CreateUserModal({
  open, onClose, departments, roles, onCreated,
}: {
  open: boolean; onClose: () => void
  departments: { id: string; name: string }[]; roles: JobRole[]; onCreated: () => void
}) {
  const { push } = useToast()
  const [form, setForm] = useState({
    email: '', full_name: '', password: '', role: 'learner' as Role,
    department_id: '', job_role_id: '', designation: '',
  })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit() {
    setBusy(true); setError(null)
    try {
      await api.post('/admin/users', {
        ...form,
        department_id: form.department_id || null,
        job_role_id: form.job_role_id || null,
        designation: form.designation || null,
      })
      push(`Created ${form.email}`, 'success')
      setForm({ email: '', full_name: '', password: '', role: 'learner', department_id: '', job_role_id: '', designation: '' })
      onCreated()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not create user')
    } finally { setBusy(false) }
  }

  return (
    <Modal open={open} onClose={onClose} title="Add a person" width={560}
      footer={
        <>
          <button className="btn" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" onClick={submit}
            disabled={busy || !form.email || !form.full_name || form.password.length < 10}>
            {busy ? <span className="spin" /> : null} Create account
          </button>
        </>
      }>
      {error ? <div className="mb-12"><Banner kind="bad">{error}</Banner></div> : null}
      <Field label="Full name"><input type="text" value={form.full_name}
        onChange={(e) => setForm({ ...form, full_name: e.target.value })} /></Field>
      <Field label="Email"><input type="email" value={form.email}
        onChange={(e) => setForm({ ...form, email: e.target.value })} /></Field>
      <Field label="Temporary password" hint="At least 10 characters with upper, lower and a digit. The user should change it after first sign-in.">
        <input type="password" value={form.password}
          onChange={(e) => setForm({ ...form, password: e.target.value })} />
      </Field>
      <div className="grid-2">
        <Field label="Role">
          <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value as Role })}>
            <option value="learner">Learner</option>
            <option value="manager">Training Manager</option>
            <option value="assessor">Competency Assessor</option>
            <option value="admin">Administrator</option>
          </select>
        </Field>
        <Field label="Designation">
          <input type="text" value={form.designation}
            onChange={(e) => setForm({ ...form, designation: e.target.value })} />
        </Field>
      </div>
      <div className="grid-2">
        <Field label="Department">
          <select value={form.department_id}
            onChange={(e) => setForm({ ...form, department_id: e.target.value })}>
            <option value="">Not specified</option>
            {departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
          </select>
        </Field>
        <Field label="Job role">
          <select value={form.job_role_id}
            onChange={(e) => setForm({ ...form, job_role_id: e.target.value })}>
            <option value="">Not specified</option>
            {roles.map((r) => <option key={r.id} value={r.id}>{r.title}</option>)}
          </select>
        </Field>
      </div>
    </Modal>
  )
}

function ManageUserModal({
  user, onClose, departments, roles, onSaved, push,
}: {
  user: User | null; onClose: () => void
  departments: { id: string; name: string }[]; roles: JobRole[]
  onSaved: () => void; push: (m: string, k?: 'success' | 'error' | 'info') => void
}) {
  const [role, setRole] = useState<Role>('learner')
  const [dept, setDept] = useState('')
  const [jobRole, setJobRole] = useState('')
  const [active, setActive] = useState(true)
  const [busy, setBusy] = useState(false)
  const [ready, setReady] = useState<string | null>(null)

  // Sync local state when a different user is opened.
  if (user && ready !== user.id) {
    setReady(user.id); setRole(user.role); setDept(user.department_id ?? '')
    setJobRole(user.job_role_id ?? ''); setActive(user.is_active)
  }

  async function save() {
    if (!user) return
    setBusy(true)
    try {
      await api.patch(`/admin/users/${user.id}`, {
        role, department_id: dept || null, job_role_id: jobRole || null, is_active: active,
      })
      push('User updated', 'success')
      onSaved()
    } catch (e) {
      push(e instanceof Error ? e.message : 'Could not update user', 'error')
    } finally { setBusy(false) }
  }

  return (
    <Modal open={!!user} onClose={onClose} title={user ? `Manage ${user.full_name}` : ''}
      width={520}
      footer={
        <>
          <button className="btn" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" onClick={save} disabled={busy}>
            {busy ? <span className="spin" /> : null} Save changes
          </button>
        </>
      }>
      {user ? (
        <>
          <p className="small muted" style={{ marginTop: 0 }}>{user.email}</p>
          <Field label="Role" hint="Changing the role immediately revokes the user's existing sessions.">
            <select value={role} onChange={(e) => setRole(e.target.value as Role)}>
              <option value="learner">Learner</option>
              <option value="manager">Training Manager</option>
              <option value="assessor">Competency Assessor</option>
              <option value="admin">Administrator</option>
            </select>
          </Field>
          <div className="grid-2">
            <Field label="Department">
              <select value={dept} onChange={(e) => setDept(e.target.value)}>
                <option value="">Not specified</option>
                {departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
              </select>
            </Field>
            <Field label="Job role" hint="Drives gap analysis.">
              <select value={jobRole} onChange={(e) => setJobRole(e.target.value)}>
                <option value="">Not specified</option>
                {roles.map((r) => <option key={r.id} value={r.id}>{r.title}</option>)}
              </select>
            </Field>
          </div>
          <label className="check" data-checked={active}>
            <input type="checkbox" checked={active} onChange={(e) => setActive(e.target.checked)} />
            <span>
              <b className="small">Account active</b>
              <span className="tiny muted" style={{ display: 'block' }}>
                Deactivating preserves assessment history and the audit trail but blocks sign-in.
              </span>
            </span>
          </label>
        </>
      ) : null}
    </Modal>
  )
}
