import { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api, type AskResponse, type Doc } from '../lib/api'
import {
  Banner, Card, EmptyState, EvidenceTag, Skeleton, useFetch, useToast, formatBytes,
} from '../components/ui'
import { IconArrow, IconChat, IconDoc, IconSpark } from '../components/icons'

interface Turn { question: string; answer: AskResponse }

export default function Assistant() {
  const [params] = useSearchParams()
  const initialDoc = params.get('doc')
  const { push } = useToast()

  const docs = useFetch<Doc[]>(() => api.get<Doc[]>('/documents?limit=60'))
  const [selected, setSelected] = useState<string[]>(initialDoc ? [initialDoc] : [])
  const [question, setQuestion] = useState('')
  const [turns, setTurns] = useState<Turn[]>([])
  const [busy, setBusy] = useState(false)
  const endRef = useRef<HTMLDivElement>(null)

  const ready = (docs.data ?? []).filter((d) => d.status === 'completed')

  useEffect(() => {
    if (initialDoc && selected.length === 0) setSelected([initialDoc])
  }, [initialDoc, selected.length])

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [turns, busy])

  function toggleDoc(id: string) {
    setSelected((prev) => prev.includes(id) ? prev.filter((d) => d !== id) : [...prev, id])
  }

  async function ask(q?: string) {
    const text = (q ?? question).trim()
    if (text.length < 3) { push('Ask a slightly longer question', 'error'); return }
    setBusy(true)
    setQuestion('')
    try {
      const res = await api.post<AskResponse>('/assistant/ask', {
        question: text,
        document_ids: selected,
      })
      setTurns((prev) => [...prev, { question: text, answer: res }])
    } catch (e) {
      push(e instanceof Error ? e.message : 'The assistant could not answer', 'error')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="stack gap-20">
      <div>
        <h2 className="display" style={{ fontSize: 26 }}>Study assistant</h2>
        <p className="small muted" style={{ margin: '4px 0 0' }}>
          Answers use material you are authorised to read. Check the cited pages in the original document
          before relying on an answer.
        </p>
      </div>

      <div className="split-left">
        <div className="stack gap-20">
          <Card title="Sources in scope">
            {docs.loading ? <Skeleton h={80} /> : ready.length === 0 ? (
              <EmptyState title="No processed material" icon={<IconDoc size={22} />}>
                Upload a document on the Learning material page and wait for it to finish indexing.
              </EmptyState>
            ) : (
              <div className="stack gap-6">
                <p className="tiny muted" style={{ margin: '0 0 4px' }}>
                  {selected.length === 0
                    ? 'Searching all material you can access.'
                    : `${selected.length} document${selected.length === 1 ? '' : 's'} selected.`}
                </p>
                {ready.map((d) => (
                  <label key={d.id} className="check" data-checked={selected.includes(d.id)}>
                    <input type="checkbox" checked={selected.includes(d.id)}
                      onChange={() => toggleDoc(d.id)} />
                    <span style={{ minWidth: 0 }}>
                      <b className="tiny" style={{ display: 'block', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {d.title}
                      </b>
                      <span className="tiny muted">
                        {d.page_count}p · {d.chunk_count} chunks · {formatBytes(d.size_bytes)}
                        {d.embedding_model ? '' : ' · keyword only'}
                      </span>
                    </span>
                  </label>
                ))}
                {selected.length ? (
                  <button className="btn btn-sm btn-ghost" onClick={() => setSelected([])}>
                    Clear selection
                  </button>
                ) : null}
              </div>
            )}
          </Card>

          <Card title="Grounding rules">
            <ul className="tiny muted" style={{ margin: 0, paddingLeft: 16, lineHeight: 1.7 }}>
              <li>Retrieval is filtered by your read permissions in the database first.</li>
              <li>Retrieved text is passed to the model as untrusted data, never as instructions.</li>
              <li>Citations that do not map to a retrieved passage are removed.</li>
              <li>The assistant may decline when it cannot retrieve suitable supporting passages.</li>
            </ul>
            <div className="mt-12"><EvidenceTag status="provisional" compact /></div>
          </Card>
        </div>

        <div className="stack gap-16">
          <Card title="Conversation">
            {turns.length === 0 && !busy ? (
              <div className="stack gap-12">
                <EmptyState title="Ask about your material" icon={<IconChat size={26} />}
                  action={
                    <div className="row gap-6 wrap" style={{ justifyContent: 'center' }}>
                      {[
                        'What does the material say about sample size derivation?',
                        'Summarise the quality dimensions it describes.',
                        'What are the common sample design failures?',
                      ].map((s) => (
                        <button key={s} className="btn btn-sm" onClick={() => ask(s)}>{s}</button>
                      ))}
                    </div>
                  }>
                  Choose sources on the left, then ask a question. The assistant will cite the pages
                  it used.
                </EmptyState>
              </div>
            ) : (
              <div className="chat">
                {turns.map((t, i) => (
                  <div key={i} className="stack gap-12">
                    <div className="msg msg-user">
                      <div className="av2">you</div>
                      <div className="bubble">{t.question}</div>
                    </div>
                    <div className="msg msg-ai">
                      <div className="av2"><IconSpark size={12} /></div>
                      <div className="bubble">
                        <div style={{ whiteSpace: 'pre-wrap' }}>{t.answer.answer}</div>
                        {t.answer.citations.map((c, ci) => (
                          <span key={c.chunk_id} className="cite">
                            <b>[S{ci + 1}] {c.document_title}</b>
                            <span className="pg">
                              {c.page_from === c.page_to
                                ? `page ${c.page_from}`
                                : `pages ${c.page_from}–${c.page_to}`}
                              {c.section ? ` · ${c.section}` : ''} · match {(c.similarity * 100).toFixed(0)}%
                            </span>
                            <span style={{ display: 'block', marginTop: 5, fontStyle: 'italic' }}>
                              “{c.snippet}”
                            </span>
                          </span>
                        ))}
                        <div className="row gap-8 mt-8 wrap">
                          <span className={`tag ${t.answer.mode === 'llm' ? 'tag-official' : t.answer.mode === 'extractive' ? 'tag-provisional' : 'tag-critical'}`}
                            style={{ fontSize: 9.5 }}>
                            {t.answer.mode === 'llm' ? 'grounded answer'
                              : t.answer.mode === 'extractive' ? 'verbatim passages' : 'declined'}
                          </span>
                          {t.answer.latency_ms ? (
                            <span className="mono tiny muted">{t.answer.latency_ms} ms</span>
                          ) : null}
                        </div>
                        {t.answer.noanswer_reason ? (
                          <div className="mt-8">
                            <Banner kind={t.answer.insufficient_evidence ? 'warn' : 'info'}>
                              {t.answer.noanswer_reason}
                            </Banner>
                          </div>
                        ) : null}
                      </div>
                    </div>
                  </div>
                ))}
                {busy ? (
                  <div className="msg msg-ai">
                    <div className="av2"><IconSpark size={12} /></div>
                    <div className="bubble row gap-8">
                      <span className="spin" />
                      <span className="small muted">Retrieving passages and checking citations…</span>
                    </div>
                  </div>
                ) : null}
                <div ref={endRef} />
              </div>
            )}
          </Card>

          <div className="card card-pad" style={{ position: 'sticky', bottom: 12 }}>
            <form onSubmit={(e) => { e.preventDefault(); ask() }} className="row gap-8">
              <input type="text" value={question} onChange={(e) => setQuestion(e.target.value)}
                placeholder="Ask a question about the selected material…"
                aria-label="Your question" disabled={busy} />
              <button className="btn btn-primary" type="submit" disabled={busy || question.trim().length < 3}>
                <IconArrow size={15} />
              </button>
            </form>
            <p className="tiny muted" style={{ margin: '7px 0 0' }}>
              Responses are intended to use the selected sources. Verify important details against the cited pages.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
