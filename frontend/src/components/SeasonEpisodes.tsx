import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getSeason } from '../api/series'
import {
  markEpisodeWatched,
  markSeasonWatched,
  unmarkEpisodeWatched,
  unmarkSeasonWatched,
} from '../api/me'
import type { EpisodeSummary } from '../api/types'

function formatDate(iso: string | null): string {
  if (!iso) return 'Sin fecha'
  const parsed = new Date(iso)
  if (Number.isNaN(parsed.getTime())) return iso
  return parsed.toLocaleDateString('es-ES', { day: 'numeric', month: 'short', year: 'numeric' })
}

function EpisodeRow({
  episode,
  seriesId,
  following,
}: {
  episode: EpisodeSummary
  seriesId: number
  following: boolean
}) {
  const queryClient = useQueryClient()
  const mutation = useMutation({
    mutationFn: () =>
      episode.watched ? unmarkEpisodeWatched(episode.tmdb_id) : markEpisodeWatched(episode.tmdb_id),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['season', seriesId, episode.season_number] }),
        queryClient.invalidateQueries({ queryKey: ['progress', seriesId] }),
      ])
    },
  })

  return (
    <li className="flex items-center gap-3 px-4 py-2.5">
      {following && (
        <input
          type="checkbox"
          checked={episode.watched}
          disabled={mutation.isPending}
          onChange={() => mutation.mutate()}
          aria-label={`Marcar visto: ${episode.name ?? `Episodio ${episode.episode_number}`}`}
          className="h-4 w-4 shrink-0 accent-brand-600"
        />
      )}
      <span className="w-6 shrink-0 text-right text-sm font-semibold text-neutral-400 tabular-nums">
        {episode.episode_number}
      </span>
      <span
        className={`min-w-0 flex-1 truncate text-sm ${episode.watched ? 'text-neutral-400 line-through' : ''}`}
        title={episode.name ?? undefined}
      >
        {episode.name ?? 'Sin título'}
      </span>
      <span className="shrink-0 text-xs text-neutral-500">{formatDate(episode.air_date)}</span>
    </li>
  )
}

// Se monta solo al desplegar la temporada → la petición de episodios es perezosa
// y TanStack Query la cachea (aprovecha la caché por temporada del backend, S2-1).
export default function SeasonEpisodes({
  seriesId,
  seasonNumber,
  following,
}: {
  seriesId: number
  seasonNumber: number
  following: boolean
}) {
  const queryClient = useQueryClient()
  const { data, isPending, isError } = useQuery({
    queryKey: ['season', seriesId, seasonNumber],
    queryFn: () => getSeason(seriesId, seasonNumber),
  })

  const seasonMutation = useMutation({
    mutationFn: (allWatched: boolean) =>
      allWatched
        ? unmarkSeasonWatched(seriesId, seasonNumber)
        : markSeasonWatched(seriesId, seasonNumber),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['season', seriesId, seasonNumber] }),
        queryClient.invalidateQueries({ queryKey: ['progress', seriesId] }),
      ])
    },
  })

  if (isPending) {
    return <p className="px-4 py-3 text-sm text-neutral-500">Cargando episodios…</p>
  }
  if (isError) {
    return <p className="px-4 py-3 text-sm text-red-600">No se pudieron cargar los episodios.</p>
  }
  if (data.episodes.length === 0) {
    return <p className="px-4 py-3 text-sm text-neutral-500">Sin episodios.</p>
  }

  const allWatched = data.episodes.every((ep) => ep.watched)

  return (
    <div>
      {following && (
        <div className="flex justify-end border-b border-neutral-200 px-4 py-2 dark:border-neutral-800">
          <button
            type="button"
            onClick={() => seasonMutation.mutate(allWatched)}
            disabled={seasonMutation.isPending}
            className="text-xs font-medium text-brand-600 transition hover:text-brand-700 disabled:opacity-60"
          >
            {allWatched ? 'Desmarcar temporada' : 'Marcar temporada como vista'}
          </button>
        </div>
      )}
      <ul className="divide-y divide-neutral-200 dark:divide-neutral-800">
        {data.episodes.map((ep) => (
          <EpisodeRow key={ep.tmdb_id} episode={ep} seriesId={seriesId} following={following} />
        ))}
      </ul>
    </div>
  )
}
