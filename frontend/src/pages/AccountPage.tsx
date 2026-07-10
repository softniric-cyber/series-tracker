import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { deleteAccount, exportMyData } from '../api/account'
import { useAuth } from '../auth/AuthContext'
import { cardClass } from '../components/ui'

function downloadJson(filename: string, data: unknown): void {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}

export default function AccountPage() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const [exporting, setExporting] = useState(false)
  const [exportError, setExportError] = useState(false)
  const [confirmingDelete, setConfirmingDelete] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState(false)

  async function handleExport() {
    setExporting(true)
    setExportError(false)
    try {
      const data = await exportMyData()
      downloadJson('series-tracker-datos.json', data)
    } catch {
      setExportError(true)
    } finally {
      setExporting(false)
    }
  }

  async function handleDelete() {
    setDeleting(true)
    setDeleteError(false)
    try {
      await deleteAccount()
      logout()
      navigate('/login', { replace: true })
    } catch {
      setDeleteError(true)
      setDeleting(false)
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Cuenta</h1>

      <section className={cardClass}>
        <h2 className="text-lg font-semibold">Perfil</h2>
        <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-6 gap-y-1.5 text-sm">
          <dt className="text-neutral-500">Email</dt>
          <dd>{user?.email}</dd>
          <dt className="text-neutral-500">País</dt>
          <dd>{user?.country}</dd>
          <dt className="text-neutral-500">Idioma</dt>
          <dd>{user?.language}</dd>
          {user?.created_at && (
            <>
              <dt className="text-neutral-500">Miembro desde</dt>
              <dd>{new Date(user.created_at).toLocaleDateString('es-ES')}</dd>
            </>
          )}
        </dl>
      </section>

      <section className={cardClass}>
        <h2 className="text-lg font-semibold">Exportar mis datos</h2>
        <p className="mt-1 text-sm text-neutral-500">
          Descarga un archivo JSON con tu perfil, tus series seguidas y tus episodios vistos.
        </p>
        <button
          type="button"
          onClick={handleExport}
          disabled={exporting}
          className="mt-4 inline-block rounded-lg border border-neutral-300 px-4 py-2 text-sm font-semibold text-neutral-700 transition hover:bg-neutral-100 disabled:opacity-60 dark:border-neutral-700 dark:text-neutral-200 dark:hover:bg-neutral-800"
        >
          {exporting ? 'Preparando…' : 'Descargar mis datos'}
        </button>
        {exportError && (
          <p className="mt-2 text-sm text-red-600">No se pudo exportar. Inténtalo de nuevo.</p>
        )}
      </section>

      <section className={`${cardClass} border-red-200 dark:border-red-900/50`}>
        <h2 className="text-lg font-semibold text-red-700 dark:text-red-400">Eliminar cuenta</h2>
        <p className="mt-1 text-sm text-neutral-500">
          Esta acción es permanente: se borrarán tu cuenta y todos tus datos (series seguidas y
          progreso). No se puede deshacer.
        </p>
        {!confirmingDelete ? (
          <button
            type="button"
            onClick={() => setConfirmingDelete(true)}
            className="mt-4 inline-block rounded-lg border border-red-300 px-4 py-2 text-sm font-semibold text-red-600 transition hover:bg-red-50 dark:border-red-900 dark:hover:bg-red-950/40"
          >
            Eliminar mi cuenta
          </button>
        ) : (
          <div className="mt-4 space-y-3 rounded-lg border border-red-300 bg-red-50 p-4 dark:border-red-900 dark:bg-red-950/30">
            <p className="text-sm font-medium text-red-700 dark:text-red-300">
              ¿Seguro que quieres eliminar tu cuenta? Esta acción no se puede deshacer.
            </p>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={handleDelete}
                disabled={deleting}
                className="rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-red-700 disabled:opacity-60"
              >
                {deleting ? 'Eliminando…' : 'Sí, eliminar mi cuenta'}
              </button>
              <button
                type="button"
                onClick={() => setConfirmingDelete(false)}
                disabled={deleting}
                className="rounded-lg border border-neutral-300 px-4 py-2 text-sm font-semibold text-neutral-700 transition hover:bg-neutral-100 disabled:opacity-60 dark:border-neutral-700 dark:text-neutral-200 dark:hover:bg-neutral-800"
              >
                Cancelar
              </button>
            </div>
            {deleteError && (
              <p className="text-sm text-red-600">No se pudo eliminar la cuenta. Inténtalo de nuevo.</p>
            )}
          </div>
        )}
      </section>
    </div>
  )
}
