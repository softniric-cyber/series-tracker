import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import type { SeriesSearchResponse } from '../api/types'

const mockSearch = vi.fn()
vi.mock('../api/series', () => ({
  searchSeries: (query: string, page?: number) => mockSearch(query, page),
}))

import SearchPage from './SearchPage'

function renderSearch() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <SearchPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('SearchPage', () => {
  it('renders results with their poster after typing a query', async () => {
    const response: SeriesSearchResponse = {
      query: 'Severance',
      page: 1,
      total_pages: 1,
      total_results: 1,
      results: [
        {
          tmdb_id: 95396,
          name: 'Separación',
          overview: null,
          poster_url: 'https://image.tmdb.org/t/p/w342/abc.jpg',
          first_air_date: '2022-02-17',
          vote_average: 8.4,
        },
      ],
    }
    mockSearch.mockResolvedValue(response)
    renderSearch()

    await userEvent.type(screen.getByRole('searchbox'), 'Severance')

    expect(await screen.findByText('Separación', {}, { timeout: 3000 })).toBeInTheDocument()
    const poster = screen.getByRole('img', { name: 'Separación' })
    expect(poster).toHaveAttribute('src', 'https://image.tmdb.org/t/p/w342/abc.jpg')
  })
})
