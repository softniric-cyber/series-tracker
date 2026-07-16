import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getSeriesDetail, getSeriesProviders } from '../api/series'
import { followSeries, getProgress, unfollowSeries } from '../api/me'
import { ApiError } from '../api/client'
import type { SeasonProgress, SeasonSummary, SeriesDetail, SeriesProgress } from '../api/types'
import SeasonEpisodes from '../components/SeasonEpisodes'
import Skeleton from '../components/Skeleton'
import { cardClass } from '../components/ui'

function yearRange(detail: SeriesDetail): string | null {
  const from = detail.first_air_date?.slice(0, 4)
  const to = detail.last_air_date?.slice(0, 4)
  if (!from) return null
  if (!to || to === from) return from
  return `${from}–${to}`
}

function FollowButton({ tmdbId, isFollowing }: { tmdbId: number; isFollowing: boolean }) {
  const queryClient = useQueryClient()
  const seriesKey = ['series', tmdbId] as const
  const mutation = useMutation({
    mutationFn: async () => {
      if (isFollowing) await unfollowSeries(tmdbId)
      else await followSeries(tmdbId)
    },
    // Optimista: el botón cambia al instante (y habilita la query de progreso al
    // seguir); si el PUT/DELETE falla, se revierte con el snapshot previo.
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: seriesKey })
      const previous = queryClient.getQueryData<SeriesDetail>(seriesKey)
      queryClient.setQueryData<SeriesDetail>(seriesKey, (old) =>
        old ? { ...old, is_following: !isFollowing } : old,
      )
      return { previous }
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) queryClient.setQueryData(seriesKey, context.previous)
    },
    onSettled: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: seriesKey }),
        queryClient.invalidateQueries({ queryKey: ['mySeries'] }),
      ])
    },
  })

  return (
    <button
      type="button"
      onClick={() => mutation.mutate()}
      disabled={mutation.isPending}
      aria-pressed={isFollowing}
      className={
        isFollowing
          ? 'inline-flex items-center gap-2 rounded-lg border border-neutral-300 px-4 py-2 text-sm font-semibold text-neutral-700 transition hover:border-red-400 hover:bg-red-50 hover:text-red-600 disabled:opacity-60 dark:border-neutral-700 dark:text-neutral-200 dark:hover:bg-red-950/40'
          : 'inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60'
      }
    >
      {isFollowing ? '✓ Siguiendo' : '+ Seguir'}
    </button>
  )
}

function Progress({ data }: { data: SeriesProgress }) {
  if (data.total_episodes === 0) return null

  const percent = Math.round((data.watched_episodes / data.total_episodes) * 100)
  const next = data.next_episode

  return (
    <section className={cardClass}>
      <div className="flex items-baseline justify-between gap-3">
        <h2 className="text-lg font-semibold">Tu progreso</h2>
        <span className="text-sm text-neutral-500">
          {data.watched_episodes} / {data.total_episodes} · {percent}%
        </span>
      </div>
      <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-neutral-200 dark:bg-neutral-800">
        <div className="h-full rounded-full bg-brand-600 transition-all" style={{ width: `${percent}%` }} />
      </div>
      <p className="mt-3 text-sm text-neutral-600 dark:text-neutral-300">
        {next ? (
          <>
            Siguiente por ver:{' '}
            <span className="font-medium">
              T{next.season_number}·E{next.episode_number}
              {next.name ? ` — ${next.name}` : ''}
            </span>
          </>
        ) : (
          '¡Estás al día! 🎉'
        )}
      </p>
    </section>
  )
}

