import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getMySeries } from '../api/me'
import type { FollowedCategory, FollowedSeries } from '../api/types'
import Skeleton from '../components/Skeleton'

// Bloques en el orden pedido: En curso, Sin comenzar, Al día, Finalizadas.
const SECTIONS: { category: FollowedCategory; title: string; hint: string }[] = [
  { category: 'watching', title: 'En curso', hint: 'Tienes episodios emitidos por ver.' },
  { category: 'not_started', title: 'Sin comenzar', hint: 'Aún no has empezado a verlas.' },
  { category: 'up_to_date', title: 'Al día', hint: 'Al corriente; llegarán nuevos episodios.' },
  { category: 'finished', title: 'Finalizadas', hint: 'Vistas al completo y sin más temporadas.' },
]

function FollowedCard({ series }: { series: FollowedSeries }) {
  const showProgress = series.aired_episodes > 0
  return (
    <Link
      to={`/series/${series.tmdb_id}`}
      className="group block overflow-hidden rounded-xl border border-neutral-200 bg-white transition hover:border-brand-500 hover:shadow-md dark:border-neutral-800 dark:bg-neutral-900 dark:hover:border-brand-500"
    >
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
          {showProgress && (
            <span>
              {series.watched_episodes}/{series.aired_episodes} vistos
            </span>
          )}
          {series.my_rating != null && (
            <span className="ml-auto shrink-0 text-amber-500" title={`Tu nota: ${series.my_rating}/5`}>
              <span aria-hidden>{'★'.repeat(series.my_rating)}</span>
              <span className="sr-only">Tu nota: {series.my_rating} de 5</span>
            </span>
          )}
        </div>
      </div>
    </Link>
  )
}

export default function MySeriesPage() {
  const { data, isPending, isError } = useQuery({
    queryKey: ['mySeries'],
    queryFn: getMySeries,
  })

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Mis series</h1>
        <p className="mt-1 text-neutral-500">Las series que sigues, organizadas por estado.</p>
      </div>

      {isPending && (
        <section className="space-y-3" role="status">
          <span className="sr-only">Cargando tus series…</span>
          <Skeleton className="h-6 w-28" />
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
            {[0, 1, 2, 3, 4].map((i) => (
              <div key={i} className="overflow-hidden rounded-xl border border-neutral-200 dark:border-neutral-800">
                <Skeleton className="aspect-[2/3] w-full rounded-none" />
                <div className="space-y-2 p-3">
                  <Skeleton className="h-4 w-3/4" />
                  <Skeleton className="h-3 w-1/2" />
                </div>
              </div>
            ))}
          </div>
        </section>
      )}
      {isError && (
        <p className="text-sm text-red-600">No se pudieron cargar tus series. Inténtalo de nuevo.</p>
      )}
      {data && data.length === 0 && (
        <p className="text-sm text-neutral-500">
          Aún no sigues ninguna serie.{' '}
          <Link to="/search" className="text-brand-600 hover:underline">
            Busca una para empezar.
          </Link>
        </p>
      )}
      {data &&
        data.length > 0 &&
        SECTIONS.map(({ category, title, hint }) => {
          const series = data.filter((s) => s.category === category)
          if (series.length === 0) return null
          return (
            <section key={category} className="space-y-3">
              <div>
                <h2 className="text-lg font-semibold tracking-tight">
                  {title}{' '}
                  <span className="text-sm font-normal text-neutral-400">({series.length})</span>
                </h2>
                <p className="text-xs text-neutral-500">{hint}</p>
              </div>
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
                {series.map((s) => (
                  <FollowedCard key={s.tmdb_id} series={s} />
                ))}
              </div>
            </section>
          )
        })}
    </div>
  )
}
