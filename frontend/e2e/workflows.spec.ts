import { test, expect } from '@playwright/test';

test('create dataset, promote trace, compare baseline and inspect history', async ({ page, request }) => {
  const errors: string[] = [];
  page.on('pageerror', e => errors.push(e.message));
  const response = await request.post('/api/backend/v1/traces', { data: {
    user_input: '退款政策是什么？', model_output: '7天内退款', model: 'e2e',
  }});
  expect(response.ok()).toBeTruthy();
  const { trace_id } = await response.json();
  await page.goto('/traces');
  await page.getByRole('link', { name: `${trace_id.slice(0, 12)}...` }).click();
  await expect(page.getByText('7天内退款', { exact: true })).toBeVisible();
  await page.goto('/datasets');
  await page.getByLabel('名称', { exact: true }).fill(`browser-${Date.now()}`);
  await page.getByRole('button', { name: '创建数据集' }).click();
  await expect(page.getByRole('button', { name: '保存用例' })).toBeVisible();
  await page.getByLabel('来源 Trace ID（可选）').fill(trace_id);
  await page.getByRole('button', { name: '保存用例' }).click();
  await expect(page.getByRole('listitem').filter({ hasText: '退款政策是什么？' })).toBeVisible();
  await page.getByLabel('要求真实裁判（关闭仅用于演示）').uncheck();
  await page.getByLabel('保存为基线').check();
  await page.getByRole('button', { name: '开始评测' }).click();
  const report = page.locator('pre');
  await expect(report).toContainText('"gate_passed": true');
  await page.getByLabel('保存为基线').uncheck();
  await page.getByLabel('比较基线').selectOption({ index: 1 });
  await page.getByLabel('版本标识').fill('browser-candidate');
  await page.getByRole('button', { name: '开始评测' }).click();
  await expect(report).toContainText('browser-candidate');
  await expect(report).toContainText('"score_delta": 0');
  await expect(report).toContainText('"gate_passed": true');
  await page.getByLabel('要求真实裁判（关闭仅用于演示）').check();
  await page.getByRole('button', { name: '开始评测' }).click();
  await expect(report).toContainText('"gate_passed": false');
  await expect(report).toContainText('Real judge required but unavailable');
  await page.reload();
  await page.getByLabel('选择数据集').selectOption({ index: 1 });
  await page.getByRole('heading', { name: '历史报告', exact: true }).locator('..').getByRole('button').first().click();
  await expect(page.locator('pre')).toContainText('"gate_passed": false');
  expect(errors).toEqual([]);
});

test('invalid JSON and invalid dataset names show errors', async ({ page }) => {
  await page.goto('/datasets');
  await page.getByRole('button', { name: '创建数据集' }).click();
  await expect(page.locator('p[role=alert]')).toBeVisible();
  await page.getByLabel('名称', { exact: true }).fill(`invalid-${Date.now()}`);
  await page.getByRole('button', { name: '创建数据集' }).click();
  await page.getByLabel('用例 JSON').fill('{invalid');
  await page.getByRole('button', { name: '保存用例' }).click();
  await expect(page.locator('p[role=alert]')).toContainText('SyntaxError');
});

test('backend failure is visible to the user', async ({ page }) => {
  await page.route('**/api/backend/v1/datasets', route => route.fulfill({
    status: 502, contentType: 'application/json', body: JSON.stringify({ detail: 'Backend unavailable or timed out' }),
  }));
  await page.goto('/datasets');
  await expect(page.locator('p[role=alert]')).toContainText('Backend unavailable');
});
