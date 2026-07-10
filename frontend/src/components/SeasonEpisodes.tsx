import { useQuery } from '@tanstack/react-query'
import { getSeason } from '../api/series'

function formatDate(iso: string | null): string {
  if (!iso) return 'Sin fecha'
  const parsed = new Date(iso)
  if (Number.isNaN(parsed.getTime())) return iso
  return parsed.toLocaleDateString('es-ES', { day: 'numeric', month: 'short', year: 'numeric' })
}

// Se monta solo al desplegar la temporada → la petición de episodios es perezosa
// y TanStack Query la cachea (aprovecha la caché por temporada del backend, S2-1).
export default function SeasonEpisodes({
  seriesId,
  seasonNumber,
}: {
  seriesId: number
  seasonNumber: number
}) {
  const { data, isPending, isError } = useQuery({
    queryKey: ['season', seriesId, seasonNumber],
    queryFn: () => getSeason(seriesId, seasonNumber),
  })

  if (isPending) {
    return <p className="px-4 py-3 text-sm text-neutral-500">Cargando episodios…</p>
  }
  if (isError) {
    return (
      <p className="px-4 py-3 text-sm text-red-600">No se pudieron cargar los episodios.</p>
    )
  }
  if (data.episodes.length === 0) {
    return <p className="px-4 py-3 text-sm text-neutral-500">Sin episodios.</p>
  }

  return (
    <ul className="divide-y divide-neutral-200 dark:divide-neutral-800">
      {data.episodes.map((ep) => (
        <li key={ep.tmdb_id} className="flex items-baseline gap-3 px-4 py-2.5">
          <span className="w-8 shrink-0 text-right text-sm font-semibold text-neutral-400 tabular-nums">
            {ep.episode_number}
          </span>
          <span className="min-w-0 flex-1 truncate text-sm" title={ep.name ?? undefined}>
            {ep.name ?? 'Sin título'}
          </span>
          <span className="shrink-0 text-xs text-neutral-500">{formatDate(ep.air_date)}</span>
        </li>
      ))}
    </ul>
  )
}
