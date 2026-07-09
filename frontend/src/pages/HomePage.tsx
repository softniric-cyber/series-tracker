import { Link } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { cardClass } from '../components/ui'

export default function HomePage() {
  const { user } = useAuth()
  const name = user?.display_name?.trim() || user?.email

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Hola{name ? `, ${name}` : ''} 👋</h1>
        <p className="mt-1 text-neutral-500">Encuentra series y sigue lo que estás viendo.</p>
      </div>

      <div className={cardClass}>
        <h2 className="text-lg font-semibold">Buscar series</h2>
        <p className="mt-1 text-sm text-neutral-500">
          Busca cualquier serie por nombre y consulta su información.
        </p>
        <Link
          to="/search"
          className="mt-4 inline-block rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700"
        >
          Ir a la búsqueda
        </Link>
      </div>

      <div className={`${cardClass} text-sm text-neutral-500`}>
        <h2 className="text-base font-semibold text-neutral-700 dark:text-neutral-200">
          Mis series
        </h2>
        <p className="mt-1">Podrás seguir series y llevar tu progreso próximamente (Sprint 2).</p>
      </div>
    </div>
  )
}
