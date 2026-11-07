/** Typed API client. Single place where auth, errors and refresh are handled. */

export type Role = 'learner' | 'admin' | 'manager' | 'assessor'
export type EvidenceStatus = 'official' | 'provisional' | 'demonstration'

export interface User {
  id: string
  email: string
  full_name: string
  role: Role
  designation: string | null
  department_id: string | null
  department_name: string | null
  job_role_id: string | null
  job_role_title: string | null
  is_active: boolean
  last_login_at: string | null
  created_at: string
}

export class ApiError extends Error {
  status: number
  errors?: { field: string; message: string }[]
  constructor(status: number, message: string, errors?: { field: string; message: string }[]) {
    super(message)
    this.status = status
    this.errors = errors
  }
}

function csrfSafeHeaders(): Record<string, string> {
  return { 'Content-Type': 'application/json' }
}

let onUnauthorized: (() => void) | null = null
export function setUnauthorizedHandler(fn: () => void) {
  onUnauthorized = fn
}

let refreshPromise: Promise<boolean> | null = null

async function tryRefresh(): Promise<boolean> {
  // Collapse concurrent refreshes into one request.
  if (!refreshPromise) {
    refreshPromise = (async () => {
      try {
        const res = await fetch('/api/auth/refresh', { method: 'POST', credentials: 'include' })
        return res.ok
      } catch {
        return false
      } finally {
        setTimeout(() => { refreshPromise = null }, 0)
      }
    })()
  }
  return refreshPromise
}

async function request<T>(
  path: string,
  init: RequestInit = {},
  retryOn401 = true,
): Promise<T> {
  const res = await fetch(`/api${path}`, {
    ...init,
    credentials: 'include',
    headers: { ...csrfSafeHeaders(), ...(init.headers || {}) },
  })

  if (res.status === 401 && retryOn401) {
    const refreshed = await tryRefresh()
    if (refreshed) return request<T>(path, init, false)
    onUnauthorized?.()
  }

  if (res.status === 204) return undefined as T

  const text = await res.text()
  let body: any = null
  if (text) {
    try { body = JSON.parse(text) } catch { body = null }
  }

  if (!res.ok) {
    const message =
      (body && typeof body.detail === 'string' && body.detail) ||
      (res.status === 403 ? 'You do not have permission to do that.' :
       res.status === 404 ? 'Not found.' :
       res.status === 429 ? 'Too many requests. Please wait a moment.' :
       res.status >= 500 ? 'The server could not complete that request.' :
       'Request failed.')
    throw new ApiError(res.status, message, body?.errors)
  }
  return body as T
}

export const api = {
  get: <T>(p: string) => request<T>(p),
  post: <T>(p: string, body?: unknown) =>
    request<T>(p, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) }),
  patch: <T>(p: string, body?: unknown) =>
    request<T>(p, { method: 'PATCH', body: body === undefined ? undefined : JSON.stringify(body) }),
  put: <T>(p: string, body?: unknown) =>
    request<T>(p, { method: 'PUT', body: body === undefined ? undefined : JSON.stringify(body) }),
  del: <T>(p: string) => request<T>(p, { method: 'DELETE' }),
  upload: async <T>(p: string, form: FormData): Promise<T> => {
    const res = await fetch(`/api${p}`, { method: 'POST', body: form, credentials: 'include' })
    const text = await res.text()
    let body: any = null
    if (text) { try { body = JSON.parse(text) } catch { body = null } }
    if (!res.ok) {
      throw new ApiError(res.status, body?.detail || 'Upload failed')
    }
    return body as T
  },
}

/* ------------------------------------------------------------------ domain types */

export interface Framework { id: string; label: string; notes: string | null; evidence_status: EvidenceStatus; is_active: boolean; created_at: string }
export interface Level { level: number; label: string; summary: string; criteria: string[]; evidence_status: EvidenceStatus }
export interface Domain { id: string; code: string; name: string; description: string | null; kind: string; evidence_status: EvidenceStatus; competency_count: number }
export interface Skill { id: string; statement: string }
export interface Competency {
  id: string; code: string; name: string; description: string | null; rationale: string | null
  evidence_status: EvidenceStatus; review_status: string; source_ref: string | null
  domain_id: string; domain_name: string | null; domain_code: string | null; skills: Skill[]
}
export interface Requirement {
  competency_id: string; competency_code: string; competency_name: string; domain_name: string
  required_level: number; importance: number; is_critical: boolean; rationale: string | null
  evidence_status: EvidenceStatus
}
export interface JobRole {
  id: string; code: string; title: string; description: string | null; cadre: string | null
  grade: string | null; evidence_status: EvidenceStatus; review_status: string
  requirement_count: number; requirements: Requirement[]
}

export interface GapItem {
  competency_id: string; competency_code: string; competency_name: string
  domain_name: string; domain_code: string
  current_level: number; current_level_source: string; target_level: number
  deficit: number; severity: 'none' | 'low' | 'moderate' | 'high' | 'critical'
  importance: number; is_critical: boolean
  priority_score: number; priority_band: 'P1' | 'P2' | 'P3' | 'P4'
  explanation: string; prerequisite_blocked: boolean; evidence_status: EvidenceStatus
}
export interface GapAnalysis {
  user_id: string; job_role_id: string | null; job_role_title: string | null
  framework_label: string; method_note: string; computed_at: string
  total_required: number; met_count: number; gap_count: number; critical_gap_count: number
  overall_readiness_percent: number; items: GapItem[]; missing_assessment: boolean
}

