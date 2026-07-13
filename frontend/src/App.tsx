import { lazy, Suspense } from 'react'
import { Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import PublicOnlyRoute from './components/PublicOnlyRoute'
import Spinner from './components/Spinner'

// Páginas cargadas de forma perezosa: cada ruta es su propio chunk, así el
// arranque (login) no descarga el código del calendario, la ficha, etc.
const HomePage = lazy(() => import('./pages/HomePage'))
const LoginPage = lazy(() => import('./pages/LoginPage'))
const RegisterPage = lazy(() => import('./pages/RegisterPage'))
const ForgotPasswordPage = lazy(() => import('./pages/ForgotPasswordPage'))
const ResetPasswordPage = lazy(() => import('./pages/ResetPasswordPage'))
const SearchPage = lazy(() => import('./pages/SearchPage'))
const MySeriesPage = lazy(() => import('./pages/MySeriesPage'))
const CalendarPage = lazy(() => import('./pages/CalendarPage'))
const AccountPage = lazy(() => import('./pages/AccountPage'))
const SeriesDetailPage = lazy(() => import('./pages/SeriesDetailPage'))
const NotFoundPage = lazy(() => import('./pages/NotFoundPage'))

export default function App() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center">
          <Spinner />
        </div>
      }
    >
      <Routes>
        <Route element={<PublicOnlyRoute />}>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/reset-password" element={<ResetPasswordPage />} />
        </Route>
        <Route element={<ProtectedRoute />}>
          <Route element={<Layout />}>
            <Route path="/" element={<HomePage />} />
            <Route path="/search" element={<SearchPage />} />
            <Route path="/mis-series" element={<MySeriesPage />} />
            <Route path="/calendario" element={<CalendarPage />} />
            <Route path="/cuenta" element={<AccountPage />} />
            <Route path="/series/:tmdbId" element={<SeriesDetailPage />} />
          </Route>
        </Route>
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </Suspense>
  )
}
