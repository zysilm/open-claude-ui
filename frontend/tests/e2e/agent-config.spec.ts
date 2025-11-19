import { test, expect } from '@playwright/test';

test.describe('Agent Configuration', () => {
  test.beforeEach(async ({ page }) => {
    // Create a project and navigate to landing page
    await page.goto('/');
    await page.click('button:has-text("Create Project")');
    await page.fill('input[name="name"]', 'Agent Config Test');
    await page.fill('textarea[name="description"]', 'Testing agent configuration');
    await page.click('button:has-text("Create")');
    await page.waitForTimeout(1000);
    await page.click('text=Agent Config Test');
    await page.waitForTimeout(500);

    // Expand agent config panel
    await page.click('text=Agent Configuration');
    await page.waitForTimeout(300);
  });

  test('AC-001: Change LLM provider and model', async ({ page }) => {
    // Click on general tab (should be default)
    await page.click('.tab:has-text("General")');

    // Change provider
    await page.selectOption('.select-input[value*="openai"]', 'anthropic');
    await page.waitForTimeout(500);

    // Verify model dropdown updated
    const modelSelect = page.locator('.form-section:has-text("Model") .select-input');
    await expect(modelSelect).toContainText('claude');

    // Change model
    await modelSelect.selectOption({ index: 1 });

    // Save configuration
    await page.click('button:has-text("Save Changes")');
    await page.waitForTimeout(1000);

    // Verify unsaved indicator disappears
    await expect(page.locator('.unsaved-indicator')).not.toBeVisible();
  });

  test('AC-002: Enable and disable tools', async ({ page }) => {
    // Click on tools tab
    await page.click('.tab:has-text("Tools")');
    await page.waitForTimeout(300);

    // Verify tool cards are visible
    await expect(page.locator('.tool-card:has-text("Bash")')).toBeVisible();
    await expect(page.locator('.tool-card:has-text("File Read")')).toBeVisible();

    // Click on Bash tool to toggle
    const bashTool = page.locator('.tool-card:has-text("Bash")');
    await bashTool.click();

    // Verify tool is enabled (has enabled class)
    await expect(bashTool).toHaveClass(/enabled/);

    // Enable File Read tool
    const fileReadTool = page.locator('.tool-card:has-text("File Read")');
    await fileReadTool.click();

    // Save configuration
    await page.click('button:has-text("Save Changes")');
    await page.waitForTimeout(1000);

    // Reload page and verify tools are still enabled
    await page.reload();
    await page.waitForTimeout(500);
    await page.click('text=Agent Configuration');
    await page.waitForTimeout(300);
    await page.click('.tab:has-text("Tools")');

    await expect(page.locator('.tool-card:has-text("Bash")').locator('input[type="checkbox"]')).toBeChecked();
    await expect(page.locator('.tool-card:has-text("File Read")').locator('input[type="checkbox"]')).toBeChecked();
  });

  test('AC-003: Update system instructions', async ({ page }) => {
    // Click on instructions tab
    await page.click('.tab:has-text("Instructions")');
    await page.waitForTimeout(300);

    // Enter custom instructions
    const instructions = 'You are a helpful Python programming assistant. Focus on writing clean, well-documented code.';
    await page.fill('.instructions-textarea', instructions);

    // Verify unsaved changes indicator appears
    await expect(page.locator('.unsaved-indicator')).toBeVisible();

    // Save configuration
    await page.click('button:has-text("Save Changes")');
    await page.waitForTimeout(1000);

    // Reload and verify instructions persist
    await page.reload();
    await page.waitForTimeout(500);
    await page.click('text=Agent Configuration');
    await page.waitForTimeout(300);
    await page.click('.tab:has-text("Instructions")');

    await expect(page.locator('.instructions-textarea')).toHaveValue(instructions);
  });

  test('AC-004: Change environment type', async ({ page }) => {
    // Click on general tab
    await page.click('.tab:has-text("General")');

    // Click on Python 3.12 environment
    await page.click('.environment-card:has-text("Python 3.12")');

    // Verify it gets selected
    await expect(page.locator('.environment-card:has-text("Python 3.12")')).toHaveClass(/selected/);

    // Save configuration
    await page.click('button:has-text("Save Changes")');
    await page.waitForTimeout(1000);

    // Reload and verify selection persists
    await page.reload();
    await page.waitForTimeout(500);
    await page.click('text=Agent Configuration');
    await page.waitForTimeout(300);
    await page.click('.tab:has-text("General")');

    await expect(page.locator('.environment-card:has-text("Python 3.12")')).toHaveClass(/selected/);
  });

  test('AC-005: Adjust temperature slider', async ({ page }) => {
    // Click on general tab
    await page.click('.tab:has-text("General")');

    // Find temperature slider
    const slider = page.locator('.form-section:has-text("Temperature") .slider');

    // Get current value
    const currentValue = await page.locator('.slider-value').first().textContent();

    // Move slider
    await slider.fill('0.9');

    // Verify value changed
    await expect(page.locator('.slider-value').first()).toHaveText('0.9');

    // Save configuration
    await page.click('button:has-text("Save Changes")');
    await page.waitForTimeout(1000);
  });

  test('AC-006: Reset changes', async ({ page }) => {
    // Click on instructions tab
    await page.click('.tab:has-text("Instructions")');

    // Enter some instructions
    await page.fill('.instructions-textarea', 'Test instructions that will be reset');

    // Verify unsaved changes indicator appears
    await expect(page.locator('.unsaved-indicator')).toBeVisible();

    // Click reset button
    await page.click('button:has-text("Reset")');

    // Verify instructions cleared
    await expect(page.locator('.instructions-textarea')).toHaveValue('');

    // Verify unsaved indicator gone
    await expect(page.locator('.unsaved-indicator')).not.toBeVisible();
  });

  test('AC-007: Collapsible panel behavior', async ({ page }) => {
    // Panel should be expanded after clicking in beforeEach

    // Verify panel content is visible
    await expect(page.locator('.config-tabs')).toBeVisible();

    // Click header to collapse
    await page.click('.sidebar-section-header:has-text("Agent Configuration")');
    await page.waitForTimeout(300);

    // Verify content is hidden
    await expect(page.locator('.config-tabs')).not.toBeVisible();

    // Click again to expand
    await page.click('.sidebar-section-header:has-text("Agent Configuration")');
    await page.waitForTimeout(300);

    // Verify content is visible again
    await expect(page.locator('.config-tabs')).toBeVisible();
  });
});
