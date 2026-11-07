import { useEffect, useState } from 'react'
import { api, type JobRole, type User } from '../lib/api'
import { useAuth } from '../lib/auth'
import {
  Banner, Card, ErrorState, Field, Skeleton, Tag, useFetch, useToast, formatDateTime,
} from '../components/ui'
import { IconBell, IconLock, IconUser } from '../components/icons'

interface Notification {
  id: string; kind: string; title: string; body: string | null
  link: string | null; read_at: string | null; created_at: string
}

export default function Settings() {
  const { user, refreshUser } = useAuth()
  const { push } = useToast()
  const roles = useFetch<JobRole[]>(() => api.get<JobRole[]>('/framework/job-roles'))
  const notifications = useFetch<Notification[]>(() => api.get<Notification[]>('/me/notifications'))

  const [fullName, setFullName] = useState(user?.full_name ?? '')
  const [designation, setDesignation] = useState(user?.designation ?? '')
  const [jobRoleId, setJobRoleId] = useState(user?.job_role_id ?? '')
  const [savingProfile, setSavingProfile] = useState(false)

  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [savingPassword, setSavingPassword] = useState(false)
  const [passwordError, setPasswordError] = useState<string | null>(null)

  useEffect(() => {
    if (user) {
      setFullName(user.full_name)
      setDesignation(user.designation ?? '')
      setJobRoleId(user.job_role_id ?? '')
    }
  }, [user])

  async function saveProfile() {
    setSavingProfile(true)
    try {
      await api.patch<User>('/auth/me', {
        full_name: fullName.trim(),
        designation: designation.trim() || null,
        job_role_id: jobRoleId || null,
      })
      await refreshUser()
      push('Profile updated', 'success')
    } catch (e) {
      push(e instanceof Error ? e.message : 'Could not update profile', 'error')
    } finally { setSavingProfile(false) }
  }

  async function changePassword() {
    setPasswordError(null)
    if (newPassword !== confirmPassword) {
      setPasswordError('The two new passwords do not match.')
      return
    }
    setSavingPassword(true)
    try {
      await api.post('/auth/change-password', { current_password: currentPassword, new_password: newPassword })
      push('Password changed. All other sessions were signed out.', 'success')
      setCurrentPassword(''); setNewPassword(''); setConfirmPassword('')
    } catch (e) {
      setPasswordError(e instanceof Error ? e.message : 'Could not change the password')
    } finally { setSavingPassword(false) }
  }

  async function markRead(id: string) {
    try {
      await api.post(`/me/notifications/${id}/read`)
      notifications.refetch()
    } catch { /* non-critical */ }
  }

  if (!user) return null

  return (
    <div className="stack gap-20">
      <div>
        <h2 className="display" style={{ fontSize: 26 }}>Profile &amp; settings</h2>
        <p className="small muted" style={{ margin: '4px 0 0' }}>
          Your job role determines the required proficiency levels used in gap analysis.
        </p>
      </div>

      <div className="split">
        <div className="stack gap-20">
          <Card title={<><IconUser size={13} /> Identity</>}>
            <div className="grid-2">
              <Field label="Full name"><input type="text" value={fullName}
                onChange={(e) => setFullName(e.target.value)} /></Field>
              <Field label="Email" hint="Email changes require administrator action.">
                <input type="text" value={user.email} disabled />
              </Field>
            </div>
            <div className="grid-2">
              <Field label="Designation"><input type="text" value={designation}
                onChange={(e) => setDesignation(e.target.value)} placeholder="e.g. Statistical Officer" /></Field>
              <Field label="Job role" hint="Drives your gap analysis and learning pathway.">
                <select value={jobRoleId} onChange={(e) => setJobRoleId(e.target.value)}>
                  <option value="">Not specified</option>
                  {roles.data?.map((r) => <option key={r.id} value={r.id}>{r.title}</option>)}
                </select>
              </Field>
            </div>
            <div className="row gap-8">
              <button className="btn btn-primary" onClick={saveProfile} disabled={savingProfile}>
                {savingProfile ? <span className="spin" /> : null} Save changes
              </button>
              <span className="tiny muted">
                Role: <Tag tone={user.role === 'admin' ? 'critical' : 'neutral'}>{user.role}</Tag>
              </span>
            </div>
            <div className="divider" />
            <div className="row gap-16 wrap tiny muted">
              <span>Department: <b>{user.department_name ?? '—'}</b></span>
              <span>Joined: <b>{formatDateTime(user.created_at)}</b></span>
              <span>Last sign-in: <b>{user.last_login_at ? formatDateTime(user.last_login_at) : '—'}</b></span>
            </div>
          </Card>

          <Card title={<><IconLock size={13} /> Change password</>}>
            {passwordError ? <div className="mb-12"><Banner kind="bad">{passwordError}</Banner></div> : null}
            <Field label="Current password">
              <input type="password" value={currentPassword} autoComplete="current-password"
                onChange={(e) => setCurrentPassword(e.target.value)} />
            </Field>
            <div className="grid-2">
              <Field label="New password" hint="At least 10 characters with upper, lower and a digit.">
                <input type="password" value={newPassword} autoComplete="new-password"
                  onChange={(e) => setNewPassword(e.target.value)} />
              </Field>
              <Field label="Confirm new password">
                <input type="password" value={confirmPassword} autoComplete="new-password"
                  onChange={(e) => setConfirmPassword(e.target.value)} />
              </Field>
            </div>
            <button className="btn" onClick={changePassword}
              disabled={savingPassword || !currentPassword || newPassword.length < 10}>
              {savingPassword ? <span className="spin" /> : null} Change password
            </button>
            <p className="tiny muted mt-8" style={{ marginBottom: 0 }}>
              Changing your password revokes every existing session, including this one.
            </p>
          </Card>
        </div>

        <div className="stack gap-20">
          <Card title={<><IconBell size={13} /> Notifications</>}
            actions={<span className="tiny muted">
              {notifications.data?.filter((n) => !n.read_at).length ?? 0} unread
            </span>}>
            {notifications.loading ? <Skeleton h={90} /> :
            notifications.error ? <ErrorState error={notifications.error} onRetry={notifications.refetch} /> :
            (notifications.data?.length ?? 0) === 0 ? (
              <p className="small muted" style={{ margin: 0 }}>Nothing yet.</p>
            ) : (
              <div className="stack gap-8">
                {notifications.data!.map((n) => (
                  <div key={n.id} style={{
                    padding: '9px 11px', border: '1px solid var(--rule)', borderRadius: 'var(--r)',
                    background: n.read_at ? 'transparent' : 'var(--teal-wash)',
                  }}>
                    <div className="row gap-8">
                      <b className="tiny grow">{n.title}</b>
                      {!n.read_at ? (
                        <button className="btn btn-sm btn-ghost" onClick={() => markRead(n.id)}>mark read</button>
                      ) : null}
                    </div>
                    {n.body ? <p className="tiny muted" style={{ margin: '3px 0 0' }}>{n.body}</p> : null}
                    <div className="tiny muted mono" style={{ marginTop: 3 }}>{formatDateTime(n.created_at)}</div>
                  </div>
                ))}
              </div>
            )}
          </Card>

          <Card title="Session & data">
            <p className="tiny muted" style={{ marginTop: 0 }}>
              Access tokens last {user ? '15' : '15'} minutes and refresh automatically. Signing out
              revokes the refresh-token family. Your assessments and documents are visible only to
              you, your assessor, and administrators.
            </p>
            <div className="divider" />
            <p className="tiny muted" style={{ margin: 0 }}>
              <b>Data retention.</b> Deleting a document removes its passages and the stored file
              immediately. Deleting a course with enrolments archives it instead, so your learning
              history is preserved.
            </p>
          </Card>
        </div>
      </div>
    </div>
  )
}
