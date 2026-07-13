import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import './index.css'
import App from './App'
import { AuthProvider } from './auth/AuthContext'
import { API_URL } from './lib/config'

// Despierta el backend (Render free se duerme tras inactividad) en cuanto carga
// la app, mientras el usuario llega al login → oculta el arranque en frío.
void fetch(`${API_URL}/health`).catch(() => {})

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      // Los datos se consideran frescos 5 min: volver a una vista ya cargada no
      // refetchea (navegación instantánea). Las mutaciones (seguir, marcar visto)
      // invalidan sus queries explícitamente, así que esto no sirve datos obsoletos.
      staleTime: 1000 * 60 * 5,
    },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <App />
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
)
