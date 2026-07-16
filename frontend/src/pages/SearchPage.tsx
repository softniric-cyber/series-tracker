import { useState } from 'react'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { searchSeries } from '../api/series'
import SeriesCard from '../components/SeriesCard'
import Spinner from '../components/Spinner'
import { inputClass } from '../components/ui'
import { useDebouncedValue } from '../lib/useDebouncedValue'

export default function SearchPage() {
  const [input, setInput] = useState('')
  const query = useDebouncedValue(input.trim(), 350)

  const { data, isFetching, isPlaceholderData, isError } = useQuery({
    queryKey: ['search', query],
    queryFn: () => searchSeries(query),
    enabled: query.length > 0,
    // Conserva los resultados anteriores mientras llega la nueva búsqueda: la
    // cuadrícula no parpadea entre pulsaciones, solo se atenúa (ver isPlaceholderData).
    placeholderData: keepPreviousData,
  })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Buscar series</h1>
        <input
          type="search"
          aria-label="Buscar series"
          placeholder="Ej. Severance, Dark, The Office…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          className={`${inputClass} mt-3`}
        />
      </div>

      {query.length === 0 && (
        <p className="text-sm text-neutral-500">Escribe el nombre de una serie para empezar.</p>
      )}
      {/* Spinner solo en la primera carga (aún no hay nada que mostrar). */}
      {isFetching && !data && <Spinner label="Buscando…" />}
      {isError && (
        <p className="text-sm text-red-600">
          No se pudo completar la búsqueda. Inténtalo de nuevo.
        </p>
      )}
      {data && !isFetching && data.results.length === 0 && (
        <p className="text-sm text-neutral-500">Sin resultados para «{query}».</p>
      )}
      {data && data.results.length > 0 && (
        <div
          className={`grid grid-cols-2 gap-4 transition-opacity sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 ${
            isPlaceholderData ? 'opacity-60' : 'opacity-100'
          }`}
        >
          {data.results.map((series) => (
            <SeriesCard key={series.tmdb_id} series={series} />
          ))}
        </div>
      )}
    </div>
  )
}
