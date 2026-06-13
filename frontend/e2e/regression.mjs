/**
 * Full-chain E2E regression for smart-investment-research.
 *
 * Prerequisites:
 * - Backend on 8099
 * - Frontend on 5199 with VITE_USE_MOCK=false
 *
 * Usage: npm run test:e2e
 */

import { chromium } from 'playwright'

const BASE_URL = process.env.E2E_BASE_URL ?? 'http://127.0.0.1:5199'
const API_BASE = process.env.E2E_API_BASE ?? `${BASE_URL}/api`
const CLEANUP = (process.env.E2E_CLEANUP ?? 'true').toLowerCase() !== 'false'

const VIEWPORTS = [
  { name: 'desktop', width: 1440, height: 900 },
  { name: 'mobile', width: 390, height: 844 },
]

const E2E_MARKER = `E2E-${Date.now()}`

function assertNoOverflow(metrics, viewport) {
  if (metrics.bodyScrollWidth > metrics.viewportWidth + 1) {
    throw new Error(
      `[${viewport.name}] horizontal overflow: bodyScrollWidth=${metrics.bodyScrollWidth}, viewport=${metrics.viewportWidth}`,
    )
  }
  if (metrics.docScrollWidth > metrics.viewportWidth + 1) {
    throw new Error(
      `[${viewport.name}] horizontal overflow: docScrollWidth=${metrics.docScrollWidth}, viewport=${metrics.viewportWidth}`,
    )
  }
}

async function readOverflow(page) {
  return page.evaluate(() => ({
    bodyScrollWidth: document.body.scrollWidth,
    docScrollWidth: document.documentElement.scrollWidth,
    viewportWidth: window.innerWidth,
  }))
}

async function waitForAssistant(page) {
  await page.locator('.message.assistant').last().waitFor({ state: 'visible', timeout: 60_000 })
}

async function runFlow(page, viewport) {
  const isNarrow = viewport.width <= 1080

  await page.goto(`${BASE_URL}/client`, { waitUntil: 'networkidle' })
  assertNoOverflow(await readOverflow(page), viewport)

  if (!isNarrow) {
    await page.getByRole('button', { name: '新建会话' }).click()
  }
  const textarea = page.locator('.composer textarea')
  await textarea.fill(`${E2E_MARKER} 宁德时代基本面怎么样`)
  await page.locator('.composer .send').click()
  await waitForAssistant(page)
  assertNoOverflow(await readOverflow(page), viewport)

  if (!isNarrow) {
    await page.locator('#historySearch').fill(E2E_MARKER)
    await page.waitForTimeout(300)
    const historyRows = page.locator('.chat-row')
    if ((await historyRows.count()) === 0) {
      throw new Error(`[${viewport.name}] history search returned no rows for marker ${E2E_MARKER}`)
    }
  }

  await page.getByRole('button', { name: '数据说明' }).click()
  await page.getByText('RAG 状态').waitFor({ state: 'visible' })
  assertNoOverflow(await readOverflow(page), viewport)

  if (!isNarrow) {
    await page.getByRole('button', { name: '对话' }).click()
    await page.getByRole('button', { name: '管理端' }).click()
  } else {
    await page.goto(`${BASE_URL}/admin`, { waitUntil: 'networkidle' })
  }
  await page.getByRole('heading', { name: 'Trace 链路' }).waitFor({ state: 'visible', timeout: 60_000 })

  const traceStep = page.locator('.trace-step').first()
  await traceStep.click()
  const jsonButton = traceStep.getByRole('button', { name: '查看完整 JSON' })
  if (await jsonButton.isVisible()) {
    await jsonButton.click()
    await page.getByRole('dialog').waitFor({ state: 'visible' })
    await page.getByRole('button', { name: '关闭' }).click()
  }
  assertNoOverflow(await readOverflow(page), viewport)

  await page.getByRole('button', { name: '系统设置' }).click()
  await page.getByText('Prompt 模块').waitFor({ state: 'visible' })
  const pageText = await page.locator('body').innerText()
  if (/sk-[A-Za-z0-9]/.test(pageText) || pageText.includes('Bearer ')) {
    throw new Error(`[${viewport.name}] possible secret leak on settings page`)
  }
  assertNoOverflow(await readOverflow(page), viewport)

  if (!isNarrow) {
    await page.getByRole('button', { name: '客户端' }).click()
  } else {
    await page.goto(`${BASE_URL}/client`, { waitUntil: 'networkidle' })
  }
  await textarea.fill(`${E2E_MARKER} 买入价100情景价120持仓1000测算收益`)
  await page.locator('.composer .send').click()
  await waitForAssistant(page)
  assertNoOverflow(await readOverflow(page), viewport)
}

async function cleanupSessions() {
  if (!CLEANUP) return
  const listRes = await fetch(`${API_BASE}/sessions`)
  if (!listRes.ok) return
  const payload = await listRes.json()
  const sessions = payload?.data?.items ?? payload?.data?.sessions ?? []
  for (const session of sessions) {
    const title = session.title ?? ''
    if (title.includes(E2E_MARKER)) {
      await fetch(`${API_BASE}/sessions/${session.id}`, { method: 'DELETE' })
    }
  }
}

async function main() {
  const browser = await chromium.launch({ headless: true })

  try {
    for (const viewport of VIEWPORTS) {
      const context = await browser.newContext({ viewport })
      const page = await context.newPage()
      const apiResponses = []
      page.on('response', (response) => {
        const url = response.url()
        if (url.includes('/api/') && !url.includes('/api/health')) {
          apiResponses.push(url)
        }
      })

      await runFlow(page, viewport)

      const proxied = apiResponses.some((url) => url.startsWith(BASE_URL))
      if (!proxied && process.env.E2E_SKIP_PROXY_CHECK !== 'true') {
        throw new Error(`[${viewport.name}] no /api requests observed via frontend proxy`)
      }

      await context.close()
      console.log(`PASS viewport ${viewport.name} (${viewport.width}x${viewport.height})`)
    }

    await cleanupSessions()
    console.log('E2E regression passed')
  } catch (error) {
    await cleanupSessions()
    console.error(error)
    process.exitCode = 1
  } finally {
    await browser.close()
  }
}

main()
