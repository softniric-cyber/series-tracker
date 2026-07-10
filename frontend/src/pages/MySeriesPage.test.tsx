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

describe('MySeriesPage', () => {
  it('lists followed series with a link to their detail', async () => {
    const followed: FollowedSeries[] = [
      {
        tmdb_id: 95396,
        name: 'Separación',
        poster_url: 'https://image.tmdb.org/t/p/w342/poster.jpg',
        status: 'Returning Series',
        added_at: '2026-07-10T00:00:00+00:00',
      },
    ]
    mockGetMySeries.mockResolvedValue(followed)
    renderPage()

    const link = await screen.findByRole('link', { name: /Separación/ })
    expect(link).toHaveAttribute('href', '/series/95396')
  })

  it('shows an empty state when following nothing', async () => {
    mockGetMySeries.mockResolvedValue([])
    renderPage()

    expect(await screen.findByText(/Aún no sigues ninguna serie/)).toBeInTheDocument()
  })
})
