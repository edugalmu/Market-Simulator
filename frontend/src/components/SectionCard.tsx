import type { PropsWithChildren, ReactNode } from 'react'

type SectionCardProps = PropsWithChildren<{
  title: string
  eyebrow?: string
  aside?: ReactNode
}>

export function SectionCard({ title, eyebrow, aside, children }: SectionCardProps) {
  return (
    <section className="section-card">
      <header className="section-card__header">
        <div>
          {eyebrow ? <p className="section-card__eyebrow">{eyebrow}</p> : null}
          <h2>{title}</h2>
        </div>
        {aside ? <div className="section-card__aside">{aside}</div> : null}
      </header>
      <div className="section-card__body">{children}</div>
    </section>
  )
}
