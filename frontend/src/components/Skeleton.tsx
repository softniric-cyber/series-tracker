// Bloque gris con pulso para estados de carga (placeholder de contenido).
// Puramente decorativo: se marca aria-hidden y el contenedor de la vista lleva el
// role="status" con un texto sr-only para anunciarlo a lectores de pantalla.
export default function Skeleton({ className = '' }: { className?: string }) {
  return (
    <span
      aria-hidden="true"
      className={`block animate-pulse rounded bg-neutral-200 dark:bg-neutral-800 ${className}`}
    />
  )
}
