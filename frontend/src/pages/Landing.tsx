import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../lib/auth'
import { IconArrow, IconChart, IconChat, IconLadder, IconShield, IconTarget } from '../components/icons'

/** Deterministic 10x10 competency matrix used as the hero figure.
 *  Generated from a fixed seed so it renders identically on every load — no stock imagery. */
function useMatrix() {
  return useMemo(() => {
    const cells: number[] = []
    let s = 7
    for (let i = 0; i < 100; i++) {
      s = (s * 1103515245 + 12345) % 2147483648
      const r = (s / 2147483648)
      // Distribution deliberately skews to low-mid levels with a few gaps highlighted.
      const v = r > 0.93 ? 0 : r > 0.86 ? 5 : r > 0.74 ? 4 : r > 0.56 ? 3 : r > 0.32 ? 2 : 1
      cells.push(v)
    }
    // Mark a coherent band of gaps, as a real gap analysis would show.
    ;[23, 34, 45, 56, 67].forEach((i) => { cells[i] = -1 })
    return cells
  }, [])
}

export default function Landing() {
  const { user } = useAuth()
  const cells = useMatrix()
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <div className="landing">
      <nav className="landing-nav" style={{
        position: 'sticky', top: 0, zIndex: 30,
        background: scrolled ? 'rgba(246,242,233,0.92)' : 'transparent',
        backdropFilter: scrolled ? 'blur(10px)' : undefined,
        transition: 'background 200ms ease',
      }}>
        <div className="mark" aria-hidden>
          <span style={{ position: 'absolute', left: 4, top: 5, fontFamily: 'var(--mono)', fontSize: 9 }}>P</span>
          <i /><i /><i /><i /><i />
        </div>
        <div className="rail-title">
          <b>PRAMANA</b>
          <span>Competency intelligence</span>
        </div>
        <span className="grow" />
        <span className="tag tag-provisional" title="Problem statement owner">
          SIH 26101 · MoSPI
        </span>
        <Link className="btn btn-sm" to="/login">Sign in</Link>
        {user ? <Link className="btn btn-sm btn-primary" to="/app">Open workspace</Link> : null}
      </nav>

      <section className="landing-hero">
        <div>
          <p className="eyebrow" style={{ marginBottom: 14 }}>
            Ministry of Statistics &amp; Programme Implementation
          </p>
          <h1>
            Competency intelligence for <em>India&rsquo;s Official Statistical System</em>
          </h1>
          <p className="landing-lead">
            PRAMANA links role requirements to competency assessments, identifies skill gaps and recommends
            relevant learning. Learners can study uploaded material, attempt quizzes and reassess
            their competencies.
          </p>
          <p className="landing-lead small muted">
            Each competency level records how it was assessed. Answers from the study assistant include
            references to the material used; check those references against the source document.
          </p>

          <div className="row gap-8 mt-20 wrap">
            <Link className="btn btn-primary btn-lg" to="/login">
              Enter the platform <IconArrow size={15} />
            </Link>
            <a className="btn btn-lg" href="#how">How it works</a>
          </div>

          <div className="landing-meta">
            <div><b>32</b><span>Competencies</span></div>
            <div><b>8</b><span>Statistical roles</span></div>
            <div><b>5</b><span>Proficiency levels</span></div>
            <div><b>6</b><span>Item checks</span></div>
          </div>
        </div>

        <div className="hero-figure reg card" style={{ padding: 22 }}>
          <div className="row" style={{ justifyContent: 'space-between', marginBottom: 12 }}>
            <span className="eyebrow">Competency matrix · illustrative</span>
            <span className="mono tiny muted">10 × 10</span>
          </div>
          <div className="matrix" role="img"
            aria-label="A grid illustrating a competency profile: filled cells show assessed proficiency, outlined cells show open gaps.">
            {cells.map((v, i) => (
              <i key={i} data-v={v === -1 ? 'g' : String(v)} />
            ))}
          </div>
          <div className="matrix-caption">
            <span>Domain rows</span>
            <span style={{ color: 'var(--ochre)' }}>◼ open gap</span>
            <span>Proficiency →</span>
          </div>
          <div className="divider" />
          <div className="row gap-12 tiny muted">
            <span className="row gap-4"><IconLadder size={13} /> Discrete 1–5 scale</span>
            <span className="row gap-4"><IconShield size={13} /> Evidence-tagged</span>
          </div>
        </div>
      </section>

      <section className="pillars" id="how">
        <article className="pillar">
          <span className="n">01 / ROLE FIRST</span>
          <h3>Start from the role</h3>
          <p>
            Each statistical job role carries required proficiency levels per competency, with an
            importance weight and criticality flag. Growing the framework updates every pathway.
          </p>
        </article>
        <article className="pillar">
          <span className="n">02 / EXPLAINABLE</span>
          <h3>See why a gap exists</h3>
          <p>
            Gap = required − current. Priority = gap × importance × criticality × confidence. The
            arithmetic is published in the product, so any score can be recomputed by hand.
          </p>
        </article>
        <article className="pillar">
          <span className="n">03 / GROUNDED</span>
          <h3>Answers with provenance</h3>
          <p>
            Document access is checked before retrieval. Citation references are checked against the passages
            returned by the search; this does not replace checking whether a passage supports a claim.
          </p>
        </article>
        <article className="pillar">
          <span className="n">04 / EVIDENCE TAGGED</span>
          <h3>Honest about provenance</h3>
          <p>
            Official, provisional and demonstration content are visually distinct throughout. The
            iGOT and NSSTA adapters report their real connection status, never a simulated one.
          </p>
        </article>
      </section>

      <section style={{ maxWidth: 1240, margin: '0 auto', padding: '0 40px 80px' }}>
        <div className="card reg" style={{ padding: 28 }}>
          <div className="grid-3" style={{ alignItems: 'start' }}>
            <div>
              <h2 style={{ fontSize: 25, marginBottom: 8 }}>The closed loop</h2>
              <p className="small muted" style={{ margin: 0 }}>
                Assessment → gap identification → recommendation → learning → quiz → reassessment.
                Each arrow is a persisted record, not a suggestion.
              </p>
            </div>
            {[
              { icon: <IconTarget size={16} />, t: 'Diagnose', d: 'Self, structured or assessor-reviewed levels with confidence and evidence notes.' },
              { icon: <IconChart size={16} />, t: 'Prioritise', d: 'P1–P4 bands from a documented formula, with prerequisite deferral.' },
              { icon: <IconChat size={16} />, t: 'Learn & verify', d: 'Grounded assistant, generated MCQs, then a reassessment that moves the level.' },
            ].map((s) => (
              <div key={s.t} className="row gap-12" style={{ alignItems: 'flex-start' }}>
                <span style={{
                  color: 'var(--teal)', border: '1px solid var(--rule)', borderRadius: 'var(--r-sm)',
                  padding: 7, display: 'grid', placeItems: 'center', background: 'var(--card)',
                }}>{s.icon}</span>
                <div>
                  <b className="small">{s.t}</b>
                  <p className="tiny muted" style={{ margin: '2px 0 0' }}>{s.d}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <footer style={{
        borderTop: '1px solid var(--rule)', padding: '22px 40px',
        display: 'flex', flexWrap: 'wrap', gap: 14, alignItems: 'center',
        maxWidth: 1240, margin: '0 auto',
      }}>
        <span className="tiny muted">
          PRAMANA prototype · SIH 26101 (MoSPI) · competency framework is provisional pending expert validation
        </span>
        <span className="grow" />
        <span className="tag tag-neutral">Not an official government platform</span>
      </footer>
    </div>
  )
}
