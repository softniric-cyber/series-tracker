import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getSeason } from '../api/series'
import {
  markEpisodeWatched,
  markSeasonWatched,
  unmarkEpisodeWatched,
  unmarkSeasonWatched,
} from '../api/me'
import type { EpisodeSummary, SeasonDetail, SeriesProgress } from '../api/types'

type QueryClient = ReturnType<typeof useQueryClient>

const clamp = (n: number, min: number, max: number): number => Math.min(Math.max(n, min), max)

// Un episodio cuenta para el progreso si es de una temporada normal y ya se emitió
// (misma semántica que el backend: season>=1 y air_date<=hoy).
function countsForProgress(ep: EpisodeSummary): boolean {
  return (
    ep.season_number >= 1 && ep.air_date != null && ep.air_date <= new Date().toISOString().slice(0, 10)
  )
}

// Reescribe la caché de la temporada aplicando `watched` a los episodios elegidos.
// Base de la actualización optimista: el check se refleja al instante, sin esperar
// al round-trip del backend ni al refetch posterior.
function patchSeasonCache(
  queryClient: QueryClient,
  seasonKey: readonly unknown[],
  watched: boolean,
  shouldPatch: (ep: EpisodeSummary) => boolean,
): SeasonDetail | undefined {
  const previous = queryClient.getQueryData<SeasonDetail>(seasonKey)
  queryClient.setQueryData<SeasonDetail>(seasonKey, (old) =>
    old
      ? { ...old, episodes: old.episodes.map((ep) => (shouldPatch(ep) ? { ...ep, watched } : ep)) }
      : old,
  )
  return previous
}

// Ajuste optimista de la barra/porcentaje de progreso: mueve el total visto y el
// conteo de la temporada afectada. `next_episode` y los distintivos finos se
// reconcilian con el refetch de onSettled (recalcularlos aquí replicaría toda la
// lógica del backend a través de todas las temporadas).
function patchProgressCache(
  queryClient: QueryClient,
  progressKey: readonly unknown[],
  seasonNumber: number,
  deltaWatched: number,
): SeriesProgress | undefined {
  const previous = queryClient.getQueryData<SeriesProgress>(progressKey)
  if (deltaWatched === 0) return previous
  queryClient.setQueryData<SeriesProgress>(progressKey, (old) => {
    if (!old) return old
    return {
      ...old,
      watched_episodes: clamp(old.watched_episodes + deltaWatched, 0, old.total_episodes),
      seasons: (old.seasons ?? []).map((s) => {
        if (s.season_number !== seasonNumber) return s
        const watched = clamp(s.watched + deltaWatched, 0, s.aired)
        return { ...s, watched, completed: s.aired > 0 && watched >= s.aired }
      }),
    }
  })
  return previous
}

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
  const seasonKey = ['season', seriesId, episode.season_number] as const
  const progressKey = ['progress', seriesId] as const
  const mutation = useMutation({
    mutationFn: () =>
      episode.watched ? unmarkEpisodeWatched(episode.tmdb_id) : markEpisodeWatched(episode.tmdb_id),
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: seasonKey })
      await queryClient.cancelQueries({ queryKey: progressKey })
      const previousSeason = patchSeasonCache(
        queryClient,
        seasonKey,
        !episode.watched,
        (ep) => ep.tmdb_id === episode.tmdb_id,
      )
      const delta = countsForProgress(episode) ? (episode.watched ? -1 : 1) : 0
      const previousProgress = patchProgressCache(
        queryClient,
        progressKey,
        episode.season_number,
        delta,
      )
      return { previousSeason, previousProgress }
    },
    onError: (_err, _vars, context) => {
      if (context?.previousSeason) queryClient.setQueryData(seasonKey, context.previousSeason)
      if (context?.previousProgress) queryClient.setQueryData(progressKey, context.previousProgress)
    },
    onSettled: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: seasonKey }),
        queryClient.invalidateQueries({ queryKey: progressKey }),
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

  const seasonKey = ['season', seriesId, seasonNumber] as const
  const progressKey = ['progress', seriesId] as const
  const seasonMutation = useMutation({
    mutationFn: (allWatched: boolean) =>
      allWatched
        ? unmarkSeasonWatched(seriesId, seasonNumber)
        : markSeasonWatched(seriesId, seasonNumber),
    onMutate: async (allWatched: boolean) => {
      await queryClient.cancelQueries({ queryKey: seasonKey })
      await queryClient.cancelQueries({ queryKey: progressKey })
      // El backend marca/desmarca TODOS los episodios de la temporada.
      const previousSeason = patchSeasonCache(queryClient, seasonKey, !allWatched, () => true)
      // Delta = cuántos episodios que CUENTAN (emitidos, no especiales) cambian de estado.
      const airedNonSpecial = (data?.episodes ?? []).filter(countsForProgress)
      const currentlyWatched = airedNonSpecial.filter((ep) => ep.watched).length
      const target = allWatched ? 0 : airedNonSpecial.length
      const previousProgress = patchProgressCache(
        queryClient,
        progressKey,
        seasonNumber,
        target - currentlyWatched,
      )
      return { previousSeason, previousProgress }
    },
    onError: (_err, _vars, context) => {
      if (context?.previousSeason) queryClient.setQueryData(seasonKey, context.previousSeason)
      if (context?.previousProgress) queryClient.setQueryData(progressKey, context.previousProgress)
    },
    onSettled: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: seasonKey }),
        queryClient.invalidateQueries({ queryKey: progressKey }),
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
