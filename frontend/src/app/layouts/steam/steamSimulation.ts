/**
 * A small fluid simulation of steam rising from a pot that stands just below
 * the bottom edge of the canvas. It runs on the GPU with WebGL2 and follows
 * the stable fluids method: the velocity field is advected, lifted by heat,
 * curled by vorticity confinement and made divergence free with a pressure
 * solve. The air carries two fields along: the visible vapour, which lingers
 * and slowly fades, and its heat, which drives the lift but cools within a few
 * seconds. Steam therefore rises quickly only just above the pot, then slows,
 * spreads and drifts, instead of shooting up in a steady jet.
 *
 * "Up" need not be the top of the screen. When the device reports how it is
 * held, the caller passes the real upward direction to setUp, the steam rises
 * that way and the pot moves to the edge that is down.
 *
 * Velocities are measured in simulation cells per second, so the tuning below
 * does not depend on the size of the screen. Positions in the shaders are in
 * square units, one unit being the canvas height, so directions keep their
 * angle on a wide or a tall screen.
 */

const SIM_HEIGHT = 128
const DYE_HEIGHT = 320
const PRESSURE_ITERATIONS = 20
const FRAME_INTERVAL_MS = 1000 / 30

const TUNING = {
  // How far beyond the canvas edge the pot stands, in canvas heights.
  sourceOffset: 0.06,
  sourceRadius: 0.008,
  jet: 3,
  // Lift per unit of heat, and how much heat the pot gives off per second.
  buoyancy: 18,
  heat: 1.2,
  turbulence: 16,
  breeze: 1,
  // Now and then a short, soft gust from a random side stirs a band of air at
  // a random height. Its peak strength, how long it lasts and the quiet time
  // between gusts, each in seconds as a range.
  gust: 2.5,
  gustLength: [1.5, 3],
  gustPause: [5, 12],
  curl: 22,
  emission: 0.85,
  // Extra fading per second near the top, where real steam has thinned out.
  topFade: 0.5,
  // Damping per second; the air's drag keeps any channel from settling in.
  velocityDissipation: 1.1,
  dyeDissipation: 0.07,
  // How quickly the steam cools, per second.
  cooling: 0.3,
  opacity: 0.16,
  // A light just beyond the top right corner that shines on the steam only.
  // How bright the steam is without it, how bright the light makes it, how
  // deeply the steam shades itself and how quickly the light fades with
  // distance.
  ambient: 0.6,
  light: 3.6,
  shadow: 4,
  lightFalloff: 0.8,
  // After a while the pot only simmers: from this many seconds on, it gives
  // off less steam, easing down over the fade time to the simmer level.
  simmerAfter: 45,
  simmerFade: 10,
  simmerLevel: 0.2,
}

const VERTEX = `#version 300 es
out vec2 vUv;
void main() {
  vec2 p = vec2(float((gl_VertexID << 1) & 2), float(gl_VertexID & 2));
  vUv = p;
  gl_Position = vec4(p * 2.0 - 1.0, 0.0, 1.0);
}`

const HEADER = `#version 300 es
precision highp float;
precision highp sampler2D;
in vec2 vUv;
out vec4 outColor;
`

const ADVECT = `${HEADER}
uniform sampler2D uVelocity;
uniform sampler2D uSource;
uniform vec2 uSimTexel;
uniform float uDt;
uniform vec4 uDissipation;
void main() {
  vec2 coord = vUv - uDt * texture(uVelocity, vUv).xy * uSimTexel;
  outColor = texture(uSource, coord) / (1.0 + uDissipation * uDt);
}`

