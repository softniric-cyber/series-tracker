import type { SeriesSearchResult } from '../api/types'

export default function SeriesCard({ series }: { series: SeriesSearchResult }) {
  const year = series.first_air_date ? series.first_air_date.slice(0, 4) : null
  const rating =
    series.vote_average != null && series.vote_average > 0 ? series.vote_average.toFixed(1) : null

  return (
    <article className="overflow-hidden rounded-xl border border-neutral-200 bg-white dark:border-neutral-800 dark:bg-neutral-900">
      <div className="aspect-[2/3] w-full bg-neutral-100 dark:bg-neutral-800">
        {series.poster_url ? (
          <img
            src={series.poster_url}
            alt={series.name}
            loading="lazy"
            className="h-full w-full object-cover"
          />
        ) : (
          <div className="flex h-full items-center justify-center text-xs text-neutral-400">
            Sin póster
          </div>
        )}
      </div>
      <div className="p-3">
        <h3 className="truncate text-sm font-semibold" title={series.name}>
          {series.name}
        </h3>
        <div className="mt-1 flex items-center gap-2 text-xs text-neutral-500">
          {year && <span>{year}</span>}
          {rating && <span>★ {rating}</span>}
        </div>
      </div>
    </article>
  )
}
