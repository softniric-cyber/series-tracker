import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getMySeries } from '../api/me'
import type { FollowedSeries } from '../api/types'
import Spinner from '../components/Spinner'

function FollowedCard({ series }: { series: FollowedSeries }) {
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
        {series.status && <p className="mt-1 text-xs text-neutral-500">{series.status}</p>}
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
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Mis series</h1>
        <p className="mt-1 text-neutral-500">Las series que sigues.</p>
      </div>

      {isPending && <Spinner label="Cargando tus series…" />}
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
      {data && data.length > 0 && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
          {data.map((series) => (
            <FollowedCard key={series.tmdb_id} series={series} />
          ))}
        </div>
      )}
    </div>
  )
}
