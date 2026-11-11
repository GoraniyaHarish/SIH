// Browser-level role journey smoke test. Credentials are supplied only by the CI job.
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE)
const baseURL = process.env.PRAMANA_BASE_URL || 'http://localhost:3000'
const password = process.env.PRAMANA_DEMO_PASSWORD
if (!password || password.length < 12) throw new Error('A private CI demo password is required')

const cases = [
  {
    role: 'learner',
    email: 'learner.iss@pramana.gov.in',
    staff: false,
    admin: false,
    routes: ['/app/gaps', '/app/courses', '/app/assessment'],
  },
  {
    role: 'manager',
    email: 'manager@pramana.gov.in',
    staff: true,
    admin: false,
    routes: ['/app/analytics'],
  },
  {
    role: 'assessor',
    email: 'assessor@pramana.gov.in',
    staff: true,
    admin: false,
    routes: ['/app/analytics'],
  },
  {
    role: 'admin',
    email: 'admin@pramana.gov.in',
    staff: true,
    admin: true,
    routes: ['/app/admin', '/app/admin/users', '/app/admin/framework', '/app/admin/integrations'],
  },
]

const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] })
const failures = []
try {
  for (const scenario of cases) {
    const context = await browser.newContext()
    const page = await context.newPage()
    page.on('pageerror', (error) => failures.push(`${scenario.role}: ${error.message}`))

    await page.goto(`${baseURL}/login`, { waitUntil: 'domcontentloaded' })
    await page.getByLabel('Email').fill(scenario.email)
    await page.getByLabel('Password').fill(password)
    await page.getByRole('button', { name: 'Sign in', exact: true }).click()
    await page.waitForURL((url) => url.pathname === '/app', { timeout: 15000 })
    await page.locator('.topbar h1').waitFor()
    if ((await page.locator('.topbar h1').textContent())?.trim() !== 'Dashboard') {\n      throw new Error(`${scenario.role}: dashboard did not render`)\n    }

    const staffLink = page.getByRole('link', { name: 'Training intelligence' })
    const adminLink = page.getByRole('link', { name: 'Admin workspace' })
    if ((await staffLink.count()) !== (scenario.staff ? 1 : 0)) {
      throw new Error(`${scenario.role}: incorrect staff navigation visibility`)
    }
    if ((await adminLink.count()) !== (scenario.admin ? 1 : 0)) {
      throw new Error(`${scenario.role}: incorrect admin navigation visibility`)
    }

    for (const route of scenario.routes) {
      await page.goto(`${baseURL}${route}`, { waitUntil: 'domcontentloaded' })
      if (scenario.role !== 'admin' && route === '/app/analytics') {
        await page.locator('.topbar h1').waitFor()
        if ((await page.locator('.topbar h1').textContent())?.trim() !== 'Training intelligence') {\n          throw new Error(`${scenario.role}: analytics page did not render`)\n        }
      } else if (scenario.role === 'admin') {
        const expected = {
          '/app/admin': 'Admin workspace',
          '/app/admin/users': 'People & roles',
          '/app/admin/framework': 'Competency framework',
          '/app/admin/integrations': 'Integrations & system',
        }[route]
        await page.locator('.topbar h1').waitFor()
        if ((await page.locator('.topbar h1').textContent())?.trim() !== expected) {\n          throw new Error(`${scenario.role}: ${route} did not render the expected page`)\n        }
      } else {
        await page.getByRole('heading').first().waitFor()
      }
    }

    if (!scenario.admin) {
      await page.goto(`${baseURL}/app/admin`, { waitUntil: 'domcontentloaded' })
      await page.waitForURL((url) => url.pathname === '/app', { timeout: 10000 })
      if ((await adminLink.count()) !== 0) {
        throw new Error(`${scenario.role}: admin-only route was not blocked`)
      }
    }

    console.log(`PASS browser journey: ${scenario.role}`)
    await context.close()
  }
  if (failures.length) throw new Error(failures.join('\n'))
  console.log('PASS all four authenticated role journeys; no uncaught browser exceptions')
} finally {
  await browser.close()
}
