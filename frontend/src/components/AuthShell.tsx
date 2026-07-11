import type { ReactNode } from 'react'
import { cardClass } from './ui'
import logoIcon from '../assets/logo-icon.svg'
import Wordmark from './Wordmark'

interface AuthShellProps {
  subtitle: string
  children: ReactNode
  footer: ReactNode
}

export default function AuthShell({ subtitle, children, footer }: AuthShellProps) {
  return (
    <div className="flex min-h-screen items-center justify-center px-4 py-10">
      <div className="w-full max-w-sm">
        <img src={logoIcon} alt="" className="mx-auto mb-2 h-14 w-14" />
        <h1 className="mb-1 text-center">
          <Wordmark className="text-2xl" />
        </h1>
        <p className="mb-6 text-center text-sm text-neutral-500">{subtitle}</p>
        <div className={cardClass}>{children}</div>
        <p className="mt-4 text-center text-sm text-neutral-500">{footer}</p>
      </div>
    </div>
  )
}
