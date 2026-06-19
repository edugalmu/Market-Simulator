type MetricCardProps = {
  label: string
  value: string
  tone?: 'neutral' | 'accent'
}

export function MetricCard({ label, value, tone = 'neutral' }: MetricCardProps) {
  return (
    <article className={`metric-card metric-card--${tone}`}>
      <span className="metric-card__label">{label}</span>
      <strong className="metric-card__value">{value}</strong>
    </article>
  )
}
