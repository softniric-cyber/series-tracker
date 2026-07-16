import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import type { SeasonDetail, SeriesDetail, SeriesProviders } from '../api/types'

const mockDetail = vi.fn()
const mockProviders = vi.fn()
const mockSeason = vi.fn()
vi.mock('../api/series', () => ({
  getSeriesDetail: (id: number) => mockDetail(id),
  getSeriesProviders: (id: number) => mockProviders(id),
  getSeason: (id: number, n: number) => mockSeason(id, n),
}))

const mockFollow = vi.fn()
const mockUnfollow = vi.fn()
const mockProgress = vi.fn()
const mockMarkEpisode = vi.fn()
const mockUnmarkEpisode = vi.fn()
const mockMarkSeason = vi.fn()
const mockUnmarkSeason = vi.fn()
vi.mock('../api/me', () => ({
  followSeries: (id: number) => mockFollow(id),
  unfollowSeries: (id: number) => mockUnfollow(id),
  getProgress: (id: number) => mockProgress(id),
  markEpisodeWatched: (id: number) => mockMarkEpisode(id),
  unmarkEpisodeWatched: (id: number) => mockUnmarkEpisode(id),
  markSeasonWatched: (id: number, n: number) => mockMarkSeason(id, n),
  unmarkSeasonWatched: (id: number, n: number) => mockUnmarkSeason(id, n),
}))

import SeriesDetailPage from './SeriesDetailPage'

const detail: SeriesDetail = {
  tmdb_id: 95396,
  name: 'Separación',
  overview: 'Mark lidera un equipo.',
  poster_url: 'https://image.tmdb.org/t/p/w342/poster.jpg',
  status: 'Returning Series',
  first_air_date: '2022-02-17',
  last_air_date: '2025-03-21',
  genres: ['Drama', 'Misterio'],
  number_of_seasons: 2,
  number_of_episodes: 19,
  in_production: true,
  seasons: [
    { season_number: 0, name: 'Especiales', episode_count: 3, air_date: null, poster_url: null },
    { season_number: 1, name: 'Temporada 1', episode_count: 9, air_date: '2022-02-17', poster_url: null },
  ],
  cached_at: '2026-07-10T00:00:00+00:00',
  is_following: false,
}

const providers: SeriesProviders = {
  country: 'ES',
  link: 'https://tmdb.org/x',
  flatrate: [
    { provider_id: 350, provider_name: 'Apple TV+', logo_url: 'https://image.tmdb.org/t/p/w92/a.jpg', display_priority: 1 },
  ],
  rent: [],
  buy: [],
}

