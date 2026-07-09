import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import Spinner from './Spinner'

export default function PublicOnlyRoute() {
  const { status } = useAuth()

  if (status === 'loading') return <Spinner />
  if (status === 'authenticated') return <Navigate to="/" replace />
  return <Outlet />
}