function WhereToWatch({ tmdbId }: { tmdbId: number }) {
  const { data, isPending, isError } = useQuery({
    queryKey: ['providers', tmdbId],
    queryFn: () => getSeriesProviders(tmdbId),
  })

  return (
    <section className={cardClass}>
      <h2 className="text-lg font-semibold">Dónde verla</h2>
      {isPending && (
        <div className="mt-3 flex gap-4" role="status">
          <span className="sr-only">Cargando proveedores…</span>
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-12 w-12 rounded-xl" />
          ))}
        </div>
      )}
      {isError && (
        <p className="mt-2 text-sm text-red-600">No se pudieron cargar los proveedores.</p>
      )}
      {data && data.flatrate.length === 0 && (
        <p className="mt-2 text-sm text-neutral-500">
          No disponible en streaming en tu país ({data.country}).
        </p>
      )}
      {data && data.flatrate.length > 0 && (
        <ul className="mt-3 flex flex-wrap gap-4">
          {data.flatrate.map((p) => (
            <li key={p.provider_id} className="flex flex-col items-center gap-1.5 text-center">
              {p.logo_url ? (
                <img
                  src={p.logo_url}
                  alt={p.provider_name}
                  loading="lazy"
                  className="h-12 w-12 rounded-xl border border-neutral-200 object-cover dark:border-neutral-700"
                />
              ) : (
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-neutral-100 text-xs text-neutral-400 dark:bg-neutral-800">
                  ?
                </div>
              )}
              <span className="max-w-[5rem] text-xs text-neutral-500">{p.provider_name}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

function SeasonStatus({ progress }: { progress: SeasonProgress }) {
  if (progress.completed) {
    // «Vista» si la temporada emitió por completo; «Al día» si aún le quedan estrenos.
    const label = progress.aired >= progress.episodes ? 'Vista' : 'Al día'
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-xs font-semibold text-green-700 dark:bg-green-500/15 dark:text-green-400">
        ✓ {label}
      </span>
    )
  }
  if (progress.watched > 0) {
    return (
      <span className="text-sm text-neutral-500">
        {progress.watched}/{progress.aired} vistos
      </span>
    )
  }
  return null
}

function SeasonRow({
  seriesId,
  season,
  following,
  progress,
}: {
  seriesId: number
  season: SeasonSummary
  following: boolean
  progress?: SeasonProgress
}) {
  const [open, setOpen] = useState(false)
  // El resumen de progreso reemplaza al conteo de episodios cuando aporta info.
  const showStatus = progress != null && (progress.completed || progress.watched > 0)
  return (
    <div className="overflow-hidden rounded-xl border border-neutral-200 dark:border-neutral-800">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-3 bg-white px-4 py-3 text-left transition hover:bg-neutral-50 dark:bg-neutral-900 dark:hover:bg-neutral-800"
      >
        <span className="flex min-w-0 items-center gap-2">
          <span className="truncate font-medium">
            {season.name ?? `Temporada ${season.season_number}`}
          </span>
          {progress && <SeasonStatus progress={progress} />}
        </span>
        <span className="flex shrink-0 items-center gap-3 text-sm text-neutral-500">
          {!showStatus && season.episode_count != null && <span>{season.episode_count} ep.</span>}
          <span aria-hidden className={open ? 'rotate-180 transition' : 'transition'}>
            ▾
          </span>
        </span>
      </button>
      {open && (
        <div className="border-t border-neutral-200 dark:border-neutral-800">
          <SeasonEpisodes
            seriesId={seriesId}
            seasonNumber={season.season_number}
            following={following}
          />
        </div>
      )}
    </div>
  )
}

// Placeholder de la ficha mientras carga: replica el layout real (póster, título,
// géneros, botón y unas filas de temporada) para evitar el salto al llegar los datos.
function SeriesDetailSkeleton() {
  return (
    <div className="space-y-6" role="status">
      <span className="sr-only">Cargando ficha…</span>
      <header className="flex flex-col gap-5 sm:flex-row">
        <div className="w-40 shrink-0 self-center sm:self-start">
          <Skeleton className="aspect-[2/3] w-full rounded-xl" />
        </div>
        <div className="min-w-0 flex-1 space-y-3">
          <Skeleton className="h-8 w-2/3" />
          <Skeleton className="h-4 w-1/2" />
          <div className="flex gap-2">
            <Skeleton className="h-5 w-16 rounded-full" />
            <Skeleton className="h-5 w-20 rounded-full" />
          </div>
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-5/6" />
          <Skeleton className="h-9 w-32 rounded-lg" />
        </div>
      </header>
      <div className={cardClass}>
        <Skeleton className="h-5 w-32" />
      </div>
      <section className="space-y-2">
        <Skeleton className="h-6 w-28" />
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} className="h-12 w-full rounded-xl" />
        ))}
      </section>
    </div>
  )
}