const FORCES = `${HEADER}
uniform sampler2D uVelocity;
uniform sampler2D uDye;
uniform vec2 uSource;
uniform vec2 uUp;
uniform float uReach;
uniform float uAspect;
uniform float uRadius;
uniform vec2 uJet;
uniform float uBuoyancy;
uniform float uTurbulence;
uniform float uBreeze;
uniform vec2 uGust;
uniform float uGustHeight;
uniform float uTime;
uniform float uDt;
void main() {
  vec2 v = texture(uVelocity, vUv).xy;
  vec2 side = vec2(uUp.y, -uUp.x);
  vec2 p = vec2(vUv.x * uAspect, vUv.y) - uSource;
  // How far up the plume this point is, from 0 at the pot to 1 at the far edge.
  float height = dot(p, uUp) / uReach;
  // The room's air is never quite still: a slow sideways drift that changes
  // with height and time makes the plume lean and wander as it rises.
  float breeze = sin(height * 3.0 + uTime * 0.21) * sin(uTime * 0.13 + height * 1.7)
    + 0.5 * sin(height * 7.0 - uTime * 0.37);
  vec2 steam = texture(uDye, vUv).rg;
  float d = steam.r;
  float g = exp(-dot(p, p) / uRadius);
  // A slow, uneven sideways nudge wherever there is vapour, so the plume
  // breaks into wisps instead of rising as a straight column.
  float wobble = sin(vUv.y * 9.0 - uTime * 0.9 + sin(vUv.x * 5.0 + uTime * 0.4) * 2.0)
    * sin(vUv.x * 7.0 + uTime * 0.6)
    + 0.6 * sin(vUv.y * 23.0 + uTime * 1.3) * sin(vUv.x * 19.0 - uTime * 0.8);
  float gustBand = vUv.y - uGustHeight;
  // Uneven along its way, so the gust ruffles the plume instead of shifting it.
  vec2 gust = uGust * exp(-gustBand * gustBand / 0.03) * (0.5 + 0.5 * sin(vUv.x * 11.0 + uTime * 0.8));
  // Close to the pot the plume is still smooth; higher up it has mixed with
  // the room's air, so it churns more.
  float churn = uTurbulence * (0.3 + 1.4 * clamp(height, 0.0, 1.0));
  vec2 force = g * uJet + side * (wobble * churn * d + breeze * uBreeze) + uUp * (uBuoyancy * steam.g);
  v += (force + gust) * uDt;
  outColor = vec4(v, 0.0, 1.0);
}`

const EMIT = `${HEADER}
uniform sampler2D uDye;
uniform vec2 uSource;
uniform vec2 uUp;
uniform float uReach;
uniform float uAspect;
uniform float uRadius;
uniform float uAmount;
uniform float uHeat;
uniform float uPuff;
uniform vec2 uThreads[3];
uniform vec3 uThreadPuff;
uniform float uTopFade;
uniform float uDt;
vec2 position() {
  return vec2(vUv.x * uAspect, vUv.y);
}
float thread(vec2 centre, float radius) {
  vec2 p = position() - centre;
  return exp(-dot(p, p) / radius);
}
void main() {
  // The vapour leaves the pot in a few separate threads that wander and puff
  // on their own, so the plume shows strands instead of an even fill.
  float r = uRadius * 0.45;
  float g = thread(uThreads[0], r) * uThreadPuff.x + thread(uThreads[1], r) * uThreadPuff.y
    + thread(uThreads[2], r) * uThreadPuff.z;
  vec2 p = position() - uSource;
  float height = dot(p, uUp) / uReach;
  vec2 steam = texture(uDye, vUv).rg;
  float d = steam.r * (1.0 - uTopFade * uDt * smoothstep(0.45, 1.0, height));
  d += g * uAmount * uDt;
  // The heat leaves the whole mouth of the pot, in the same puffs.
  float h = steam.g + exp(-dot(p, p) / uRadius) * uPuff * uHeat * uDt;
  outColor = vec4(min(d, 1.5), min(h, 2.0), 0.0, 1.0);
}`

const CURL = `${HEADER}
uniform sampler2D uVelocity;
uniform vec2 uTexel;
void main() {
  float l = texture(uVelocity, vUv - vec2(uTexel.x, 0.0)).y;
  float r = texture(uVelocity, vUv + vec2(uTexel.x, 0.0)).y;
  float b = texture(uVelocity, vUv - vec2(0.0, uTexel.y)).x;
  float t = texture(uVelocity, vUv + vec2(0.0, uTexel.y)).x;
  outColor = vec4(0.5 * ((r - l) - (t - b)), 0.0, 0.0, 1.0);
}`