export interface Course {
  id: string; code: string; title: string; summary: string | null; provider: string
  provider_url: string | null; level: string; duration_minutes: number; language: string
  tags: string[]; objectives: string[]; prerequisites: string[]
  evidence_status: EvidenceStatus; is_archived: boolean
  competency_ids: string[]; competency_names: string[]
}
export interface Material {
  id: string; title: string; kind: string; description: string | null
  duration_minutes: number; sort_order: number; external_url: string | null
}
export interface Enrolment {
  id: string; course_id: string; status: string; progress_percent: number
  completed_material_ids: string[]; started_at: string; completed_at: string | null
  course_title: string | null
}
export interface CourseDetail extends Course {
  description: string | null; materials: Material[]; enrolment: Enrolment | null
}

export interface Recommendation {
  kind: 'course' | 'quiz' | 'review' | 'assessment'
  ref_id: string | null; title: string; subtitle: string | null; score: number
  reasons: string[]; competency_code: string | null; competency_name: string | null
  target_level: number | null; current_level: number | null
  duration_minutes: number | null; provider: string | null
  evidence_status: EvidenceStatus | null
}

export interface PlanItem {
  id: string; competency_id: string; competency_code: string | null
  competency_name: string | null; course_id: string | null; course_title: string | null
  activity_type: string; title: string; detail: string | null; target_level: number
  estimated_minutes: number; priority: number; sort_order: number; status: string
  completed_at: string | null
}
export interface Plan {
  id: string; title: string; rationale: string | null; generated_at: string
  is_active: boolean; version: number; items: PlanItem[]
  total_minutes: number; completed_items: number
}

export interface Doc {
  id: string; title: string; original_filename: string; mime_type: string
  size_bytes: number; visibility: string; status: 'queued' | 'processing' | 'completed' | 'failed'
  error_code: string | null; error_detail: string | null; page_count: number; char_count: number; chunk_count: number
  embedding_model: string | null; processed_at: string | null; created_at: string
  owner_id: string; owner_name: string | null; course_id: string | null; topic_hint: string | null
}
export interface ChunkPreview {
  ordinal: number; page_from: number; page_to: number; section: string | null
  preview: string; has_embedding: boolean
}
export interface Citation {
  document_id: string; document_title: string; chunk_id: string
  page_from: number; page_to: number; section: string | null
  snippet: string; similarity: number
}
export interface AskResponse {
  answer: string; grounded: boolean; mode: 'llm' | 'extractive' | 'refused'
  citations: Citation[]; insufficient_evidence: boolean
  noanswer_reason: string | null; latency_ms: number | null
}

export interface QuizQuestion {
  id: string; stem: string; options: { text: string; index: number }[]
  correct_index: number; explanation: string; source_page: number | null
  source_quote: string | null; source_document_id: string | null
  difficulty: string; question_type: string; validation_state: string
  validation_notes: string[]; sort_order: number
}
export interface Quiz {
  id: string; title: string; description: string | null; status: string
  difficulty: string; generation_mode: string; pass_percent: number
  time_limit_minutes: number; source_document_id: string | null; created_at: string
  question_count: number; best_score: number | null; attempt_count: number
}
export interface QuizDetail extends Quiz { questions: QuizQuestion[]; can_manage: boolean }

export interface RenderedQuestion {
  question_id: string; stem: string
  options: { index: number; text: string }[]
  difficulty: string; source_page: number | null
}
export interface AttemptPayload {
  attempt_id: string; quiz_id: string; title: string
  time_limit_minutes: number; pass_percent: number; questions: RenderedQuestion[]
}
export interface AttemptAnswer {
  question_id: string; stem: string; options: { text: string; index: number }[]
  correct_index: number; selected_index: number | null; is_correct: boolean
  explanation: string; source_page: number | null; source_quote: string | null
}
export interface AttemptResult {
  id: string; quiz_id: string; quiz_title: string
  score_correct: number; score_total: number; score_percent: number
  passed: boolean; submitted_at: string | null; answers: AttemptAnswer[]
}

export interface Dashboard {
  readiness_percent: number; gap_count: number; critical_gap_count: number
  assessed_competencies: number; total_required: number
  active_courses: number; completed_courses: number
  quiz_attempts: number; quiz_average: number | null
  plan_items: number; plan_completed: number; plan_minutes_remaining: number
  assessment_history: { date: string; method: string; status: string }[]
  top_gaps: { competency_code: string; competency_name: string; current_level: number; target_level: number; severity: string; priority_band: string }[]
  missing_assessment: boolean
  recommendations: Recommendation[]
  unread_notifications: number
}

export interface ManagerAnalytics {
  scope: string; as_of: string; headcount_considered: number; assessed_learners: number
  suppression_applied: boolean; suppression_threshold: number
  average_readiness_percent: number | null; critical_gap_learners: number | null
  domain_gaps: { domain_code: string; domain_name: string; competency_count: number; average_deficit: number | null; learners_with_gap: number | null }[]
  course_completion: { course: string; enrolled: number; completed: number; average_progress: number | null; suppressed: boolean }[]
  assessment_outcomes: { method: string; count: number; suppressed: boolean }[]
  quiz_performance: { quiz: string; attempts: number; average_score: number | null; suppressed: boolean }[]
}

export interface Integration {
  provider: string; status: string; configured: boolean; base_url_host: string | null
  http_status: number | null; latency_ms: number | null; detail: string | null
  checked_at: string | null; capabilities: string[]; notes: string
}

export interface AdminOverview {
  users_by_role: Record<string, number>; active_users: number
  documents_by_status: Record<string, number>; courses_total: number
  quizzes_total: number; attempts_total: number; ai_calls_24h: number
  ai_error_rate_24h: number | null; integrations: Integration[]; audit_events_24h: number
}

export interface AuditEvent {
  id: string; actor_id: string | null; actor_role: string | null; action: string
  resource_type: string | null; resource_id: string | null; outcome: string
  detail: string | null; created_at: string
}
