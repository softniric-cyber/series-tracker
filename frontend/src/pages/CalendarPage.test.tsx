import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import type { CalendarEntry } from '../api/types'
import { toKey } from '../lib/dates'

const mockGetCalendar = vi.fn()
vi.mock('../api/me', () => ({
  getCalendar: (from: string, to: string) => mockGetCalendar(from, to),
}))

import CalendarPage from './CalendarPage'

const todayKey = toKey(new Date())

function entryToday(): CalendarEntry {
  return {
    series_tmdb_id: 1399,
    series_name: 'Juego de tronos',
    poster_url: null,
    episode_tmdb_id: 555,
    season_number: 2,
    episode_number: 3,
    episode_name: 'Lo que está muerto',
    air_date: todayKey,
  }
}

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <CalendarPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('CalendarPage', () => {
  it("renders a premiere as a link to the series' detail page", async () => {
    mockGetCalendar.mockResolvedValue([entryToday()])
    renderPage()

    // Se renderizan la cuadrícula (escritorio) y la agenda (móvil): el enlace
    // aparece en ambas (jsdom no aplica el CSS que oculta una).
    const links = await screen.findAllByRole('link', { name: /Juego de tronos/ })
    expect(links[0]).toHaveAttribute('href', '/series/1399')
    expect(links[0]).toHaveTextContent('T2·E3')
  })

  it('switches to the week view and refetches a 7-day range', async () => {
    mockGetCalendar.mockResolvedValue([entryToday()])
    renderPage()
    await screen.findAllByRole('link', { name: /Juego de tronos/ })

    await userEvent.click(screen.getByRole('button', { name: 'Semana' }))

    // La última llamada cubre exactamente 7 días (lun→dom).
    const [from, to] = mockGetCalendar.mock.calls.at(-1) as [string, string]
    const days = (new Date(to).getTime() - new Date(from).getTime()) / 86_400_000
    expect(days).toBe(6)
    expect((await screen.findAllByRole('link', { name: /Juego de tronos/ })).length).toBeGreaterThan(
      0,
    )
  })

  it('shows an empty state when there are no premieres', async () => {
    mockGetCalendar.mockResolvedValue([])
    renderPage()

    expect(await screen.findByText(/No hay estrenos/)).toBeInTheDocument()
  })
})
