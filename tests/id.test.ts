import { describe, expect, it } from 'vitest'
import { newId, now } from '../src/application/id'

describe('id helpers', () => {
  it('newId returns a UUID v4 string', () => {
    const value = newId()

    expect(value).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
    )
  })

  it('now returns an ISO 8601 timestamp', () => {
    const value = now()

    expect(value).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/)
    expect(Number.isNaN(Date.parse(value))).toBe(false)
  })
})