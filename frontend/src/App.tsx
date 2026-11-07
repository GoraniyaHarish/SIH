import { Suspense, lazy } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import Shell from './components/Shell'
import { Spinner } from './components/ui'
import { useAuth } from './lib/auth'

const Landing = lazy(() => import('./pages/Landing'))
const Login = lazy(() => import('./pages/Login'))
const Dashboard = lazy(() => import('./pages/Dashboard'))
const Profile = lazy(() => import('./pages/Profile'))
const Assessment = lazy(() => import('./pages/Assessment'))
const Gaps = lazy(() => import('./pages/Gaps'))
const Courses = lazy(() => import('./pages/Courses'))
const CourseDetail = lazy(() => import('./pages/CourseDetail'))
const Plan = lazy(() => import('./pages/Plan'))
const Assistant = lazy(() => import('./pages/Assistant'))
const Documents = lazy(() => import('./pages/Documents'))
const Quizzes = lazy(() => import('./pages/Quizzes'))
const Analytics = lazy(() => import('./pages/Analytics'))
const Admin = lazy(() => import('./pages/Admin'))
const AdminUsers = lazy(() => import('./pages/AdminUsers'))
const AdminFramework = lazy(() => import('./pages/AdminFramework'))
const AdminIntegrations = lazy(() => import('./pages/AdminIntegrations'))
const Settings = lazy(() => import('./pages/Settings'))

function Guard({ children }: { children: JSX.Element }) {
  const { user, loading } = useAuth()
  if (loading) return <div style={{ padding: 60 }}><Spinner label="Restoring session…" /></div>
  if (!user) return <Navigate to="/login" replace />
  return children
}

function StaffOnly({ children }: { children: JSX.Element }) {
  const { can } = useAuth()
  if (!can('staff')) return <Navigate to="/app" replace />
  return children
}

function AdminOnly({ children }: { children: JSX.Element }) {
  const { can } = useAuth()
  if (!can('admin')) return <Navigate to="/app" replace />
  return children
}

export default function App() {
  return (
    <Suspense fallback={<div style={{ padding: 60 }}><Spinner /></div>}>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/app" element={<Guard><Shell /></Guard>}>
          <Route index element={<Dashboard />} />
          <Route path="profile" element={<Profile />} />
          <Route path="assessment" element={<Assessment />} />
          <Route path="gaps" element={<Gaps />} />
          <Route path="courses" element={<Courses />} />
          <Route path="courses/:courseId" element={<CourseDetail />} />
          <Route path="plan" element={<Plan />} />
          <Route path="assistant" element={<Assistant />} />
          <Route path="documents" element={<Documents />} />
          <Route path="quizzes" element={<Quizzes />} />
          <Route path="quizzes/:quizId" element={<Quizzes />} />
          <Route path="analytics" element={<StaffOnly><Analytics /></StaffOnly>} />
          <Route path="admin" element={<AdminOnly><Admin /></AdminOnly>} />
          <Route path="admin/users" element={<AdminOnly><AdminUsers /></AdminOnly>} />
          <Route path="admin/framework" element={<AdminOnly><AdminFramework /></AdminOnly>} />
          <Route path="admin/integrations" element={<AdminOnly><AdminIntegrations /></AdminOnly>} />
          <Route path="settings" element={<Settings />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  )
}
