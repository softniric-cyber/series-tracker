import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'

const mockForgot = vi.fn()
vi.mock('../api/auth', () => ({
  forgotPassword: (email: string) => mockForgot(email),
}))

import ForgotPasswordPage from './ForgotPasswordPage'

function renderPage() {
  return render(
    <MemoryRouter>
      <ForgotPasswordPage />
    </MemoryRouter>,
  )
}

describe('ForgotPasswordPage', () => {
  it('submits the email and shows a neutral confirmation', async () => {
    mockForgot.mockResolvedValue({ message: 'ok' })
    renderPage()

    await userEvent.type(screen.getByLabelText('Email'), 'ana@example.com')
    await userEvent.click(screen.getByRole('button', { name: /Enviar enlace/ }))

    expect(mockForgot).toHaveBeenCalledWith('ana@example.com')
    expect(await screen.findByText(/te hemos enviado un enlace/i)).toBeInTheDocument()
  })

  it('still shows success even if the request fails (anti-enumeration)', async () => {
    mockForgot.mockRejectedValue(new Error('boom'))
    renderPage()

    await userEvent.type(screen.getByLabelText('Email'), 'ana@example.com')
    await userEvent.click(screen.getByRole('button', { name: /Enviar enlace/ }))

    expect(await screen.findByText(/te hemos enviado un enlace/i)).toBeInTheDocument()
  })
})