const season1: SeasonDetail = {
  series_tmdb_id: 95396,
  season_number: 1,
  name: 'Temporada 1',
  episodes: [
    { tmdb_id: 1, season_number: 1, episode_number: 1, name: 'Buenas noticias', air_date: '2022-02-17', watched: false },
    { tmdb_id: 2, season_number: 1, episode_number: 2, name: 'Half Loop', air_date: '2022-02-18', watched: false },
  ],
}

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/series/95396']}>
        <Routes>
          <Route path="/series/:tmdbId" element={<SeriesDetailPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('SeriesDetailPage', () => {
  it('shows header, streaming providers and lazily loads a season', async () => {
    mockDetail.mockResolvedValue(detail)
    mockProviders.mockResolvedValue(providers)
    mockSeason.mockResolvedValue(season1)
    renderPage()

    // Cabecera
    expect(await screen.findByRole('heading', { name: 'Separación', level: 1 })).toBeInTheDocument()
    expect(screen.getByText('Drama')).toBeInTheDocument()
    expect(screen.getByText('2022–2025')).toBeInTheDocument()

    // Dónde verla (flatrate)
    expect(await screen.findByRole('img', { name: 'Apple TV+' })).toBeInTheDocument()

    // La temporada 0 (especiales) está oculta; solo aparece la 1.
    expect(screen.queryByText('Especiales')).not.toBeInTheDocument()
    const seasonButton = screen.getByRole('button', { name: /Temporada 1/ })

    // Los episodios no se piden hasta desplegar.
    expect(mockSeason).not.toHaveBeenCalled()
    await userEvent.click(seasonButton)

    expect(await screen.findByText('Buenas noticias')).toBeInTheDocument()
    expect(screen.getByText('Half Loop')).toBeInTheDocument()
    expect(mockSeason).toHaveBeenCalledWith(95396, 1)
  })

  it('follows the series when clicking the follow button', async () => {
    mockDetail.mockResolvedValue({ ...detail, is_following: false })
    mockProviders.mockResolvedValue(providers)
    mockFollow.mockResolvedValue({ tmdb_id: 95396 })
    renderPage()

    const followButton = await screen.findByRole('button', { name: /Seguir/ })
    await userEvent.click(followButton)
    expect(mockFollow).toHaveBeenCalledWith(95396)
  })

  it('shows the following state when already followed', async () => {
    mockDetail.mockResolvedValue({ ...detail, is_following: true })
    mockProviders.mockResolvedValue(providers)
    mockProgress.mockResolvedValue({
      tmdb_id: 95396,
      total_episodes: 9,
      watched_episodes: 3,
      next_episode: null,
      seasons: [],
    })
    renderPage()

    expect(await screen.findByRole('button', { name: /Siguiendo/ })).toBeInTheDocument()
  })

  it('marks a fully-watched season as "Vista" in the list without expanding', async () => {
    mockDetail.mockResolvedValue({ ...detail, is_following: true })
    mockProviders.mockResolvedValue(providers)
    mockProgress.mockResolvedValue({
      tmdb_id: 95396,
      total_episodes: 9,
      watched_episodes: 9,
      next_episode: null,
      // T1 emitida por completo y toda vista → «Vista».
      seasons: [{ season_number: 1, episodes: 9, aired: 9, watched: 9, completed: true }],
    })
    renderPage()

    // El distintivo aparece en la lista, con la temporada aún colapsada.
    expect(await screen.findByText(/✓ Vista/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Temporada 1/ })).toHaveAttribute(
      'aria-expanded',
      'false',
    )
    expect(screen.queryByText('Buenas noticias')).not.toBeInTheDocument()
  })

  it('shows progress and marks an episode watched when following', async () => {
    mockDetail.mockResolvedValue({ ...detail, is_following: true })
    mockProviders.mockResolvedValue(providers)
    mockProgress.mockResolvedValue({
      tmdb_id: 95396,
      total_episodes: 9,
      watched_episodes: 3,
      next_episode: {
        tmdb_id: 4,
        season_number: 1,
        episode_number: 4,
        name: 'El episodio 4',
        air_date: '2022-03-10',
        watched: false,
      },
    })
    mockSeason.mockResolvedValue(season1)
    mockMarkEpisode.mockResolvedValue(undefined)
    renderPage()

    // Barra de progreso con "siguiente por ver".
    expect(await screen.findByText('Tu progreso')).toBeInTheDocument()
    expect(screen.getByText(/3 \/ 9/)).toBeInTheDocument()
    expect(screen.getByText(/T1·E4/)).toBeInTheDocument()

    // Desplegar la temporada muestra checkboxes; marcar uno llama al API.
    await userEvent.click(screen.getByRole('button', { name: /Temporada 1/ }))
    const checkbox = await screen.findByRole('checkbox', { name: /Buenas noticias/ })
    await userEvent.click(checkbox)
    expect(mockMarkEpisode).toHaveBeenCalledWith(1)
  })

  it('checks the episode and bumps progress optimistically before the request resolves', async () => {
    mockDetail.mockResolvedValue({ ...detail, is_following: true })
    mockProviders.mockResolvedValue(providers)
    mockProgress.mockResolvedValue({
      tmdb_id: 95396,
      total_episodes: 9,
      watched_episodes: 3,
      next_episode: null,
      seasons: [{ season_number: 1, episodes: 9, aired: 9, watched: 3, completed: false }],
    })
    // Primera carga sin vistos; la reconciliación posterior ya lo trae marcado.
    const watchedSeason1: SeasonDetail = {
      ...season1,
      episodes: season1.episodes.map((ep) => (ep.tmdb_id === 1 ? { ...ep, watched: true } : ep)),
    }
    mockSeason.mockResolvedValueOnce(season1)
    mockSeason.mockResolvedValue(watchedSeason1)
    // La mutación queda "colgada": la UI NO debe esperar a que resuelva.
    let resolveMark: () => void = () => {}
    mockMarkEpisode.mockReturnValue(
      new Promise<void>((resolve) => {
        resolveMark = resolve
      }),
    )
    renderPage()

    expect(await screen.findByText(/3 \/ 9/)).toBeInTheDocument()
    await userEvent.click(await screen.findByRole('button', { name: /Temporada 1/ }))
    const checkbox = await screen.findByRole('checkbox', { name: /Buenas noticias/ })
    expect(checkbox).not.toBeChecked()

    await userEvent.click(checkbox)
    // Optimista: check y barra de progreso al instante, sin respuesta del backend.
    expect(checkbox).toBeChecked()
    expect(screen.getByText(/4 \/ 9/)).toBeInTheDocument()

    resolveMark()
  })

  it('flips the follow button optimistically before the request resolves', async () => {
    mockDetail.mockResolvedValue({ ...detail, is_following: false })
    mockProviders.mockResolvedValue(providers)
    mockProgress.mockResolvedValue({
      tmdb_id: 95396,
      total_episodes: 9,
      watched_episodes: 0,
      next_episode: null,
      seasons: [],
    })
    // followSeries queda "colgada": el botón NO debe esperar a que resuelva.
    let resolveFollow: () => void = () => {}
    mockFollow.mockReturnValue(
      new Promise<void>((resolve) => {
        resolveFollow = resolve
      }),
    )
    renderPage()

    const followButton = await screen.findByRole('button', { name: /Seguir/ })
    await userEvent.click(followButton)
    // Optimista: pasa a "Siguiendo" sin esperar la respuesta del backend.
    expect(await screen.findByRole('button', { name: /Siguiendo/ })).toBeInTheDocument()

    resolveFollow()
  })

  it('shows a skeleton loading state while the detail is pending', async () => {
    // La ficha no resuelve: debe verse el placeholder anunciado a lectores de pantalla.
    mockDetail.mockReturnValue(new Promise(() => {}))
    mockProviders.mockResolvedValue(providers)
    renderPage()

    expect(await screen.findByText('Cargando ficha…')).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Separación' })).not.toBeInTheDocument()
  })

  it('shows a not-found message on 404', async () => {
    const { ApiError } = await import('../api/client')
    mockDetail.mockRejectedValue(new ApiError(404, 'Serie no encontrada'))
    mockProviders.mockResolvedValue(providers)
    renderPage()

    expect(await screen.findByText('Serie no encontrada.')).toBeInTheDocument()
  })
})
