import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { rateSeries, unrateSeries } from '../api/me'
import type { SeriesDetail } from '../api/types'

const STARS = [1, 2, 3, 4, 5]

/**
 * Puntuación personal de 1 a 5 estrellas.
 *
 * Pulsar la estrella ya marcada quita la puntuación (es la única forma de volver
 * a «sin nota», y evita añadir un botón aparte).
 *
 * La actualización es optimista, como el resto de acciones de la ficha (#28):
 * las estrellas cambian al instante y se revierten si la petición falla.
 */
export default function StarRating({ tmdbId, value }: { tmdbId: number; value: number | null }) {
  const queryClient = useQueryClient()
  const [hovered, setHovered] = useState<number | null>(null)
  const seriesKey = ['series', tmdbId] as const

  const mutation = useMutation({
    mutationFn: async (score: number | null) => {
      if (score === null) await unrateSeries(tmdbId)
      else await rateSeries(tmdbId, score)
    },
    onMutate: async (score) => {
      await queryClient.cancelQueries({ queryKey: seriesKey })
      const previous = queryClient.getQueryData<SeriesDetail>(seriesKey)
      queryClient.setQueryData<SeriesDetail>(seriesKey, (old) =>
        old ? { ...old, my_rating: score } : old,
      )
      return { previous }
    },
    onError: (_err, _score, context) => {
      if (context?.previous) queryClient.setQueryData(seriesKey, context.previous)
    },
    onSettled: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: seriesKey }),
        queryClient.invalidateQueries({ queryKey: ['mySeries'] }),
      ])
    },
  })

  // Al pasar el ratón se previsualiza la nota que se guardaría al pulsar.
  const shown = hovered ?? value ?? 0

  return (
    <div className="flex flex-wrap items-center gap-3">
      <div
        className="flex items-center gap-0.5"
        role="group"
        aria-label="Tu puntuación"
        onMouseLeave={() => setHovered(null)}
      >
        {STARS.map((star) => (
          <button
            key={star}
            type="button"
            onClick={() => mutation.mutate(star === value ? null : star)}
            onMouseEnter={() => setHovered(star)}
            onFocus={() => setHovered(star)}
            onBlur={() => setHovered(null)}
            disabled={mutation.isPending}
            aria-pressed={value != null && star <= value}
            aria-label={
              star === value ? `Quitar tu puntuación de ${star}` : `Puntuar con ${star} estrellas`
            }
            className={`rounded p-0.5 text-2xl leading-none transition hover:scale-110 disabled:opacity-60 ${
              star <= shown ? 'text-amber-500' : 'text-neutral-300 dark:text-neutral-600'
            }`}
          >
            <span aria-hidden>{star <= shown ? '★' : '☆'}</span>
          </button>
        ))}
      </div>
      <span className="text-sm text-neutral-500">
        {value != null ? `Tu nota: ${value}/5` : 'Sin puntuar'}
      </span>
    </div>
  )
}
