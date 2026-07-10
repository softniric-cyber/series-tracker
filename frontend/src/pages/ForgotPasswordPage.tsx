import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { forgotPassword } from '../api/auth'
import AuthShell from '../components/AuthShell'
import { inputClass, labelClass, primaryButtonClass } from '../components/ui'

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [done, setDone] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setSubmitting(true)
    try {
      // Respuesta neutra del backend (anti-enumeración): mostramos éxito siempre.
      await forgotPassword(email)
    } catch {
      // Ignoramos el error a propósito para no revelar si el email existe.
    } finally {
      setSubmitting(false)
      setDone(true)
    }
  }

  return (
    <AuthShell
      subtitle="Recupera tu contraseña"
      footer={
        <>
          ¿Ya la recuerdas?{' '}
          <Link to="/login" className="font-medium text-brand-600 hover:underline">
            Inicia sesión
          </Link>
        </>
      }
    >
      {done ? (
        <p className="text-sm text-neutral-600 dark:text-neutral-300" role="status">
          Si ese email tiene una cuenta, te hemos enviado un enlace para restablecer la contraseña.
          Revisa tu bandeja de entrada (y la carpeta de spam). El enlace caduca en 30 minutos.
        </p>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          <p className="text-sm text-neutral-500">
            Introduce tu email y te enviaremos un enlace para elegir una nueva contraseña.
          </p>
          <div>
            <label htmlFor="email" className={labelClass}>
              Email
            </label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className={inputClass}
            />
          </div>
          <button type="submit" disabled={submitting} className={primaryButtonClass}>
            {submitting ? 'Enviando…' : 'Enviar enlace'}
          </button>
        </form>
      )}
    </AuthShell>
  )
}
