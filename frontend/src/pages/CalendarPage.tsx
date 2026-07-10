import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getCalendar } from '../api/me'
import type { CalendarEntry } from '../api/types'
import Spinner from '../components/Spinner'
import { addDays, addMonths, monthGridDays, toKey, weekDays } from '../lib/dates'

type View = 'month' | 'week'

const WEEKDAYS = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
const TODAY_KEY = toKey(new Date())

function EntryChip({ entry }: { entry: CalendarEntry }) {
  return (
    <Link
      to={`/series/${entry.series_tmdb_id}`}
      title={`${entry.series_name} — T${entry.season_number}·E${entry.episode_number}${
        entry.episode_name ? ` · ${entry.episode_name}` : ''
      }`}
      className="block truncate rounded bg-brand-50 px-1.5 py-0.5 text-xs text-brand-700 transition hover:bg-brand-100 dark:bg-brand-500/10 dark:text-brand-400 dark:hover:bg-brand-500/20"
    >
      <span className="font-medium">{entry.series_name}</span>{' '}
      <span className="text-brand-500/80">
        T{entry.season_number}·E{entry.episode_number}
      </span>
    </Link>
  )
}

function DayCell({
  date,
  entries,
  dimmed,
}: {
  date: Date
  entries: CalendarEntry[]
  dimmed: boolean
}) {
  const key = toKey(date)
  const isToday = key === TODAY_KEY
  return (
    <div
      className={`flex min-h-24 flex-col gap-1 border border-neutral-200 p-1.5 dark:border-neutral-800 ${
        dimmed ? 'bg-neutral-50 dark:bg-neutral-900/50' : 'bg-white dark:bg-neutral-900'
      }`}
    >
      <span
        className={`text-xs font-semibold ${
          isToday
            ? 'flex h-5 w-5 items-center justify-center rounded-full bg-brand-600 text-white'
            : dimmed
              ? 'text-neutral-400'
              : 'text-neutral-500'
        }`}
      >
        {date.getDate()}
      </span>
      <div className="flex flex-col gap-1">
        {entries.map((e) => (
          <EntryChip key={e.episode_tmdb_id} entry={e} />
        ))}
      </div>
    </div>
  )
}

export default function CalendarPage() {
  const [view, setView] = useState<View>('month')
  const [anchor, setAnchor] = useState(() => new Date())

  const days = useMemo(
    () => (view === 'month' ? monthGridDays(anchor) : weekDays(anchor)),
    [view, anchor],
  )
  const from = toKey(days[0])
  const to = toKey(days[days.length - 1])
  const anchorMonth = anchor.getMonth()

  const { data, isPending, isError } = useQuery({
    queryKey: ['calendar', from, to],
    queryFn: () => getCalendar(from, to),
  })

  const byDay = useMemo(() => {
    const map = new Map<string, CalendarEntry[]>()
    for (const entry of data ?? []) {
      const list = map.get(entry.air_date) ?? []
      list.push(entry)
      map.set(entry.air_date, list)
    }
    return map
  }, [data])

  const title =
    view === 'month'
      ? anchor.toLocaleDateString('es-ES', { month: 'long', year: 'numeric' })
      : `${days[0].toLocaleDateString('es-ES', { day: 'numeric', month: 'short' })} – ${days[6].toLocaleDateString('es-ES', { day: 'numeric', month: 'short', year: 'numeric' })}`

  function step(direction: number) {
    setAnchor((current) =>
      view === 'month' ? addMonths(current, direction) : addDays(current, direction * 7),
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold tracking-tight">Calendario</h1>
        <div className="inline-flex overflow-hidden rounded-lg border border-neutral-300 dark:border-neutral-700">
          {(['month', 'week'] as const).map((v) => (
            <button
              key={v}
              type="button"
              onClick={() => setView(v)}
              className={`px-3 py-1.5 text-sm font-medium transition ${
                view === v
                  ? 'bg-brand-600 text-white'
                  : 'bg-white text-neutral-600 hover:bg-neutral-100 dark:bg-neutral-900 dark:text-neutral-300 dark:hover:bg-neutral-800'
              }`}
            >
              {v === 'month' ? 'Mes' : 'Semana'}
            </button>
          ))}
        </div>
      </div>

      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => step(-1)}
          aria-label="Anterior"
          className="rounded-md border border-neutral-300 px-2.5 py-1 text-sm transition hover:bg-neutral-100 dark:border-neutral-700 dark:hover:bg-neutral-800"
        >
          ‹
        </button>
        <button
          type="button"
          onClick={() => setAnchor(new Date())}
          className="rounded-md border border-neutral-300 px-3 py-1 text-sm transition hover:bg-neutral-100 dark:border-neutral-700 dark:hover:bg-neutral-800"
        >
          Hoy
        </button>
        <button
          type="button"
          onClick={() => step(1)}
          aria-label="Siguiente"
          className="rounded-md border border-neutral-300 px-2.5 py-1 text-sm transition hover:bg-neutral-100 dark:border-neutral-700 dark:hover:bg-neutral-800"
        >
          ›
        </button>
        <span className="ml-1 text-sm font-medium capitalize text-neutral-600 dark:text-neutral-300">
          {title}
        </span>
      </div>

      {isError && (
        <p className="text-sm text-red-600">No se pudo cargar el calendario. Inténtalo de nuevo.</p>
      )}

      <div className="overflow-x-auto">
        <div className="min-w-[640px]">
          <div className="grid grid-cols-7">
            {WEEKDAYS.map((d) => (
              <div
                key={d}
                className="border-b border-neutral-200 px-1.5 py-1 text-xs font-semibold text-neutral-500 dark:border-neutral-800"
              >
                {d}
              </div>
            ))}
          </div>
          <div className="grid grid-cols-7">
            {days.map((date) => (
              <DayCell
                key={toKey(date)}
                date={date}
                entries={byDay.get(toKey(date)) ?? []}
                dimmed={view === 'month' && date.getMonth() !== anchorMonth}
              />
            ))}
          </div>
        </div>
      </div>

      {isPending && <Spinner label="Cargando calendario…" />}
      {data && data.length === 0 && !isPending && (
        <p className="text-sm text-neutral-500">
          No hay estrenos de tus series en este periodo.
        </p>
      )}
    </div>
  )
}
