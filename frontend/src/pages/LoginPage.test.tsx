import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { ApiError } from '../api/client'

const mockLogin = vi.fn()
vi.mock('../auth/AuthContext', () => ({
  useAuth: () => ({ login: mockLogin }),
}))

// Import después del mock para que LoginPage use el useAuth mockeado.
import LoginPage from './LoginPage'

function renderLogin() {
  return render(
    <MemoryRouter>
      <LoginPage />
    </MemoryRouter>,
  )
}

describe('LoginPage', () => {
  it('sends the credentials to login', async () => {
    mockLogin.mockReset().mockResolvedValueOnce(undefined)
    renderLogin()

    await userEvent.type(screen.getByLabelText(/email/i), 'a@b.com')
    await userEvent.type(screen.getByLabelText(/contraseña/i), 'password123')
    await userEvent.click(screen.getByRole('button', { name: /entrar/i }))

    expect(mockLogin).toHaveBeenCalledWith('a@b.com', 'password123')
  })

  it('shows an error message on invalid credentials', async () => {
    mockLogin.mockReset().mockRejectedValueOnce(new ApiError(401, 'invalid'))
    renderLogin()

    await userEvent.type(screen.getByLabelText(/email/i), 'a@b.com')
    await userEvent.type(screen.getByLabelText(/contraseña/i), 'wrongpass1')
    await userEvent.click(screen.getByRole('button', { name: /entrar/i }))

    expect(await screen.findByText(/incorrectos/i)).toBeInTheDocument()
  })
})
