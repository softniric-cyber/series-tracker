import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'

const mockExport = vi.fn()
const mockDelete = vi.fn()
vi.mock('../api/account', () => ({
  exportMyData: () => mockExport(),
  deleteAccount: () => mockDelete(),
}))

const mockLogout = vi.fn()
vi.mock('../auth/AuthContext', () => ({
  useAuth: () => ({
    user: { email: 'ana@example.com', country: 'ES', language: 'es-ES', created_at: '2026-01-01' },
    logout: mockLogout,
  }),
}))

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async (orig) => ({
  ...(await orig<typeof import('react-router-dom')>()),
  useNavigate: () => mockNavigate,
}))

import AccountPage from './AccountPage'

function renderPage() {
  return render(
    <MemoryRouter>
      <AccountPage />
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  // jsdom no implementa createObjectURL; lo stubbeamos para el flujo de descarga.
  URL.createObjectURL = vi.fn(() => 'blob:mock')
  URL.revokeObjectURL = vi.fn()
})

describe('AccountPage', () => {
  it('shows the profile and exports data on demand', async () => {
    mockExport.mockResolvedValue({ profile: {}, followed_series: [], watched_episodes: [] })
    renderPage()

    expect(screen.getByText('ana@example.com')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /Descargar mis datos/ }))
    expect(mockExport).toHaveBeenCalledOnce()
    expect(URL.createObjectURL).toHaveBeenCalled()
  })

  it('deletes the account only after confirmation, then logs out', async () => {
    mockDelete.mockResolvedValue(undefined)
    renderPage()

    // Primer clic solo muestra la confirmación, no borra.
    await userEvent.click(screen.getByRole('button', { name: 'Eliminar mi cuenta' }))
    expect(mockDelete).not.toHaveBeenCalled()

    await userEvent.click(screen.getByRole('button', { name: /Sí, eliminar mi cuenta/ }))
    expect(mockDelete).toHaveBeenCalledOnce()
    expect(mockLogout).toHaveBeenCalledOnce()
    expect(mockNavigate).toHaveBeenCalledWith('/login', { replace: true })
  })

  it('can cancel the deletion', async () => {
    renderPage()
    await userEvent.click(screen.getByRole('button', { name: 'Eliminar mi cuenta' }))
    await userEvent.click(screen.getByRole('button', { name: 'Cancelar' }))
    expect(screen.queryByRole('button', { name: /Sí, eliminar/ })).not.toBeInTheDocument()
    expect(mockDelete).not.toHaveBeenCalled()
  })
})
