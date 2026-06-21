import { test, expect } from '@playwright/test'

test.describe('用例选中与执行按钮状态', () => {
  test.beforeEach(async ({ page }) => {
    const now = new Date().toISOString()
    await page.route((url) => url.pathname === '/api/projects', (route) => {
      if (route.request().method() === 'GET') {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([
            { id: 1, name: '测试项目', git_url: 'https://example.com/repo.git', case_dir: '.', status: 1, created_at: now },
          ]),
        })
      } else {
        route.continue()
      }
    })
    await page.route('**/api/projects/1/cases/tree', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          tree: {
            name: 'root', type: 'dir', children: [
              {
                name: 'test_dir', type: 'dir', total_cases: 2, children: [
                  {
                    name: 'test_sample.py', type: 'file', case_count: 2,
                    cases: [
                      { nodeid: 'node_1', name: 'test_case_one', description: '第一个测试用例' },
                      { nodeid: 'node_2', name: 'test_case_two', description: '第二个测试用例' },
                    ],
                  },
                ],
              },
            ],
          },
          flat: [
            { nodeid: 'node_1', name: 'test_case_one' },
            { nodeid: 'node_2', name: 'test_case_two' },
          ],
        }),
      })
    })
    await page.goto('/#/projects/1')
    await page.waitForSelector('.tree-case', { timeout: 5000 })
  })

  test('初始状态：未选择用例时按钮应置灰禁用', async ({ page }) => {
    const runBtn = page.locator('.run-actions .el-button--success').first()
    await expect(runBtn).toBeDisabled()
    await expect(runBtn).toContainText('执行选中 (0)')
  })

  test('点击用例行后按钮应变为可用', async ({ page }) => {
    const firstCase = page.locator('.tree-case').first()
    await firstCase.click()
    const runBtn = page.locator('.run-actions .el-button--success').first()
    await expect(runBtn).toBeEnabled()
    await expect(runBtn).toContainText('执行选中 (1)')
  })

  test('点击两个用例后数量应显示为2', async ({ page }) => {
    const cases = page.locator('.tree-case')
    await cases.nth(0).click()
    await cases.nth(1).click()
    const runBtn = page.locator('.run-actions .el-button--success').first()
    await expect(runBtn).toBeEnabled()
    await expect(runBtn).toContainText('执行选中 (2)')
  })

  test('取消勾选后按钮应恢复置灰', async ({ page }) => {
    const firstCase = page.locator('.tree-case').first()
    await firstCase.click()
    const runBtn = page.locator('.run-actions .el-button--success').first()
    await expect(runBtn).toContainText('执行选中 (1)')
    await firstCase.click()
    await expect(runBtn).toBeDisabled()
    await expect(runBtn).toContainText('执行选中 (0)')
  })

  test('点击全选按钮后应选中所有用例', async ({ page }) => {
    await page.locator('button:has-text("全选")').click()
    const runBtn = page.locator('.run-actions .el-button--success').first()
    await expect(runBtn).toBeEnabled()
    await expect(runBtn).toContainText('执行选中 (2)')
  })

  test('点击取消按钮后应清空所有选中', async ({ page }) => {
    await page.locator('button:has-text("全选")').click()
    await page.locator('button:has-text("取消")').click()
    const runBtn = page.locator('.run-actions .el-button--success').first()
    await expect(runBtn).toBeDisabled()
    await expect(runBtn).toContainText('执行选中 (0)')
  })
})

