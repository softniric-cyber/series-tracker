// Logotipo de texto de la marca: «trackmy» en gris + «series» en morado,
// replicando el lockup de img/horizontal.svg pero como texto (legible en dark).
export default function Wordmark({ className }: { className?: string }) {
  return (
    <span className={`tracking-tight ${className ?? ''}`}>
      <span className="font-semibold text-neutral-700 dark:text-neutral-200">trackmy</span>
      <span className="font-extrabold text-brand-600 dark:text-brand-400">series</span>
    </span>
  )
}
