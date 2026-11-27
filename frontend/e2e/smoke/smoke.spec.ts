/**
 * Visits every main page as each demo account and records what goes wrong:
 * uncaught errors, console errors, API calls that fail, and text that still
 * shows an untranslated message key. Every page is also saved as a full-page
 * screenshot under test-results/smoke for a person to look through. A test
 * fails only on uncaught errors and failed API calls; console noise and
 * suspicious text are collected in issues.json next to the screenshots.
 */
import { createHmac } from 'node:crypto'
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { expect, test, type Page } from '@playwright/test'

const API = process.env.E2E_API_URL ?? 'http://localhost:3000'
const OUT = 'test-results/smoke'

interface Account {
  /** A short label for the test title and the screenshot folder. */
  name: string
  /** The e-mail address, or `system` for the system user. */
  login: string
  password: string
  /** The system user must use TOTP, so it signs in through the API. */
  totp?: boolean
}

const ACCOUNTS: Account[] = [
  {
    name: 'system',
    login: 'system',
    password: process.env.E2E_ADMIN_PASSWORD ?? '',
    totp: true,
  },
  { name: 'anna', login: 'anna@example.com', password: process.env.E2E_ANNA_PASSWORD ?? 'anna-dev-password' },
  { name: 'ben', login: 'ben@example.com', password: process.env.E2E_BEN_PASSWORD ?? 'ben-dev-password' },
]

interface Issue {
  page: string
  kind: 'pageerror' | 'console' | 'response' | 'text'
  detail: string
}

/**
 * Answers the app expects and handles with its own message: a legal page
 * that was never published, and the editor of a recipe the account may not
 * change, which shows a "you can't edit this" page.
 */
const EXPECTED_RESPONSES: [number, RegExp][] = [
  [404, /\/api\/v1\/public\/legal\/(imprint|privacy)/],
  [403, /\/api\/v1\/web\/recipes\/[^/]+\/edit$/],
]

function expected(status: number, url: string): boolean {
  return EXPECTED_RESPONSES.some(([code, pattern]) => code === status && pattern.test(new URL(url).pathname))
}

const ADMIN_TABS = [
  'host', 'general', 'users', 'groups', 'auth', 'agents',
  'catalogue', 'legal', 'storage', 'operations', 'notifications',
]
const RESOURCE_TABS = ['units', 'tags', 'categories', 'families', 'equipment']

const CSRF = { 'X-Requested-With': 'cuisine' }
// Outside test-results, which a fresh run may clear, and ignored with
// node_modules: the secret only belongs to the local dev database.
const TOTP_SECRET_FILE = 'node_modules/.cache/e2e-system-totp-secret'

/** RFC 6238 code for a base32 secret, as an authenticator app shows it. */
function totpCode(secret: string): string {
  const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567'
  let bits = ''
  for (const char of secret.replace(/=+$/, '').toUpperCase()) {
    bits += alphabet.indexOf(char).toString(2).padStart(5, '0')
  }
  const key = Buffer.from(bits.match(/.{8}/g)!.map((byte) => parseInt(byte, 2)))
  const counter = Buffer.alloc(8)
  counter.writeBigUInt64BE(BigInt(Math.floor(Date.now() / 30_000)))
  const hmac = createHmac('sha1', key).update(counter).digest()
  const offset = hmac[hmac.length - 1]! & 0x0f
  const value = (hmac.readUInt32BE(offset) & 0x7fffffff) % 1_000_000
  return value.toString().padStart(6, '0')
}

/** Signs the system user in through the API, enrolling TOTP on the first
 * run and keeping the secret for later runs. The session cookie lands in
 * the page's context, so the app is signed in afterwards. */
async function signInWithTotp(page: Page, account: Account): Promise<void> {
  const login = await page.request.post(`${API}/api/v1/auth/login`, {
    headers: CSRF,
    data: { login: account.login, password: account.password },
  })
  expect(login.ok(), await login.text()).toBe(true)
  const body = (await login.json()) as { status: string; partial_token: string | null; setup_token: string | null }
  if (body.setup_token) {
    const bearer = { ...CSRF, Authorization: `Bearer ${body.setup_token}` }
    const enrol = await page.request.post(`${API}/api/v1/web/users/me/totp/enroll`, { headers: bearer })
    expect(enrol.ok(), await enrol.text()).toBe(true)
    const { secret } = (await enrol.json()) as { secret: string }
    mkdirSync('node_modules/.cache', { recursive: true })
    writeFileSync(TOTP_SECRET_FILE, secret)
    const confirm = await page.request.post(`${API}/api/v1/web/users/me/totp/confirm`, {
      headers: bearer,
      data: { code: totpCode(secret) },
    })
    expect(confirm.ok(), await confirm.text()).toBe(true)
  } else if (body.partial_token) {
    expect(existsSync(TOTP_SECRET_FILE), 'TOTP is set up but its secret is unknown; reset the dev database').toBe(true)
    const secret = readFileSync(TOTP_SECRET_FILE, 'utf8').trim()
    const totp = await page.request.post(`${API}/api/v1/auth/login/totp`, {
      headers: CSRF,
      data: { partial_token: body.partial_token, code: totpCode(secret), trust_device: false },
    })
    expect(totp.ok(), await totp.text()).toBe(true)
  }
  await page.goto('/')
  await page.waitForLoadState('load')
  await acceptPrivacyIfAsked(page)
  await acknowledgeSystemUserWarning(page)
}

/** The system account's warning dialog blocks the app once per tab until
 * it is acknowledged; the acknowledgement lasts for the rest of the tab. */
