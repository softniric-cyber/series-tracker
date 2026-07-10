// Utilidades de fecha para el calendario. Se trabaja con `Date` en hora local y
// se generan claves `YYYY-MM-DD` (mismos strings que devuelve el backend en
// air_date) para agrupar/comparar sin problemas de zona horaria.

export function toKey(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

export function addDays(d: Date, n: number): Date {
  const r = new Date(d)
  r.setDate(r.getDate() + n)
  return r
}

// Lunes como primer día de la semana.
export function startOfWeek(d: Date): Date {
  const r = new Date(d.getFullYear(), d.getMonth(), d.getDate())
  const offset = (r.getDay() + 6) % 7
  return addDays(r, -offset)
}

export function startOfMonth(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), 1)
}

export function endOfMonth(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth() + 1, 0)
}

export function addMonths(d: Date, n: number): Date {
  return new Date(d.getFullYear(), d.getMonth() + n, 1)
}

/** Días (lunes→domingo) que cubren la cuadrícula del mes que contiene `anchor`. */
export function monthGridDays(anchor: Date): Date[] {
  const gridStart = startOfWeek(startOfMonth(anchor))
  const gridEnd = addDays(startOfWeek(endOfMonth(anchor)), 6)
  const days: Date[] = []
  for (let d = gridStart; d <= gridEnd; d = addDays(d, 1)) days.push(d)
  return days
}

/** Los 7 días (lunes→domingo) de la semana que contiene `anchor`. */
export function weekDays(anchor: Date): Date[] {
  const start = startOfWeek(anchor)
  return Array.from({ length: 7 }, (_, i) => addDays(start, i))
}