const VORTICITY = `${HEADER}
uniform sampler2D uVelocity;
uniform sampler2D uCurl;
uniform vec2 uTexel;
uniform float uCurlStrength;
uniform float uDt;
void main() {
  float l = texture(uCurl, vUv - vec2(uTexel.x, 0.0)).r;
  float r = texture(uCurl, vUv + vec2(uTexel.x, 0.0)).r;
  float b = texture(uCurl, vUv - vec2(0.0, uTexel.y)).r;
  float t = texture(uCurl, vUv + vec2(0.0, uTexel.y)).r;
  float c = texture(uCurl, vUv).r;
  vec2 force = 0.5 * vec2(abs(t) - abs(b), abs(r) - abs(l));
  force /= length(force) + 0.0001;
  force *= uCurlStrength * c;
  force.y *= -1.0;
  vec2 v = texture(uVelocity, vUv).xy + force * uDt;
  outColor = vec4(v, 0.0, 1.0);
}`

const DIVERGENCE = `${HEADER}
uniform sampler2D uVelocity;
uniform vec2 uTexel;
void main() {
  float l = texture(uVelocity, vUv - vec2(uTexel.x, 0.0)).x;
  float r = texture(uVelocity, vUv + vec2(uTexel.x, 0.0)).x;
  float b = texture(uVelocity, vUv - vec2(0.0, uTexel.y)).y;
  float t = texture(uVelocity, vUv + vec2(0.0, uTexel.y)).y;
  outColor = vec4(0.5 * (r - l + t - b), 0.0, 0.0, 1.0);
}`

const PRESSURE = `${HEADER}
uniform sampler2D uPressure;
uniform sampler2D uDivergence;
uniform vec2 uTexel;
void main() {
  float l = texture(uPressure, vUv - vec2(uTexel.x, 0.0)).r;
  float r = texture(uPressure, vUv + vec2(uTexel.x, 0.0)).r;
  float b = texture(uPressure, vUv - vec2(0.0, uTexel.y)).r;
  float t = texture(uPressure, vUv + vec2(0.0, uTexel.y)).r;
  float div = texture(uDivergence, vUv).r;
  outColor = vec4((l + r + b + t - div) * 0.25, 0.0, 0.0, 1.0);
}`

const GRADIENT = `${HEADER}
uniform sampler2D uPressure;
uniform sampler2D uVelocity;
uniform vec2 uTexel;
void main() {
  float l = texture(uPressure, vUv - vec2(uTexel.x, 0.0)).r;
  float r = texture(uPressure, vUv + vec2(uTexel.x, 0.0)).r;
  float b = texture(uPressure, vUv - vec2(0.0, uTexel.y)).r;
  float t = texture(uPressure, vUv + vec2(0.0, uTexel.y)).r;
  vec2 v = texture(uVelocity, vUv).xy - 0.5 * vec2(r - l, t - b);
  outColor = vec4(v, 0.0, 1.0);
}`

const SCALE = `${HEADER}
uniform sampler2D uSource;
uniform float uFactor;
void main() {
  outColor = texture(uSource, vUv) * uFactor;
}`

const DISPLAY = `${HEADER}
uniform sampler2D uDye;
uniform vec2 uDyeTexel;
uniform float uOpacity;
uniform float uAspect;
uniform float uAmbient;
uniform float uLight;
uniform float uShadow;
uniform float uFalloff;
const vec2 LIGHT = vec2(1.05, 1.05);
const int STEPS = 10;
void main() {
  // A light blur softens the edges the advection leaves sharp.
  vec2 o = uDyeTexel * 1.5;
  float d = texture(uDye, vUv).r * 0.4
    + (texture(uDye, vUv + vec2(o.x, o.y)).r + texture(uDye, vUv + vec2(-o.x, o.y)).r
    + texture(uDye, vUv + vec2(o.x, -o.y)).r + texture(uDye, vUv - o).r) * 0.15;
  float a = (1.0 - exp(-d * 1.2)) * uOpacity;
  // Walk towards the light and add up the vapour in the way: steam that faces
  // the light glows, steam behind other steam stays in its shadow.
  vec2 toLight = LIGHT - vUv;
  vec2 stepUv = toLight / float(STEPS) * 0.5;
  float depth = 0.0;
  for (int i = 1; i <= STEPS; i++) {
    depth += texture(uDye, vUv + stepUv * float(i)).r;
  }
  depth *= length(stepUv * vec2(uAspect, 1.0));
  float distance = length(toLight * vec2(uAspect, 1.0));
  float reach = 1.0 / (1.0 + uFalloff * distance * distance);
  float lit = uAmbient + uLight * exp(-depth * uShadow) * reach;
  outColor = vec4(vec3(1.0, 0.96, 0.9) * lit * a, a);
}`