async function acknowledgeSystemUserWarning(page: Page): Promise<void> {
  const understood = page.getByRole('button', { name: /understood|verstanden/i })
  if (await understood.first().isVisible({ timeout: 2_000 }).catch(() => false)) {
    await understood.first().click()
  }
}

async function signIn(page: Page, account: Account): Promise<void> {
  if (account.totp) return signInWithTotp(page, account)
  await page.goto('/login')
  await page.locator('#login-email').fill(account.login)
  await page.locator('#login-password').fill(account.password)
  await page.locator('button[type="submit"]').click()
  await page.waitForURL((url) => !url.pathname.startsWith('/login'), { timeout: 20_000 })
  await acceptPrivacyIfAsked(page)
}

/** The privacy statement blocks the app until it is acknowledged. */
async function acceptPrivacyIfAsked(page: Page): Promise<void> {
  const accept = page.getByRole('button', { name: /accept|akzeptieren|zustimmen/i })
  if (await accept.first().isVisible({ timeout: 2_000 }).catch(() => false)) {
    await accept.first().click()
    await page.waitForTimeout(1_000)
  }
}

async function firstId(page: Page, path: string): Promise<string | null> {
  const response = await page.request.get(`${API}/api/v1/web/${path}`)
  if (!response.ok()) return null
  const body = (await response.json()) as { items?: { id: string }[] }
  return body.items?.[0]?.id ?? null
}

async function settle(page: Page): Promise<void> {
  // Pages with a live shopping list keep a stream open, so the network never
  // goes idle; a fixed pause after load is enough for the first render.
  await page.waitForLoadState('load')
  await page.waitForTimeout(1_500)
}

for (const account of ACCOUNTS) {
  test(`pages as ${account.name}`, async ({ page }, info) => {
    test.skip(!account.password, `no password for ${account.name}`)
    const issues: Issue[] = []
    let current = 'login'
    page.on('pageerror', (error) => issues.push({ page: current, kind: 'pageerror', detail: error.message }))
    page.on('console', (message) => {
      // The browser also logs every failed request; those are covered by the
      // response check above, expected ones included, so only the rest count.
      if (message.type() === 'error' && !message.text().startsWith('Failed to load resource')) {
        issues.push({ page: current, kind: 'console', detail: message.text() })
      }
    })
    page.on('response', (response) => {
      const url = response.url()
      if (url.includes('/api/') && response.status() >= 400 && response.status() !== 401 && !expected(response.status(), url)) {
        issues.push({ page: current, kind: 'response', detail: `${response.status()} ${response.request().method()} ${url}` })
      }
    })

    const dir = `${OUT}/${info.project.name}/${account.name}`
    mkdirSync(dir, { recursive: true })

    await signIn(page, account)

    const recipe = await firstId(page, 'recipes?limit=1')
    const ingredient = await firstId(page, 'ingredients?limit=1')
    const list = await firstId(page, 'shopping-lists')

    const pages: [string, string][] = [
      ['home', '/'],
      ['recipes', '/recipes'],
      ['drafts', '/recipes/drafts'],
      ['recipe-new', '/recipes/new'],
      ['meal-plan', '/meal-plan'],
      ['shopping', '/shopping'],
      ['cooked', '/cooked'],
      ['ingredients', '/ingredients'],
      ['kitchen', '/kitchen'],
      ['household', '/household'],
      ['account', '/account'],
      ['legal-privacy', '/legal/privacy'],
      ...RESOURCE_TABS.map((tab): [string, string] => [`resources-${tab}`, `/resources/${tab}`]),
    ]
    if (recipe) {
      pages.push(['recipe', `/recipes/${recipe}`], ['recipe-edit', `/recipes/${recipe}/edit`], ['cook', `/recipes/${recipe}/cook`])
    }
    if (ingredient) pages.push(['ingredient', `/ingredients/${ingredient}`])
    if (list) pages.push(['shopping-list', `/shopping/${list}`])
    if (account.name === 'system') {
      pages.push(...ADMIN_TABS.map((tab): [string, string] => [`admin-${tab}`, `/admin/${tab}`]))
    }

    for (const [name, path] of pages) {
      current = name
      await page.goto(path)
      await settle(page)
      const text = await page.locator('body').innerText()
      // An untranslated key shows as a dotted lower-camel path such as
      // "recipes.editor.title".
      for (const match of text.match(/\b[a-z][a-zA-Z]+(?:\.[a-z][a-zA-Z0-9]+){2,}\b/g) ?? []) {
        issues.push({ page: name, kind: 'text', detail: `possible missing translation: ${match}` })
      }
      await page.screenshot({ path: `${dir}/${name}.png`, fullPage: true })
    }

    // The account page keeps its tabs out of the URL, so they are clicked.
    current = 'account-tabs'
    await page.goto('/account')
    await settle(page)
    const tabs = page.getByRole('tab')
    const count = await tabs.count()
    for (let index = 0; index < count; index += 1) {
      const tab = tabs.nth(index)
      const label = ((await tab.innerText()) || `tab${index}`).trim().toLowerCase().replace(/\W+/g, '-')
      current = `account-${label}`
      await tab.click()
      await page.waitForTimeout(1_000)
      await page.screenshot({ path: `${dir}/account-${label}.png`, fullPage: true })
    }

    writeFileSync(`${dir}/issues.json`, JSON.stringify(issues, null, 2))
    const fatal = issues.filter((issue) => issue.kind === 'pageerror' || issue.kind === 'response')
    expect(fatal, JSON.stringify(fatal, null, 2)).toEqual([])
  })
}
