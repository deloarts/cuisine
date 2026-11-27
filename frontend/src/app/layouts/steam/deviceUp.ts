/**
 * Reads which way is really up from the device's orientation sensor, as a
 * direction on the screen, so the steam can rise against true gravity on a
 * tilted phone or tablet.
 *
 * It only listens: it never asks for the permission that iOS requires, so a
 * visitor is never prompted on the sign-in screen. Where the events do not
 * arrive (no sensor, no permission, a desktop browser), nothing is reported
 * and the steam keeps rising to the top of the screen.
 */

/**
 * Projects the upward direction onto the screen, given the device's tilt
 * angles from a deviceorientation event (degrees) and the screen's rotation
 * against the device (degrees, as screen.orientation.angle reports it).
 * The result has x to the right and y to the top of the screen. Its length is
 * the sine of the screen's tilt from lying flat, so it is close to zero when
 * the device lies on a table and up points out of the screen.
 */
export function screenUp(beta: number, gamma: number, screenAngle: number): [number, number] {
  const b = (beta * Math.PI) / 180
  const g = (gamma * Math.PI) / 180
  // The earth's up axis in the device's own frame, following the order in
  // which the orientation angles are applied (z, then x, then y).
  const x = -Math.cos(b) * Math.sin(g)
  const y = Math.sin(b)
  // When the screen is turned against the device, its axes are turned too.
  const a = (screenAngle * Math.PI) / 180
  return [x * Math.cos(a) - y * Math.sin(a), x * Math.sin(a) + y * Math.cos(a)]
}

/**
 * Below this length the device lies too flat for the screen to have an up;
 * the last direction is kept instead of following the sensor's noise.
 */
const FLAT = 0.2

function currentScreenAngle(): number {
  return screen.orientation?.angle ?? 0
}

/**
 * Calls back with the upward direction whenever the device reports a new
 * orientation that is clear enough to use. Returns a function that stops
 * listening.
 */
export function watchDeviceUp(onUp: (x: number, y: number) => void): () => void {
  if (typeof window === 'undefined' || !('DeviceOrientationEvent' in window)) return () => {}

  function onOrientation(event: DeviceOrientationEvent) {
    if (event.beta === null || event.gamma === null) return
    const [x, y] = screenUp(event.beta, event.gamma, currentScreenAngle())
    if (Math.hypot(x, y) < FLAT) return
    onUp(x, y)
  }

  window.addEventListener('deviceorientation', onOrientation)
  return () => window.removeEventListener('deviceorientation', onOrientation)
}
