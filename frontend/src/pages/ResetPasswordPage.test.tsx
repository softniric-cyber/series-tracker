import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'

const mockReset = vi.fn()
vi.mock('../api/auth', () => ({
  resetPassword: (token: string, pw: string) => mockReset(token, pw),
}))

import ResetPasswordPage from './ResetPasswordPage'

beforeEach(() => {
  mockReset.mockReset()
})

function renderPage(entry: string) {
  return render(
    <MemoryRouter initialEntries={[entry]}>
      <Routes>
        <Route path="/reset-password" element={<ResetPasswordPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('ResetPasswordPage', () => {
  it('resets the password with the token from the URL', async () => {
    mockReset.mockResolvedValue({ message: 'ok' })
    renderPage('/reset-password?token=abc123')

    await userEvent.type(screen.getByLabelText('Nueva contraseña'), 'newpassword1')
    await userEvent.click(screen.getByRole('button', { name: /Guardar contraseña/ }))

    expect(mockReset).toHaveBeenCalledWith('abc123', 'newpassword1')
    expect(await screen.findByText(/Contraseña actualizada/i)).toBeInTheDocument()
  })

  it('shows an error when the link is invalid or expired (400)', async () => {
    const { ApiError } = await import('../api/client')
    mockReset.mockRejectedValue(new ApiError(400, 'bad'))
    renderPage('/reset-password?token=expired')

    await userEvent.type(screen.getByLabelText('Nueva contraseña'), 'newpassword1')
    await userEvent.click(screen.getByRole('button', { name: /Guardar contraseña/ }))

    expect(await screen.findByText(/inválido o ha caducado/i)).toBeInTheDocument()
  })

  it('warns when the token is missing from the URL', () => {
    renderPage('/reset-password')
    expect(screen.getByText(/Falta el token/i)).toBeInTheDocument()
    expect(mockReset).not.toHaveBeenCalled()
  })
})
