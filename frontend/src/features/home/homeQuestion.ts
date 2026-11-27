/**
 * The subtitle of the home page is drawn once per app load: the draw lives
 * at module scope, so every visit of the home page during one load shows
 * the same line and the next load may show another.
 */
let drawn: number | null = null

export function appLoadPick(count: number): number {
  drawn ??= Math.floor(Math.random() * count)
  return drawn % count
}

/** Forgets the draw, for tests that want a fresh load. */
export function resetAppLoadPick(): void {
  drawn = null
}