export default function SeriesDetailPage() {
  const { tmdbId } = useParams<{ tmdbId: string }>()
  const id = Number(tmdbId)

  const { data, isPending, isError, error } = useQuery({
    queryKey: ['series', id],
    queryFn: () => getSeriesDetail(id),
    enabled: Number.isFinite(id),
  })

  // El progreso (que cachea todas las temporadas en el backend) solo se pide si
  // sigues la serie; alimenta tanto la barra como los distintivos por temporada.
  const { data: progress } = useQuery({
    queryKey: ['progress', id],
    queryFn: () => getProgress(id),
    enabled: Number.isFinite(id) && data?.is_following === true,
  })

  if (isPending) return <SeriesDetailSkeleton />

  if (isError) {
    const notFound = error instanceof ApiError && error.status === 404
    return (
      <div className="space-y-3">
        <p className="text-sm text-red-600">
          {notFound ? 'Serie no encontrada.' : 'No se pudo cargar la ficha.'}
        </p>
        <Link to="/search" className="text-sm text-brand-600 hover:underline">
          ← Volver a la búsqueda
        </Link>
      </div>
    )
  }

  const years = yearRange(data)
  // Ocultamos la temporada 0 (especiales) de la lista principal.
  const seasons = data.seasons.filter((s) => s.season_number !== 0)
  const progressBySeason = new Map<number, SeasonProgress>(
    (progress?.seasons ?? []).map((s) => [s.season_number, s]),
  )

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-5 sm:flex-row">
        <div className="w-40 shrink-0 self-center overflow-hidden rounded-xl border border-neutral-200 bg-neutral-100 dark:border-neutral-800 dark:bg-neutral-800 sm:self-start">
          <div className="aspect-[2/3] w-full">
            {data.poster_url ? (
              <img
                src={data.poster_url}
                alt={data.name}
                className="h-full w-full object-cover"
              />
            ) : (
              <div className="flex h-full items-center justify-center text-xs text-neutral-400">
                Sin póster
              </div>
            )}
          </div>
        </div>

        <div className="min-w-0 flex-1 space-y-3">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">{data.name}</h1>
            <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-neutral-500">
              {years && <span>{years}</span>}
              {data.status && <span>{data.status}</span>}
              {data.number_of_seasons != null && (
                <span>
                  {data.number_of_seasons}{' '}
                  {data.number_of_seasons === 1 ? 'temporada' : 'temporadas'}
                </span>
              )}
            </div>
          </div>

          {data.genres.length > 0 && (
            <ul className="flex flex-wrap gap-2">
              {data.genres.map((g) => (
                <li
                  key={g}
                  className="rounded-full bg-brand-50 px-2.5 py-0.5 text-xs font-medium text-brand-700 dark:bg-brand-500/10 dark:text-brand-400"
                >
                  {g}
                </li>
              ))}
            </ul>
          )}

          {data.overview && (
            <p className="text-sm leading-relaxed text-neutral-700 dark:text-neutral-300">
              {data.overview}
            </p>
          )}

          <FollowButton tmdbId={id} isFollowing={data.is_following} />
        </div>
      </header>

      {data.is_following && progress && <Progress data={progress} />}

      <WhereToWatch tmdbId={id} />

      <section className="space-y-2">
        <h2 className="text-lg font-semibold">Temporadas</h2>
        {seasons.length === 0 ? (
          <p className="text-sm text-neutral-500">No hay temporadas disponibles.</p>
        ) : (
          <div className="space-y-2">
            {seasons.map((s) => (
              <SeasonRow
                key={s.season_number}
                seriesId={id}
                season={s}
                following={data.is_following}
                progress={progressBySeason.get(s.season_number)}
              />
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
