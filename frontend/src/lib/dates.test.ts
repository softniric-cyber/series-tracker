import { describe, expect, it } from 'vitest'
import { addDays, endOfMonth, monthGridDays, startOfMonth, startOfWeek, toKey, weekDays } from './dates'

describe('date helpers', () => {
  it('formats a local date key as YYYY-MM-DD', () => {
    expect(toKey(new Date(2026, 6, 9))).toBe('2026-07-09')
    expect(toKey(new Date(2026, 0, 1))).toBe('2026-01-01')
  })

  it('startOfWeek returns the Monday of the week', () => {
    // 2026-07-09 es jueves → lunes = 2026-07-06.
    expect(toKey(startOfWeek(new Date(2026, 6, 9)))).toBe('2026-07-06')
    expect(startOfWeek(new Date(2026, 6, 9)).getDay()).toBe(1)
  })

  it('addDays crosses month boundaries', () => {
    expect(toKey(addDays(new Date(2026, 6, 31), 1))).toBe('2026-08-01')
  })

  it('monthGridDays covers whole weeks including the 1st and last of the month', () => {
    const days = monthGridDays(new Date(2026, 6, 15))
    expect(days.length % 7).toBe(0)
    expect(days[0].getDay()).toBe(1) // empieza en lunes
    const keys = days.map(toKey)
    expect(keys).toContain(toKey(startOfMonth(new Date(2026, 6, 15))))
    expect(keys).toContain(toKey(endOfMonth(new Date(2026, 6, 15))))
  })

  it('weekDays returns 7 days from Monday', () => {
    const days = weekDays(new Date(2026, 6, 9))
    expect(days).toHaveLength(7)
    expect(toKey(days[0])).toBe('2026-07-06')
    expect(toKey(days[6])).toBe('2026-07-12')
  })
})