interface Target {
  texture: WebGLTexture
  framebuffer: WebGLFramebuffer
  width: number
  height: number
}

interface DoubleTarget {
  read: Target
  write: Target
  swap: () => void
}

interface Program {
  use: () => void
  uniform: (name: string) => WebGLUniformLocation | null
}

export interface SteamSimulation {
  /** Matches the simulation to the canvas's current size, starting it afresh. */
  resize: () => void
  /**
   * Points the steam the given way: a direction on the screen with x to the
   * right and y to the top, of any length. The steam turns there smoothly.
   */
  setUp: (x: number, y: number) => void
  start: () => void
  stop: () => void
  destroy: () => void
}

/**
 * Sets the simulation up on the canvas, or returns null when the browser lacks
 * WebGL2 or cannot render to floating point textures. The caller then simply
 * shows no steam.
 */
export function createSteamSimulation(canvas: HTMLCanvasElement): SteamSimulation | null {
  const context = canvas.getContext('webgl2', {
    alpha: true,
    premultipliedAlpha: true,
    antialias: false,
    depth: false,
    stencil: false,
    powerPreference: 'low-power',
  })
  if (!context || !context.getExtension('EXT_color_buffer_float')) return null
  const gl: WebGL2RenderingContext = context

  const vertexShader = compile(gl.VERTEX_SHADER, VERTEX)
  const programs = {
    advect: link(ADVECT),
    forces: link(FORCES),
    emit: link(EMIT),
    curl: link(CURL),
    vorticity: link(VORTICITY),
    divergence: link(DIVERGENCE),
    pressure: link(PRESSURE),
    gradient: link(GRADIENT),
    scale: link(SCALE),
    display: link(DISPLAY),
  }
  const vertexArray = gl.createVertexArray()
  gl.bindVertexArray(vertexArray)
  gl.disable(gl.BLEND)

  let velocity: DoubleTarget
  let dye: DoubleTarget
  let pressure: DoubleTarget
  let divergence: Target
  let curl: Target
  let simTexel: [number, number] = [0, 0]
  let dyeTexel: [number, number] = [0, 0]
  let aspect = 1
  let frame = 0
  let last = 0
  let elapsed = 0
  let running = false
  const gust = { start: 0, length: 0, angle: 0, height: 0.5 }
  // The direction the steam rises in, as an angle on the screen, and the one
  // it is turning towards.
  let upAngle = Math.PI / 2
  let upTarget = upAngle

  function compile(type: number, source: string): WebGLShader {
    const shader = gl.createShader(type)!
    gl.shaderSource(shader, source)
    gl.compileShader(shader)
    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
      throw new Error(gl.getShaderInfoLog(shader) ?? 'Steam shader failed to compile')
    }
    return shader
  }

  function link(fragment: string): Program {
    const program = gl.createProgram()
    gl.attachShader(program, vertexShader)
    gl.attachShader(program, compile(gl.FRAGMENT_SHADER, fragment))
    gl.linkProgram(program)
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      throw new Error(gl.getProgramInfoLog(program) ?? 'Steam program failed to link')
    }
    const locations = new Map<string, WebGLUniformLocation | null>()
    return {
      use: () => gl.useProgram(program),
      uniform: (name) => {
        if (!locations.has(name)) locations.set(name, gl.getUniformLocation(program, name))
        return locations.get(name)!
      },
    }
  }

  function createTarget(width: number, height: number, format: number, internal: number): Target {
    const texture = gl.createTexture()
    gl.bindTexture(gl.TEXTURE_2D, texture)
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR)
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR)
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE)
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE)
    gl.texImage2D(gl.TEXTURE_2D, 0, internal, width, height, 0, format, gl.HALF_FLOAT, null)
    const framebuffer = gl.createFramebuffer()
    gl.bindFramebuffer(gl.FRAMEBUFFER, framebuffer)
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, texture, 0)
    gl.viewport(0, 0, width, height)
    gl.clearColor(0, 0, 0, 0)
    gl.clear(gl.COLOR_BUFFER_BIT)
    return { texture, framebuffer, width, height }
  }

  function createDouble(width: number, height: number, format: number, internal: number): DoubleTarget {
    const pair = {
      read: createTarget(width, height, format, internal),
      write: createTarget(width, height, format, internal),
      swap: () => {
        const read = pair.read
        pair.read = pair.write
        pair.write = read
      },
    }
    return pair
  }

  function releaseTarget(target: Target) {
    gl.deleteTexture(target.texture)
    gl.deleteFramebuffer(target.framebuffer)
  }

  function releaseTargets() {
    if (!velocity) return
    for (const pair of [velocity, dye, pressure]) {
      releaseTarget(pair.read)
      releaseTarget(pair.write)
    }
    releaseTarget(divergence)
    releaseTarget(curl)
  }

  function resize() {
    // The steam is soft, so a canvas at half the CSS size scaled up looks the same.
    const width = Math.max(1, Math.round(canvas.clientWidth / 2))
    const height = Math.max(1, Math.round(canvas.clientHeight / 2))
    canvas.width = width
    canvas.height = height
    aspect = width / height

    releaseTargets()
    const simW = Math.max(16, Math.round(SIM_HEIGHT * aspect))
    const dyeW = Math.max(16, Math.round(DYE_HEIGHT * aspect))
    velocity = createDouble(simW, SIM_HEIGHT, gl.RG, gl.RG16F)
    pressure = createDouble(simW, SIM_HEIGHT, gl.RED, gl.R16F)
    divergence = createTarget(simW, SIM_HEIGHT, gl.RED, gl.R16F)
    curl = createTarget(simW, SIM_HEIGHT, gl.RED, gl.R16F)
    dye = createDouble(dyeW, DYE_HEIGHT, gl.RG, gl.RG16F)
    simTexel = [1 / simW, 1 / SIM_HEIGHT]
    dyeTexel = [1 / dyeW, 1 / DYE_HEIGHT]
  }

  function bindTexture(program: Program, name: string, unit: number, target: Target) {
    gl.activeTexture(gl.TEXTURE0 + unit)
    gl.bindTexture(gl.TEXTURE_2D, target.texture)
    gl.uniform1i(program.uniform(name), unit)
  }

  function draw(target: Target | null) {
    if (target) {
      gl.bindFramebuffer(gl.FRAMEBUFFER, target.framebuffer)
      gl.viewport(0, 0, target.width, target.height)
    } else {
      gl.bindFramebuffer(gl.FRAMEBUFFER, null)
      gl.viewport(0, 0, canvas.width, canvas.height)
    }
    gl.drawArrays(gl.TRIANGLES, 0, 3)
  }

  function setUp(x: number, y: number) {
    upTarget = Math.atan2(y, x)
  }

  function step(dt: number) {
    const time = elapsed
    // Turn along the shorter way round, quickly but not in a jump.
    const turn = Math.atan2(Math.sin(upTarget - upAngle), Math.cos(upTarget - upAngle))
    upAngle += turn * Math.min(1, dt * 2.5)
    const up: [number, number] = [Math.cos(upAngle), Math.sin(upAngle)]
    const side: [number, number] = [up[1], -up[0]]
    // The pot stands just beyond the edge that is down, under the centre: walk
    // from the centre against the up direction until the edge is reached.
    const halfWidth = aspect / 2
    const toEdge = Math.min(
      Math.abs(up[0]) > 1e-4 ? halfWidth / Math.abs(up[0]) : Infinity,
      Math.abs(up[1]) > 1e-4 ? 0.5 / Math.abs(up[1]) : Infinity,
    )
    const reach = 2 * toEdge
    // The pot's steam does not leave from one fixed point: its centre and
    // direction sway a little, as they would in a kitchen's moving air.
    const drift = 0.03 * Math.sin(time * 0.37) + 0.018 * Math.sin(time * 1.13)
    const back = toEdge + TUNING.sourceOffset
    const source: [number, number] = [
      halfWidth - up[0] * back + side[0] * drift,
      0.5 - up[1] * back + side[1] * drift,
    ]
    // A gust swells and fades within its short life; after it, the air stays
    // quiet for a while before the next one arrives from somewhere else.
    if (time >= gust.start + gust.length) {
      gust.start = time + between(TUNING.gustPause)
      gust.length = between(TUNING.gustLength)
      gust.angle = (Math.random() < 0.5 ? 0 : Math.PI) + (Math.random() - 0.5) * 1.2
      gust.height = between([0.25, 0.9])
    }
    const progress = (time - gust.start) / gust.length
    const gustStrength = progress > 0 && progress < 1 ? TUNING.gust * Math.sin(Math.PI * progress) ** 2 : 0
    // Steam leaves a pot in uneven puffs rather than a steady stream, and each
    // puff pushes the air as well as carrying vapour, so it rolls up as it rises.
    const wave = 0.5 + 0.5 * Math.sin(time * 1.3) * Math.sin(time * 0.71 + 1)
    const simmer = Math.min(1, Math.max(0, (time - TUNING.simmerAfter) / TUNING.simmerFade))
    const strength = 1 - (1 - TUNING.simmerLevel) * (simmer * simmer * (3 - 2 * simmer))
    const puff = (0.2 + 1.3 * wave * wave) * strength
    const sway = TUNING.jet * (0.25 * Math.sin(time * 0.53) + 0.12 * Math.sin(time * 1.7))

    const forces = programs.forces
    forces.use()
    bindTexture(forces, 'uVelocity', 0, velocity.read)
    bindTexture(forces, 'uDye', 1, dye.read)
    gl.uniform2f(forces.uniform('uSource'), source[0], source[1])
    gl.uniform2f(forces.uniform('uUp'), up[0], up[1])
    gl.uniform1f(forces.uniform('uReach'), reach)
    gl.uniform1f(forces.uniform('uAspect'), aspect)
    gl.uniform1f(forces.uniform('uRadius'), TUNING.sourceRadius)
    gl.uniform2f(
      forces.uniform('uJet'),
      (side[0] * sway + up[0] * TUNING.jet) * puff,
      (side[1] * sway + up[1] * TUNING.jet) * puff,
    )
    gl.uniform1f(forces.uniform('uBuoyancy'), TUNING.buoyancy)
    gl.uniform1f(forces.uniform('uTurbulence'), TUNING.turbulence)
    gl.uniform1f(forces.uniform('uBreeze'), TUNING.breeze)
    gl.uniform2f(
      forces.uniform('uGust'),
      gustStrength * Math.cos(gust.angle),
      gustStrength * Math.sin(gust.angle),
    )
    gl.uniform1f(forces.uniform('uGustHeight'), gust.height)
    gl.uniform1f(forces.uniform('uTime'), time)
    gl.uniform1f(forces.uniform('uDt'), dt)
    draw(velocity.write)
    velocity.swap()

    programs.curl.use()
    bindTexture(programs.curl, 'uVelocity', 0, velocity.read)
    gl.uniform2f(programs.curl.uniform('uTexel'), ...simTexel)
    draw(curl)

    const vorticity = programs.vorticity
    vorticity.use()
    bindTexture(vorticity, 'uVelocity', 0, velocity.read)
    bindTexture(vorticity, 'uCurl', 1, curl)
    gl.uniform2f(vorticity.uniform('uTexel'), ...simTexel)
    gl.uniform1f(vorticity.uniform('uCurlStrength'), TUNING.curl)
    gl.uniform1f(vorticity.uniform('uDt'), dt)
    draw(velocity.write)
    velocity.swap()

    programs.divergence.use()
    bindTexture(programs.divergence, 'uVelocity', 0, velocity.read)
    gl.uniform2f(programs.divergence.uniform('uTexel'), ...simTexel)
    draw(divergence)

    // The last frame's pressure, faded, is a good first guess for this one.
    programs.scale.use()
    bindTexture(programs.scale, 'uSource', 0, pressure.read)
    gl.uniform1f(programs.scale.uniform('uFactor'), 0.8)
    draw(pressure.write)
    pressure.swap()

    const solve = programs.pressure
    solve.use()
    gl.uniform2f(solve.uniform('uTexel'), ...simTexel)
    bindTexture(solve, 'uDivergence', 1, divergence)
    for (let i = 0; i < PRESSURE_ITERATIONS; i++) {
      bindTexture(solve, 'uPressure', 0, pressure.read)
      draw(pressure.write)
      pressure.swap()
    }

    const gradient = programs.gradient
    gradient.use()
    bindTexture(gradient, 'uPressure', 0, pressure.read)
    bindTexture(gradient, 'uVelocity', 1, velocity.read)
    gl.uniform2f(gradient.uniform('uTexel'), ...simTexel)
    draw(velocity.write)
    velocity.swap()

    const advect = programs.advect
    advect.use()
    gl.uniform2f(advect.uniform('uSimTexel'), ...simTexel)
    gl.uniform1f(advect.uniform('uDt'), dt)
    bindTexture(advect, 'uVelocity', 0, velocity.read)
    bindTexture(advect, 'uSource', 1, velocity.read)
    const damping = TUNING.velocityDissipation
    gl.uniform4f(advect.uniform('uDissipation'), damping, damping, 0, 0)
    draw(velocity.write)
    velocity.swap()

    bindTexture(advect, 'uVelocity', 0, velocity.read)
    bindTexture(advect, 'uSource', 1, dye.read)
    gl.uniform4f(advect.uniform('uDissipation'), TUNING.dyeDissipation, TUNING.cooling, 0, 0)
    draw(dye.write)
    dye.swap()

    const emit = programs.emit
    emit.use()
    bindTexture(emit, 'uDye', 0, dye.read)
    gl.uniform2f(emit.uniform('uSource'), source[0], source[1])
    gl.uniform2f(emit.uniform('uUp'), up[0], up[1])
    gl.uniform1f(emit.uniform('uReach'), reach)
    gl.uniform1f(emit.uniform('uAspect'), aspect)
    gl.uniform1f(emit.uniform('uRadius'), TUNING.sourceRadius)
    gl.uniform1f(emit.uniform('uAmount'), TUNING.emission)
    gl.uniform1f(emit.uniform('uHeat'), TUNING.heat)
    gl.uniform1f(emit.uniform('uPuff'), puff)
    const threads = [
      -0.08 + 0.04 * Math.sin(time * 0.41),
      0.04 * Math.sin(time * 0.29 + 2),
      0.08 + 0.04 * Math.sin(time * 0.47 + 4),
    ].flatMap((offset) => [source[0] + side[0] * offset, source[1] + side[1] * offset])
    gl.uniform2fv(emit.uniform('uThreads'), threads)
    gl.uniform3f(
      emit.uniform('uThreadPuff'),
      puff * threadPuff(time, 0.9, 0),
      puff * threadPuff(time, 1.17, 2.1),
      puff * threadPuff(time, 0.77, 4.3),
    )
    gl.uniform1f(emit.uniform('uTopFade'), TUNING.topFade)
    gl.uniform1f(emit.uniform('uDt'), dt)
    draw(dye.write)
    dye.swap()
  }

  function between(range: readonly number[]): number {
    const [low = 0, high = low] = range
    return low + Math.random() * (high - low)
  }

  function threadPuff(time: number, rate: number, phase: number): number {
    const wave = 0.5 + 0.5 * Math.sin(time * rate + phase) * Math.sin(time * rate * 0.61 + phase * 1.7)
    return 0.15 + 1.7 * wave * wave
  }

  function render() {
    const display = programs.display
    display.use()
    bindTexture(display, 'uDye', 0, dye.read)
    gl.uniform2f(display.uniform('uDyeTexel'), ...dyeTexel)
    gl.uniform1f(display.uniform('uOpacity'), TUNING.opacity)
    gl.uniform1f(display.uniform('uAspect'), aspect)
    gl.uniform1f(display.uniform('uAmbient'), TUNING.ambient)
    gl.uniform1f(display.uniform('uLight'), TUNING.light)
    gl.uniform1f(display.uniform('uShadow'), TUNING.shadow)
    gl.uniform1f(display.uniform('uFalloff'), TUNING.lightFalloff)
    draw(null)
  }

  function tick(now: number) {
    if (!running) return
    frame = requestAnimationFrame(tick)
    const delta = now - last
    if (delta < FRAME_INTERVAL_MS - 2) return
    last = now
    const dt = Math.min(delta / 1000, 1 / 20)
    elapsed += dt
    step(dt)
    render()
  }

  function start() {
    if (running) return
    running = true
    last = performance.now()
    frame = requestAnimationFrame(tick)
  }

  function stop() {
    running = false
    cancelAnimationFrame(frame)
  }

  function destroy() {
    stop()
    releaseTargets()
    gl.getExtension('WEBGL_lose_context')?.loseContext()
  }

  resize()
  return { resize, setUp, start, stop, destroy }
}
