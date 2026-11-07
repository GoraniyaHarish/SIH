import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import { useAuth } from '../lib/auth'
import {
  IconBell, IconBook, IconChart, IconChat, IconDoc, IconGauge, IconGrid, IconLadder,
  IconLock, IconMenu, IconPlug, IconQuiz, IconRoute, IconShield, IconTarget, IconUser,
  IconUsers, IconX,
} from './icons'

interface NavEntry { to: string; label: string; icon: JSX.Element }

const LEARNER_NAV: { group: string; items: NavEntry[] }[] = [
  {
    group: 'Overview',
    items: [
      { to: '/app', label: 'Dashboard', icon: <IconGauge /> },
      { to: '/app/profile', label: 'Competency profile', icon: <IconLadder /> },
      { to: '/app/gaps', label: 'Skill-gap analysis', icon: <IconTarget /> },
    ],
  },
  {
    group: 'Develop',
    items: [
      { to: '/app/plan', label: 'Learning plan', icon: <IconRoute /> },
      { to: '/app/courses', label: 'Course catalogue', icon: <IconBook /> },
      { to: '/app/assistant', label: 'Study assistant', icon: <IconChat /> },
      { to: '/app/quizzes', label: 'Assessments', icon: <IconQuiz /> },
    ],
  },
  {
    group: 'Evidence',
    items: [
      { to: '/app/assessment', label: 'Take assessment', icon: <IconLadder /> },
      { to: '/app/documents', label: 'Learning material', icon: <IconDoc /> },
      { to: '/app/settings', label: 'Profile & settings', icon: <IconUser /> },
    ],
  },
]

const STAFF_NAV: NavEntry = { to: '/app/analytics', label: 'Training intelligence', icon: <IconChart /> }

const ADMIN_NAV: { group: string; items: NavEntry[] }[] = [
  {
    group: 'Administration',
    items: [
      { to: '/app/admin', label: 'Admin workspace', icon: <IconGrid /> },
      { to: '/app/admin/users', label: 'People & roles', icon: <IconUsers /> },
      { to: '/app/admin/framework', label: 'Competency framework', icon: <IconShield /> },
      { to: '/app/admin/integrations', label: 'Integrations & system', icon: <IconPlug /> },
    ],
  },
]

export default function Shell() {
  const { user, logout, can } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [open, setOpen] = useState(false)
  const [unread, setUnread] = useState(0)

  useEffect(() => { setOpen(false) }, [location.pathname])

  useEffect(() => {
    if (!user) return
    api.get<{ unread_notifications: number }>('/me/dashboard')
      .then((d) => setUnread(d.unread_notifications))
      .catch(() => setUnread(0))
  }, [user, location.pathname])

  if (!user) return null

  const initials = user.full_name.split(' ').slice(0, 2).map((p) => p[0]).join('').toUpperCase()

  return (
    <div className="shell" data-collapsed="false">
      <aside className="rail" data-open={open} aria-label="Primary navigation">
        <div className="rail-head">
          <div className="mark" aria-hidden>
            <span style={{ position: 'absolute', left: 4, top: 5, fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--paper)' }}>P</span>
            <i /><i /><i /><i /><i />
          </div>
          <div className="rail-title">
            <b>PRAMANA</b>
            <span>Competency intelligence</span>
          </div>
        </div>

        <nav className="rail-nav">
          {LEARNER_NAV.map((group) => (
            <div className="rail-group" key={group.group}>
              <p>{group.group}</p>
              {group.items.map((item) => (
                <NavLink key={item.to} to={item.to} end={item.to === '/app'}
                  className="nav-item">
                  {item.icon}
                  <span>{item.label}</span>
                </NavLink>
              ))}
            </div>
          ))}

          {can('staff') ? (
            <div className="rail-group">
              <p>Insight</p>
              <NavLink to={STAFF_NAV.to} className="nav-item">
                {STAFF_NAV.icon}
                <span>{STAFF_NAV.label}</span>
              </NavLink>
            </div>
          ) : null}

          {can('admin') ? (
            ADMIN_NAV.map((group) => (
              <div className="rail-group" key={group.group}>
                <p>{group.group}</p>
                {group.items.map((item) => (
                  <NavLink key={item.to} to={item.to} className="nav-item">
                    {item.icon}
                    <span>{item.label}</span>
                  </NavLink>
                ))}
              </div>
            ))
          ) : null}
        </nav>

        <div className="rail-foot">
          <div className="who">
            <div className="av">{initials}</div>
            <div>
              <b title={user.full_name}>{user.full_name}</b>
              <span>{user.role}{user.department_name ? ` · ${user.department_name}` : ''}</span>
            </div>
          </div>
          <button className="btn btn-sm btn-ghost" style={{ justifyContent: 'flex-start' }}
            onClick={async () => { await logout(); navigate('/login') }}>
            <IconLock size={14} /> Sign out
          </button>
        </div>
      </aside>

      <div className="main">
        <header className="topbar">
          <button className="btn btn-ghost btn-sm mobile-only" aria-label="Toggle navigation"
            onClick={() => setOpen((v) => !v)}>
            {open ? <IconX size={17} /> : <IconMenu size={17} />}
          </button>
          <div>
            <div className="eyebrow">SIH 26101 · MoSPI · Official Statistical System</div>
            <h1>{titleFor(location.pathname)}</h1>
          </div>
          <span className="spacer" />
          <NavLink to="/app/settings" className="btn btn-sm btn-ghost" aria-label="Notifications">
            <IconBell size={15} />
            {unread > 0 ? (
              <span style={{
                fontFamily: 'var(--mono)', fontSize: 10, background: 'var(--ochre)',
                color: '#fff', borderRadius: 99, padding: '0 5px',
              }}>{unread}</span>
            ) : null}
          </NavLink>
        </header>
        <main className="page">
          <Outlet />
        </main>
      </div>

      {open ? (
        <div onClick={() => setOpen(false)} aria-hidden
          style={{ position: 'fixed', inset: 0, background: 'rgba(26,33,48,0.28)', zIndex: 50 }} />
      ) : null}
    </div>
  )
}

function titleFor(path: string): string {
  const map: [string, string][] = [
    ['/app/admin/users', 'People & roles'],
    ['/app/admin/framework', 'Competency framework'],
    ['/app/admin/integrations', 'Integrations & system'],
    ['/app/admin', 'Admin workspace'],
    ['/app/analytics', 'Training intelligence'],
    ['/app/profile', 'Competency profile'],
    ['/app/gaps', 'Skill-gap analysis'],
    ['/app/plan', 'Learning plan'],
    ['/app/courses/', 'Course'],
    ['/app/courses', 'Course catalogue'],
    ['/app/assistant', 'Study assistant'],
    ['/app/quizzes/', 'Assessment'],
    ['/app/quizzes', 'Assessments'],
    ['/app/documents', 'Learning material'],
    ['/app/assessment', 'Competency assessment'],
    ['/app/settings', 'Profile & settings'],
    ['/app', 'Dashboard'],
  ]
  for (const [prefix, title] of map) if (path.startsWith(prefix)) return title
  return 'PRAMANA'
}
