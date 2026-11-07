import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import {
  api, type AttemptPayload, type AttemptResult, type Doc, type Quiz, type QuizDetail,
} from '../lib/api'
import { useAuth } from '../lib/auth'
import {
  Banner, Card, EmptyState, ErrorState, Skeleton, useFetch, useToast,
  formatDate,
} from '../components/ui'
import { IconCheck, IconQuiz, IconSpark, IconTrash, IconX } from '../components/icons'

type Mode = 'list' | 'take' | 'result' | 'review'

export default function Quizzes() {
  const { quizId } = useParams()
  const [params] = useSearchParams()
  const docId = params.get('doc')
  const { can } = useAuth()
  const { push } = useToast()
  const navigate = useNavigate()

  const [mode, setMode] = useState<Mode>('list')
  const [attempt, setAttempt] = useState<AttemptPayload | null>(null)
  const [result, setResult] = useState<AttemptResult | null>(null)
  const [review, setReview] = useState<QuizDetail | null>(null)
  const [busy, setBusy] = useState(false)

  const quizzes = useFetch<Quiz[]>(() => api.get<Quiz[]>('/quizzes?limit=60'))
  const docs = useFetch<Doc[]>(() => api.get<Doc[]>('/documents?limit=60'))
  const attempts = useFetch<{ id: string; quiz_id: string; quiz_title: string; score_percent: number; passed: boolean; submitted_at: string }[]>(
    () => api.get('/me/attempts'),
  )

  const readyDocs = (docs.data ?? []).filter((d) => d.status === 'completed')

  // Deep link: /app/quizzes/:id starts an attempt
  useEffect(() => {
    if (!quizId) { setMode('list'); return }
    let cancelled = false
    ;(async () => {
      setBusy(true)
      try {
        const detail = await api.get<QuizDetail>(`/quizzes/${quizId}`)
        if (cancelled) return
        if (detail.status !== 'published') {
          setReview(detail); setMode('review')
        } else {
          const payload = await api.post<AttemptPayload>(`/quizzes/${quizId}/attempts`)
          if (!cancelled) { setAttempt(payload); setMode('take') }
        }
      } catch (e) {
        push(e instanceof Error ? e.message : 'Could not open the assessment', 'error')
        navigate('/app/quizzes')
      } finally {
        if (!cancelled) setBusy(false)
      }
    })()
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [quizId])

  async function generate(documentId: string, count: number, difficulty: string) {
    setBusy(true)
    try {
      const detail = await api.post<QuizDetail>('/quizzes/generate', {
        document_id: documentId, question_count: count, difficulty,
      })
      push(`${detail.questions.length} questions generated and validated`, 'success')
      quizzes.refetch()
      setReview(detail)
      setMode('review')
      navigate('/app/quizzes')
    } catch (e) {
      push(e instanceof Error ? e.message : 'Generation failed', 'error')
    } finally {
      setBusy(false)
    }
  }

  if (mode === 'take' && attempt) {
    return <TakeQuiz payload={attempt} onDone={(r) => { setResult(r); setMode('result'); setAttempt(null) }} />
  }
  if (mode === 'result' && result) {
    return <QuizResult result={result} onClose={() => { setMode('list'); setResult(null); quizzes.refetch(); attempts.refetch() }} />
  }

  return (
    <div className="stack gap-20">
      <div className="row gap-12 wrap" style={{ alignItems: 'flex-end' }}>
        <div className="grow">
          <h2 className="display" style={{ fontSize: 26 }}>Assessments</h2>
          <p className="small muted" style={{ margin: '4px 0 0' }}>
            Every question is generated from a passage in the material, validated before publishing,
            and cites the page it came from.
          </p>
        </div>
      </div>

      {can('staff') ? <GeneratePanel docs={readyDocs} busy={busy} onGenerate={generate} presetDocId={docId} /> : null}

      {review ? (
        <ReviewPanel quiz={review} onClose={() => setReview(null)}
          onPublished={() => { setReview(null); quizzes.refetch() }} />
      ) : null}

      <div className="split">
        <Card title={`Published assessments (${(quizzes.data ?? []).filter((q) => q.status === 'published').length})`}>
          {quizzes.loading ? <Skeleton h={120} /> :
          quizzes.error ? <ErrorState error={quizzes.error} onRetry={quizzes.refetch} /> :
          (quizzes.data ?? []).length === 0 ? (
            <EmptyState title="No assessments yet" icon={<IconQuiz size={26} />}>
              {can('staff')
                ? 'Generate one from a processed document using the panel opposite.'
                : 'A training manager or administrator must generate and publish an assessment before you can attempt one.'}
            </EmptyState>
          ) : (
            <div className="stack gap-8">
              {quizzes.data!
                .filter((q) => q.status === 'published' || can('staff'))
                .map((q) => (
                  <div key={q.id} className="doc-row">
                    <div className="doc-ico" style={{ background: 'var(--teal-wash)', color: 'var(--teal-deep)' }}>
                      {q.question_count}Q
                    </div>
                    <div className="grow" style={{ minWidth: 0 }}>
                      <div className="row gap-8 wrap">
                        <b className="small">{q.title}</b>
                        <span className={`tag ${q.status === 'published' ? 'tag-official' : q.status === 'draft' ? 'tag-provisional' : 'tag-pending'}`}
                          style={{ fontSize: 9.5 }}>{q.status}</span>
                        <span className="tag tag-neutral" style={{ fontSize: 9.5 }}>{q.difficulty}</span>
                      </div>
                      <div className="tiny muted">
                        {q.question_count} questions · pass {q.pass_percent}%
                        {q.best_score !== null ? ` · your best ${q.best_score.toFixed(0)}%` : ''}
                        {q.attempt_count ? ` · ${q.attempt_count} attempt${q.attempt_count === 1 ? '' : 's'}` : ''}
                      </div>
                    </div>
                    <div className="row gap-6">
                      {can('staff') && q.status !== 'published' ? (
                        <button className="btn btn-sm" onClick={async () => {
                          const d = await api.get<QuizDetail>(`/quizzes/${q.id}`)
                          setReview(d)
                        }}>Review</button>
                      ) : null}
                      {q.status === 'published' ? (
                        <button className="btn btn-sm btn-primary" onClick={() => navigate(`/app/quizzes/${q.id}`)}>
                          Start
                        </button>
                      ) : null}
                    </div>
                  </div>
                ))}
            </div>
          )}
        </Card>

        <Card title="Your attempts">
          {attempts.loading ? <Skeleton h={80} /> : (attempts.data ?? []).length === 0 ? (
            <p className="small muted" style={{ margin: 0 }}>No attempts submitted yet.</p>
          ) : (
            <table className="ledger">
              <thead><tr><th>Assessment</th><th className="num">Score</th><th>Result</th></tr></thead>
              <tbody>
                {attempts.data!.slice(0, 10).map((a) => (
                  <tr key={a.id}>
                    <td>
                      <b className="tiny">{a.quiz_title}</b>
                      <div className="tiny muted">{formatDate(a.submitted_at)}</div>
                    </td>
                    <td className="num tiny">{a.score_percent.toFixed(0)}%</td>
                    <td>
                      <span className={`tag ${a.passed ? 'tag-official' : 'tag-critical'}`} style={{ fontSize: 9.5 }}>
                        {a.passed ? 'passed' : 'not passed'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      </div>
    </div>
  )
}

function GeneratePanel({
  docs, busy, onGenerate, presetDocId,
}: { docs: Doc[]; busy: boolean; onGenerate: (id: string, n: number, d: string) => void; presetDocId: string | null }) {
  const [docId, setDocId] = useState(presetDocId ?? docs[0]?.id ?? '')
  const [count, setCount] = useState(5)
  const [difficulty, setDifficulty] = useState('medium')
  useEffect(() => { if (!docId && docs[0]) setDocId(docs[0].id) }, [docs, docId])

  return (
    <Card title="Generate an assessment" reg>
      {docs.length === 0 ? (
        <EmptyState title="No processed documents" icon={<IconSpark size={22} />}>
          Upload and index a document first; questions are generated only from its actual text.
        </EmptyState>
      ) : (
        <div className="grid-3" style={{ alignItems: 'end' }}>
          <label className="field" style={{ margin: 0 }}>
            <span className="small" style={{ fontWeight: 600 }}>Source document</span>
            <select value={docId} onChange={(e) => setDocId(e.target.value)}>
              {docs.map((d) => <option key={d.id} value={d.id}>{d.title}</option>)}
            </select>
          </label>
          <label className="field" style={{ margin: 0 }}>
            <span className="small" style={{ fontWeight: 600 }}>Questions</span>
            <select value={count} onChange={(e) => setCount(Number(e.target.value))}>
              {[3, 5, 8, 10, 15].map((n) => <option key={n} value={n}>{n}</option>)}
            </select>
          </label>
          <label className="field" style={{ margin: 0 }}>
            <span className="small" style={{ fontWeight: 600 }}>Difficulty</span>
            <div className="row gap-8">
              <select value={difficulty} onChange={(e) => setDifficulty(e.target.value)}>
                <option value="easy">Easy</option>
                <option value="medium">Medium</option>
                <option value="hard">Hard</option>
              </select>
              <button className="btn btn-primary" disabled={busy || !docId}
                onClick={() => onGenerate(docId, count, difficulty)}>
                {busy ? <span className="spin" /> : <IconSpark size={14} />} Generate
              </button>
            </div>
          </label>
        </div>
      )}
    </Card>
  )
}

function ReviewPanel({ quiz, onClose, onPublished }: { quiz: QuizDetail; onClose: () => void; onPublished: () => void }) {
  const { push } = useToast()
  const [busy, setBusy] = useState(false)
  const [items, setItems] = useState(quiz.questions)

  async function publish() {
    setBusy(true)
    try {
      await api.post(`/quizzes/${quiz.id}/publish`, {})
      push('Assessment published — learners can now attempt it', 'success')
      onPublished()
    } catch (e) {
      push(e instanceof Error ? e.message : 'Could not publish', 'error')
    } finally { setBusy(false) }
  }

  async function remove(questionId: string) {
    try {
      await api.del(`/quizzes/${quiz.id}/questions/${questionId}`)
      setItems((prev) => prev.filter((q) => q.id !== questionId))
      push('Question removed', 'success')
    } catch (e) {
      push(e instanceof Error ? e.message : 'Cannot remove', 'error')
    }
  }

  return (
    <Card
      title={`Review: ${quiz.title}`}
      actions={
        <div className="row gap-8">
          <span className="tag tag-neutral" style={{ fontSize: 9.5 }}>{quiz.generation_mode.replace('_', ' ')}</span>
          <button className="btn btn-sm btn-ghost" onClick={onClose}><IconX size={13} /></button>
        </div>
      }>
      <Banner kind={quiz.generation_mode === 'extractive_fallback' ? 'warn' : 'info'}>
        {quiz.generation_mode === 'extractive_fallback'
          ? 'These items were built by the deterministic fallback generator (cloze deletion from source sentences) because the AI provider was unavailable. Review them before publishing.'
          : 'Items were generated by the language model and passed the six validation checks: structure, duplicate options, source grounding, answer support, ambiguity and cross-question duplication.'}
      </Banner>

      <div className="stack gap-12 mt-16">
        {items.map((q, i) => (
          <div key={q.id} className="q-block">
            <div className="row gap-8 wrap mb-8">
              <span className="mono tiny muted">Q{i + 1}</span>
              <span className="tag tag-neutral" style={{ fontSize: 9.5 }}>{q.difficulty}</span>
              {q.source_page ? <span className="tag tag-neutral" style={{ fontSize: 9.5 }}>p.{q.source_page}</span> : null}
              <span className="grow" />
              <button className="btn btn-sm btn-ghost" onClick={() => remove(q.id)} aria-label="Remove question">
                <IconTrash size={12} />
              </button>
            </div>
            <p className="small" style={{ margin: '0 0 8px', fontWeight: 600 }}>{q.stem}</p>
            <div className="stack gap-4">
              {q.options.map((o, oi) => (
                <div key={oi} className="opt" data-state={oi === q.correct_index ? 'correct' : undefined}
                  style={{ cursor: 'default' }}>
                  <span className="l">{String.fromCharCode(65 + oi)}</span>
                  <span>{o.text}</span>
                  {oi === q.correct_index ? <span style={{ marginLeft: 'auto' }}><IconCheck size={13} /></span> : null}
                </div>
              ))}
            </div>
            <p className="tiny muted" style={{ margin: '8px 0 0' }}>
              <b>Explanation: </b>{q.explanation}
            </p>
            {q.source_quote ? (
              <span className="cite">
                <b>Source passage</b>
                <span style={{ display: 'block', fontStyle: 'italic', marginTop: 3 }}>“{q.source_quote}”</span>
              </span>
            ) : null}
          </div>
        ))}
      </div>

      <div className="row gap-8 mt-16" style={{ justifyContent: 'flex-end' }}>
        <button className="btn" onClick={onClose}>Keep as draft</button>
        <button className="btn btn-primary" onClick={publish} disabled={busy || items.length === 0}>
          {busy ? <span className="spin" /> : <IconCheck size={14} />} Publish {items.length} questions
        </button>
      </div>
    </Card>
  )
}

function TakeQuiz({ payload, onDone }: { payload: AttemptPayload; onDone: (r: AttemptResult) => void }) {
  const [answers, setAnswers] = useState<Record<string, number>>({})
  const [busy, setBusy] = useState(false)
  const { push } = useToast()
  const answered = Object.keys(answers).length

  async function submit() {
    setBusy(true)
    try {
      const res = await api.post<AttemptResult>(`/attempts/${payload.attempt_id}/submit`, { answers })
      onDone(res)
    } catch (e) {
      push(e instanceof Error ? e.message : 'Could not submit', 'error')
    } finally { setBusy(false) }
  }

  return (
    <div className="stack gap-20">
      <div className="row gap-12 wrap">
        <div className="grow">
          <h2 className="display" style={{ fontSize: 26 }}>{payload.title}</h2>
          <p className="small muted" style={{ margin: '4px 0 0' }}>
            {payload.questions.length} questions · pass mark {payload.pass_percent}% · options are
            shuffled for this attempt
          </p>
        </div>
        <span className="mono small">{answered}/{payload.questions.length} answered</span>
      </div>

      {payload.questions.map((q, i) => (
        <div key={q.question_id} className="q-block">
          <div className="row gap-8 mb-8">
            <span className="mono tiny muted">Q{i + 1}</span>
            <span className="tag tag-neutral" style={{ fontSize: 9.5 }}>{q.difficulty}</span>
          </div>
          <p className="small" style={{ margin: '0 0 10px', fontWeight: 600 }}>{q.stem}</p>
          <div className="stack gap-4">
            {q.options.map((o) => (
              <button key={o.index} className="opt" aria-pressed={answers[q.question_id] === o.index}
                onClick={() => setAnswers((p) => ({ ...p, [q.question_id]: o.index }))}>
                <span className="l">{String.fromCharCode(65 + o.index)}</span>
                <span>{o.text}</span>
              </button>
            ))}
          </div>
        </div>
      ))}

      <div className="card card-pad row gap-12" style={{ position: 'sticky', bottom: 12 }}>
        <span className="grow small">
          {answered < payload.questions.length
            ? `${payload.questions.length - answered} left unanswered`
            : 'All questions answered'}
        </span>
        <button className="btn btn-primary btn-lg" onClick={submit} disabled={busy}>
          {busy ? <span className="spin" /> : <IconCheck size={15} />} Submit attempt
        </button>
      </div>
    </div>
  )
}

function QuizResult({ result, onClose }: { result: AttemptResult; onClose: () => void }) {
  return (
    <div className="stack gap-20">
      <div className="row gap-12 wrap">
        <div className="grow">
          <h2 className="display" style={{ fontSize: 26 }}>{result.quiz_title}</h2>
          <p className="small muted" style={{ margin: '4px 0 0' }}>
            {result.score_correct} of {result.score_total} correct
          </p>
        </div>
        <Link className="btn" to="/app/gaps">Review gaps</Link>
        <button className="btn btn-primary" onClick={onClose}>Back to assessments</button>
      </div>

      <div className="stats">
        <div className="stat" data-tone={result.passed ? 'good' : 'bad'}>
          <div className="k">Score</div>
          <div className="v">{result.score_percent.toFixed(0)}<small>%</small></div>
          <div className="d">{result.passed ? 'Passed' : 'Not passed'}</div>
        </div>
        <div className="stat"><div className="k">Correct</div><div className="v">{result.score_correct}</div></div>
        <div className="stat"><div className="k">Total</div><div className="v">{result.score_total}</div></div>
      </div>

      {result.answers.map((a, i) => (
        <div key={a.question_id} className="q-block">
          <div className="row gap-8 mb-8">
            <span className="mono tiny muted">Q{i + 1}</span>
            <span className={`tag ${a.is_correct ? 'tag-official' : 'tag-critical'}`} style={{ fontSize: 9.5 }}>
              {a.is_correct ? 'correct' : 'incorrect'}
            </span>
            {a.source_page ? <span className="tag tag-neutral" style={{ fontSize: 9.5 }}>p.{a.source_page}</span> : null}
          </div>
          <p className="small" style={{ margin: '0 0 10px', fontWeight: 600 }}>{a.stem}</p>
          <div className="stack gap-4">
            {a.options.map((o, oi) => {
              const state = oi === a.correct_index ? 'correct' : oi === a.selected_index ? 'wrong' : undefined
              return (
                <div key={oi} className="opt" data-state={state} style={{ cursor: 'default' }}>
                  <span className="l">{String.fromCharCode(65 + oi)}</span>
                  <span>{o.text}</span>
                </div>
              )
            })}
          </div>
          <p className="tiny muted" style={{ margin: '9px 0 0' }}><b>Why: </b>{a.explanation}</p>
          {a.source_quote ? (
            <span className="cite"><b>Source</b>
              <span style={{ display: 'block', fontStyle: 'italic', marginTop: 3 }}>“{a.source_quote}”</span>
            </span>
          ) : null}
        </div>
      ))}
    </div>
  )
}