test.describe('任务管理', () => {
  /** Register a single catch-all route for all /api/projects/1/tasks* requests */
  async function mockTasksApi(page, now, opts = {}) {
    const { empty = false, taskCreated = null, afterDelete = null } = opts

    await page.route('**/api/projects/1/tasks**', (route) => {
      const url = route.request().url()
      const method = route.request().method()

      // runs/all
      if (url.includes('/runs/all')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
      }

      // GET with page param → tasks list
      if (method === 'GET' && url.includes('?page=')) {
        let items
        if (afterDelete) {
          items = []
        } else if (empty) {
          items = []
        } else {
          items = [
            { id: 1, project_id: 1, name: '冒烟测试', description: '关键流程', nodeids: ['n1', 'n2'], created_at: now, updated_at: now },
            { id: 2, project_id: 1, name: '回归测试', description: '', nodeids: ['n1'], created_at: now, updated_at: now },
          ]
        }
        if (taskCreated) {
          items = [{ id: 1, project_id: 1, name: '新增任务', description: '', nodeids: ['n1'], created_at: now, updated_at: now }]
        }
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ items, total: items.length, page: 1, page_size: 8 }),
        })
      }

      // POST → create task
      if (method === 'POST') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ id: 1, name: '新增任务', description: '', nodeids: ['n1'] }),
        })
      }

      // DELETE /tasks/1
      if (method === 'DELETE' && url.includes('/tasks/1')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: '{}' })
      }

      route.continue()
    })
  }

  test.beforeEach(async ({ page }) => {
    const now = new Date().toISOString()
    await page.route((url) => url.pathname === '/api/projects', (route) => {
      if (route.request().method() === 'GET') {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([
            { id: 1, name: '测试项目', git_url: 'https://example.com/repo.git', case_dir: '.', status: 1, created_at: now },
          ]),
        })
      } else {
        route.continue()
      }
    })
    await page.route('**/api/projects/1/cases/tree', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          tree: {
            name: 'root', type: 'dir', children: [
              {
                name: 'test_sample.py', type: 'file', case_count: 2,
                cases: [
                  { nodeid: 'n1', name: '测试登录', description: '' },
                  { nodeid: 'n2', name: '测试注册', description: '' },
                ],
              },
            ],
          },
          flat: [
            { nodeid: 'n1', name: '测试登录' },
            { nodeid: 'n2', name: '测试注册' },
          ],
        }),
      })
    })
    await page.unroute('**/api/projects/1/tasks**')
  })

  test('任务列表加载并展示数据', async ({ page }) => {
    const now = new Date().toISOString()
    await mockTasksApi(page, now, { empty: false })

    await page.goto('/#/projects/1')
    await page.waitForSelector('.el-tabs', { timeout: 5000 })
    await page.locator('.el-tabs .el-tabs__item').nth(1).click()
    await page.waitForTimeout(2000)

    const rows = page.locator('.el-table__body tr')
    await expect(rows.first()).toContainText('冒烟测试')
    await expect(rows.nth(1)).toContainText('回归测试')
  })

  test('创建任务后列表应刷新显示新任务', async ({ page }) => {
    const now = new Date().toISOString()
    let created = false

    // Override mock with dynamic behavior
    await page.route('**/api/projects/1/tasks**', (route) => {
      const url = route.request().url()
      const method = route.request().method()

      if (url.includes('/runs/all')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
      }

      if (method === 'GET' && url.includes('?page=')) {
        const items = created
          ? [{ id: 1, project_id: 1, name: '新增任务', description: '', nodeids: ['n1'], created_at: now, updated_at: now }]
          : []
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ items, total: items.length, page: 1, page_size: 8 }),
        })
      }

      if (method === 'POST') {
        created = true
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ id: 1, name: '新增任务', description: '', nodeids: ['n1'] }),
        })
      }

      route.continue()
    })

    await page.goto('/#/projects/1')
    await page.waitForSelector('.el-tabs', { timeout: 5000 })
    await page.locator('.el-tabs .el-tabs__item').nth(1).click()
    await page.waitForTimeout(1500)
    await expect(page.getByText('暂无任务')).toBeVisible()

    await page.locator('button:has-text("创建任务")').click()
    await page.waitForSelector('.el-dialog', { timeout: 3000 })
    await page.locator('.el-dialog .el-input__inner').first().fill('新增任务')

    await page.locator('.el-dialog .sn-case').first().click()
    await page.waitForTimeout(300)

    await page.locator('.el-dialog .el-button--primary').click()
    await page.waitForTimeout(2000)

    await expect(page.locator('.el-table__body tr')).toHaveCount(1)
    await expect(page.locator('.el-table__body')).toContainText('新增任务')
  })

  test('删除任务后列表应更新', async ({ page }) => {
    const now = new Date().toISOString()
    let deleted = false

    await page.route('**/api/projects/1/tasks**', (route) => {
      const url = route.request().url()
      const method = route.request().method()

      if (url.includes('/runs/all')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
      }

      if (method === 'GET' && url.includes('?page=')) {
        const items = deleted ? [] : [{ id: 1, project_id: 1, name: '待删除任务', description: '', nodeids: ['n1'], created_at: now, updated_at: now }]
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ items, total: items.length, page: 1, page_size: 8 }),
        })
      }

      if (method === 'DELETE' && url.includes('/tasks/1')) {
        deleted = true
        return route.fulfill({ status: 200, contentType: 'application/json', body: '{}' })
      }

      route.continue()
    })

    await page.goto('/#/projects/1')
    await page.waitForSelector('.el-tabs', { timeout: 5000 })
    await page.locator('.el-tabs .el-tabs__item').nth(1).click()
    await page.waitForTimeout(1500)
    await expect(page.locator('.el-table__body tr')).toHaveCount(1)
    await expect(page.locator('.el-table__body')).toContainText('待删除任务')

    await page.locator('button:has-text("删除")').click()
    await page.locator('.el-popconfirm button:has-text("确定")').click()
    await page.waitForTimeout(2000)

    await expect(page.getByText('暂无任务')).toBeVisible()
  })
})
