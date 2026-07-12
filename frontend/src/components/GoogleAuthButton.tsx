import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { GOOGLE_CLIENT_ID } from '../lib/config'

const GSI_SRC = 'https://accounts.google.com/gsi/client'

// Carga el script de Google Identity Services una sola vez.
function loadGsi(): Promise<void> {
  if (window.google) return Promise.resolve()
  const existing = document.getElementById('gsi-client') as HTMLScriptElement | null
  if (existing) {
    return new Promise((resolve, reject) => {
      existing.addEventListener('load', () => resolve())
      existing.addEventListener('error', () => reject(new Error('gsi load error')))
    })
  }
  return new Promise((resolve, reject) => {
    const script = document.createElement('script')
    script.id = 'gsi-client'
    script.src = GSI_SRC
    script.async = true
    script.defer = true
    script.onload = () => resolve()
    script.onerror = () => reject(new Error('gsi load error'))
    document.head.appendChild(script)
  })
}

/**
 * Botón «Continuar con Google». Se oculta si no hay client ID configurado
 * (`VITE_GOOGLE_CLIENT_ID`). Tras autenticar, navega a `redirectTo`.
 */
export default function GoogleAuthButton({ redirectTo }: { redirectTo: string }) {
  const { loginWithGoogle } = useAuth()
  const navigate = useNavigate()
  const containerRef = useRef<HTMLDivElement>(null)
  const [error, setError] = useState<string | null>(null)

  const handleCredential = useCallback(
    async (credential: string) => {
      setError(null)
      try {
        await loginWithGoogle(credential)
        navigate(redirectTo, { replace: true })
      } catch {
        setError('No se pudo iniciar sesión con Google. Inténtalo de nuevo.')
      }
    },
    [loginWithGoogle, navigate, redirectTo],
  )

  useEffect(() => {
    if (!GOOGLE_CLIENT_ID) return
    let cancelled = false
    loadGsi()
      .then(() => {
        if (cancelled || !window.google || !containerRef.current) return
        window.google.accounts.id.initialize({
          client_id: GOOGLE_CLIENT_ID,
          callback: (response) => {
            void handleCredential(response.credential)
          },
        })
        window.google.accounts.id.renderButton(containerRef.current, {
          type: 'standard',
          theme: 'outline',
          size: 'large',
          text: 'continue_with',
          shape: 'pill',
          logo_alignment: 'left',
        })
      })
      .catch(() => setError('No se pudo cargar Google. Inténtalo de nuevo.'))
    return () => {
      cancelled = true
    }
  }, [handleCredential])

  if (!GOOGLE_CLIENT_ID) return null

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3 text-xs text-neutral-400">
        <span className="h-px flex-1 bg-neutral-200 dark:bg-neutral-800" />o
        <span className="h-px flex-1 bg-neutral-200 dark:bg-neutral-800" />
      </div>
      <div ref={containerRef} className="flex justify-center" />
      {error && (
        <p className="text-sm text-red-600" role="alert">
          {error}
        </p>
      )}
    </div>
  )
}
