export default function Spinner({ label = 'Cargando…' }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-3 py-16 text-neutral-500" role="status">
      <span className="h-5 w-5 animate-spin rounded-full border-2 border-neutral-300 border-t-brand-600" />
      <span className="text-sm">{label}</span>
    </div>
  )
}
