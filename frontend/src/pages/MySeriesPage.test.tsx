import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import type { FollowedSeries } from '../api/types'

const mockGetMySeries = vi.fn()
vi.mock('../api/me', () => ({
  getMySeries: () => mockGetMySeries(),
}))

import MySeriesPage from './MySeriesPage'

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <MySeriesPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

function makeSeries(overrides: Partial<FollowedSeries>): FollowedSeries {
  return {
    tmdb_id: 1,
    name: 'Serie',
    poster_url: null,
    status: 'Returning Series',
    added_at: '2026-07-10T00:00:00+00:00',
    category: 'watching',
    aired_episodes: 0,
    watched_episodes: 0,
    my_rating: null,
    ...overrides,
  }
}

describe('MySeriesPage', () => {
  it('lists followed series with a link to their detail', async () => {
    const followed: FollowedSeries[] = [
      makeSeries({
        tmdb_id: 95396,
        name: 'Separación',
        poster_url: 'https://image.tmdb.org/t/p/w342/poster.jpg',
        category: 'watching',
        aired_episodes: 9,
        watched_episodes: 3,
      }),
    ]
    mockGetMySeries.mockResolvedValue(followed)
    renderPage()

    const link = await screen.findByRole('link', { name: /Separación/ })
    expect(link).toHaveAttribute('href', '/series/95396')
    expect(screen.getByText('3/9 vistos')).toBeInTheDocument()
  })

  it('shows the personal rating on the card', async () => {
    mockGetMySeries.mockResolvedValue([makeSeries({ name: 'Separación', my_rating: 4 })])
    renderPage()

    expect(await screen.findByText('Tu nota: 4 de 5')).toBeInTheDocument()
  })

  it('groups series into ordered sections by category', async () => {
    mockGetMySeries.mockResolvedValue([
      makeSeries({ tmdb_id: 1, name: 'Finalizada', category: 'finished' }),
      makeSeries({ tmdb_id: 2, name: 'EnCurso', category: 'watching' }),
      makeSeries({ tmdb_id: 3, name: 'AlDia', category: 'up_to_date' }),
      makeSeries({ tmdb_id: 4, name: 'SinComenzar', category: 'not_started' }),
    ])
    renderPage()

    const headings = await screen.findAllByRole('heading', { level: 2 })
    expect(headings.map((h) => h.textContent)).toEqual([
      'En curso (1)',
      'Sin comenzar (1)',
      'Al día (1)',
      'Finalizadas (1)',
    ])
  })

  it('shows an empty state when following nothing', async () => {
    mockGetMySeries.mockResolvedValue([])
    renderPage()

    expect(await screen.findByText(/Aún no sigues ninguna serie/)).toBeInTheDocument()
  })
})
