import { useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api, type Competency, type Course } from '../lib/api'
import {
  Banner, Card, EmptyState, ErrorState, EvidenceTag, Skeleton, useFetch, formatDuration,
} from '../components/ui'
import { IconBook, IconSearch } from '../components/icons'

export default function Courses() {
  const [params, setParams] = useSearchParams()
  const competencyCode = params.get('competency') ?? ''
  const [q, setQ] = useState('')
  const [level, setLevel] = useState('')
  const [sort, setSort] = useState<'title' | 'shortest' | 'provider'>('title')

  const competencies = useFetch<Competency[]>(() => api.get<Competency[]>('/framework/competencies'))
  const matched = competencies.data?.find((c) => c.code === competencyCode)

  const courses = useFetch<Course[]>(
    () => {
      const qs = new URLSearchParams()
      if (q.trim()) qs.set('q', q.trim())
      if (level) qs.set('level', level)
      if (matched) qs.set('competency_id', matched.id)
      qs.set('limit', '60')
      return api.get<Course[]>(`/courses?${qs.toString()}`)
    },
    [q, level, matched?.id],
  )

  const sorted = useMemo(() => {
    const list = [...(courses.data ?? [])]
    if (sort === 'shortest') list.sort((a, b) => a.duration_minutes - b.duration_minutes)
    else if (sort === 'provider') list.sort((a, b) => a.provider.localeCompare(b.provider))
    else list.sort((a, b) => a.title.localeCompare(b.title))
    return list
  }, [courses.data, sort])

  return (
    <div className="stack gap-20">
      <div>
        <h2 className="display" style={{ fontSize: 26 }}>Course catalogue</h2>
        <p className="small muted" style={{ margin: '4px 0 0' }}>
          {courses.data?.length ?? 0} courses, each mapped to the competencies it develops.
        </p>
      </div>

      {matched ? (
        <Banner kind="info">
          Filtered to material for <b>{matched.code} · {matched.name}</b>.{' '}
          <button className="btn btn-sm btn-ghost" onClick={() => setParams({})}>Clear filter</button>
        </Banner>
      ) : null}

      <Banner kind="warn">
        <b>Catalogue content is demonstration data.</b> These courses are illustrative records
        created for this prototype. They are not real iGOT Karmayogi or NSSTA courses, and no
        provider URL is shown where a real one could not be verified.
      </Banner>

      <div className="toolbar">
        <div className="row gap-8" style={{ position: 'relative', flex: '1 1 240px' }}>
          <IconSearch size={15} />
          <input type="search" placeholder="Search title, provider or summary…" value={q}
            onChange={(e) => setQ(e.target.value)} aria-label="Search courses"
            style={{ maxWidth: 360 }} />
        </div>
        <select value={level} onChange={(e) => setLevel(e.target.value)} aria-label="Level">
          <option value="">All levels</option>
          <option value="foundation">Foundation</option>
          <option value="intermediate">Intermediate</option>
          <option value="advanced">Advanced</option>
        </select>
        <select value={sort} onChange={(e) => setSort(e.target.value as typeof sort)} aria-label="Sort">
          <option value="title">Sort: title</option>
          <option value="shortest">Sort: shortest first</option>
          <option value="provider">Sort: provider</option>
        </select>
        <span className="grow" />
        <span className="tiny muted mono">{sorted.length} shown</span>
      </div>

      {courses.loading ? (
        <div className="grid-3">
          {[0, 1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="card card-pad"><Skeleton h={18} w="70%" /><Skeleton h={11} /><Skeleton h={11} w="60%" /></div>
          ))}
        </div>
      ) : courses.error ? (
        <ErrorState error={courses.error} onRetry={courses.refetch} />
      ) : sorted.length === 0 ? (
        <Card>
          <EmptyState title="No courses match" icon={<IconBook size={26} />}
            action={<button className="btn btn-sm" onClick={() => { setQ(''); setLevel(''); setParams({}) }}>
              Clear all filters
            </button>}>
            {q || level || matched
              ? 'Try a broader search, or clear the filters.'
              : 'The catalogue is empty. An administrator can add courses from the admin workspace.'}
          </EmptyState>
        </Card>
      ) : (
        <div className="grid-3">
          {sorted.map((course) => (
            <Link key={course.id} to={`/app/courses/${course.id}`}
              style={{ textDecoration: 'none', color: 'inherit' }}>
              <article className="course-card">
                <div className="row gap-8 wrap">
                  <span className="tag tag-neutral" style={{ fontSize: 9.5, textTransform: 'uppercase' }}>
                    {course.level}
                  </span>
                  <EvidenceTag status={course.evidence_status} compact />
                  <span className="grow" />
                  <span className="mono tiny muted">{formatDuration(course.duration_minutes)}</span>
                </div>
                <h3>{course.title}</h3>
                <p className="tiny muted" style={{ margin: 0, flex: 1 }}>{course.summary}</p>
                <div className="row gap-6 wrap">
                  {course.competency_names.slice(0, 3).map((name) => (
                    <span key={name} className="tag tag-neutral" style={{ fontSize: 9.5 }}>{name}</span>
                  ))}
                  {course.competency_names.length > 3 ? (
                    <span className="tiny muted">+{course.competency_names.length - 3}</span>
                  ) : null}
                </div>
                <div className="row gap-8" style={{ borderTop: '1px solid var(--rule)', paddingTop: 9 }}>
                  <span className="tiny muted" style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {course.provider}
                  </span>
                  <span className="grow" />
                  <span className="tiny mono" style={{ color: 'var(--teal)' }}>open →</span>
                </div>
              </article>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
