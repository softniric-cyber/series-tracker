import { NavLink } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

const linkBase = 'rounded-md px-3 py-1.5 text-sm font-medium transition'

function navClass({ isActive }: { isActive: boolean }): string {
  return isActive
    ? `${linkBase} bg-brand-100 text-brand-700 dark:bg-brand-600/20 dark:text-brand-400`
    : `${linkBase} text-neutral-600 hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-neutral-800`
}

export default function Navbar() {
  const { user, logout } = useAuth()
  return (
    <header className="border-b border-neutral-200 bg-white/80 backdrop-blur dark:border-neutral-800 dark:bg-neutral-900/80">
      <div className="mx-auto flex w-full max-w-5xl flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3">
        <NavLink to="/" className="text-lg font-bold tracking-tight text-brand-600">
          SeriesTracker
        </NavLink>
        <nav className="flex items-center gap-1">
          <NavLink to="/" end className={navClass}>
            Inicio
          </NavLink>
          <NavLink to="/search" className={navClass}>
            Buscar
          </NavLink>
        </nav>
        <div className="ml-auto flex items-center gap-3">
          {user && (
            <span className="hidden max-w-[12rem] truncate text-sm text-neutral-500 sm:inline">
              {user.email}
            </span>
          )}
          <button
            type="button"
            onClick={logout}
            className="rounded-md border border-neutral-300 px-3 py-1.5 text-sm font-medium text-neutral-700 transition hover:bg-neutral-100 dark:border-neutral-700 dark:text-neutral-200 dark:hover:bg-neutral-800"
          >
            Salir
          </button>
        </div>
      </div>
    </header>
  )
}
