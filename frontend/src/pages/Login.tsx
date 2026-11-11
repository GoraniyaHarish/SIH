import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, ApiError, type User } from '../lib/api'
import { useAuth } from '../lib/auth'
import { Banner, Field, useToast } from '../components/ui'

export default function Login() {
  const { login, user } = useAuth()
  const navigate = useNavigate()
  const { push } = useToast()

  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [departments, setDepartments] = useState<{ id: string; name: string }[]>([])
  const [jobRoles, setJobRoles] = useState<{ id: string; title: string }[]>([])
  const [departmentId, setDepartmentId] = useState('')
  const [jobRoleId, setJobRoleId] = useState('')

  useEffect(() => { if (user) navigate('/app', { replace: true }) }, [user, navigate])

  useEffect(() => {
    api.get<{ id: string; name: string }[]>('/departments').then(setDepartments).catch(() => setDepartments([]))
    api.get<{ id: string; title: string }[]>('/framework/job-roles').then(setJobRoles).catch(() => setJobRoles([]))
  }, [])

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    setFieldErrors({})
    try {
      if (mode === 'login') {
        const u = await login(email.trim(), password)
        push(`Signed in as ${u.full_name}`, 'success')
        navigate('/app', { replace: true })
      } else {
        const created = await api.post<User>('/auth/register', {
          email: email.trim(),
          full_name: fullName.trim(),
          password,
          department_id: departmentId || null,
          job_role_id: jobRoleId || null,
        })
        push('Account created. Signing you in…', 'success')
        await login(created.email, password)
        navigate('/app', { replace: true })
      }
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message)
        if (err.errors?.length) {
          setFieldErrors(Object.fromEntries(err.errors.map((f) => [f.field, f.message])))
        }
      } else {
        setError('Could not reach the server. Check that the API is running.')
      }
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="auth-wrap">
      <section className="auth-art">
        <div className="rail-title" style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
          <div className="mark" aria-hidden>
            <span style={{ position: 'absolute', left: 4, top: 5, fontFamily: 'var(--mono)', fontSize: 9 }}>P</span>
            <i /><i /><i /><i /><i />
          </div>
          <div>
            <b style={{ fontSize: 18 }}>PRAMANA</b>
            <span>Competency intelligence</span>
          </div>
        </div>

        <div>
          <blockquote>
            &ldquo;Capacity building in official statistics fails quietly when nobody knows which
            competency is actually missing.&rdquo;
          </blockquote>
          <p className="small muted" style={{ maxWidth: '34ch', marginTop: 16 }}>
            PRAMANA makes the missing competency explicit, ranks it against the requirements of a
            real statistical job role, and attaches evidence to every level it reports.
          </p>
        </div>

        <div>
          <div className="auth-note">
            <p className="eyebrow" style={{ marginBottom: 8 }}>Institutional access</p>
            <p className="small muted" style={{ margin: 0 }}>
              Sign in with an account issued by your organisation. Demonstration accounts, when
              enabled for a private evaluation, are provisioned separately and are never published
              with shared credentials.
            </p>
          </div>
        </div>
      </section>

      <section className="auth-form-wrap">
        <div className="auth-form">
          <h2 className="display">{mode === 'login' ? 'Sign in' : 'Create a learner account'}</h2>
          <p className="small muted" style={{ marginTop: 4, marginBottom: 22 }}>
            {mode === 'login'
              ? 'Use your institutional email address.'
              : 'Self-registration creates a learner account. Elevated roles are granted by an administrator.'}
          </p>

          {error ? <div className="mb-16"><Banner kind="bad">{error}</Banner></div> : null}

          <form onSubmit={submit} noValidate>
            {mode === 'register' ? (
              <Field label="Full name" htmlFor="name" error={fieldErrors.full_name}>
                <input id="name" type="text" value={fullName} autoComplete="name"
                  onChange={(e) => setFullName(e.target.value)} required
                  placeholder="e.g. Priya Nair" />
              </Field>
            ) : null}

            <Field label="Email" htmlFor="email" error={fieldErrors.email}>
              <input id="email" type="email" value={email} autoComplete="username"
                onChange={(e) => setEmail(e.target.value)} required
                placeholder="name@pramana.gov.in" />
            </Field>

            <Field
              label="Password"
              htmlFor="password"
              error={fieldErrors.password}
              hint={mode === 'register'
                ? 'At least 10 characters, with upper case, lower case and a digit.'
                : undefined}
            >
              <input id="password" type="password" value={password}
                autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                onChange={(e) => setPassword(e.target.value)} required />
            </Field>

            {mode === 'register' ? (
              <>
                <Field label="Department (optional)" htmlFor="dept">
                  <select id="dept" value={departmentId} onChange={(e) => setDepartmentId(e.target.value)}>
                    <option value="">Not specified</option>
                    {departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
                  </select>
                </Field>
                <Field label="Job role (optional)" htmlFor="role"
                  hint="Your role determines the required proficiency levels used in gap analysis.">
                  <select id="role" value={jobRoleId} onChange={(e) => setJobRoleId(e.target.value)}>
                    <option value="">Not specified</option>
                    {jobRoles.map((r) => <option key={r.id} value={r.id}>{r.title}</option>)}
                  </select>
                </Field>
              </>
            ) : null}

            <button className="btn btn-primary btn-block btn-lg mt-8" type="submit" disabled={busy}>
              {busy ? <span className="spin" /> : null}
              {mode === 'login' ? 'Sign in' : 'Create account and sign in'}
            </button>
          </form>

          <div className="row gap-4 mt-16" style={{ justifyContent: 'center' }}>
            <span className="small muted">
              {mode === 'login' ? 'No account yet?' : 'Already registered?'}
            </span>
            <button className="btn btn-ghost btn-sm" type="button"
              onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError(null); setFieldErrors({}) }}>
              {mode === 'login' ? 'Register as a learner' : 'Sign in instead'}
            </button>
          </div>

          <div className="divider" />
          <p className="tiny muted" style={{ textAlign: 'center' }}>
            <Link to="/">← Back to overview</Link>
          </p>
        </div>
      </section>
    </div>
  )
}
