import { test, expect } from '@playwright/test';

test.describe('Project Management', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to home page before each test
    await page.goto('/');
  });

  test('PM-001: Create new project', async ({ page }) => {
    // Click create project button
    await page.click('button:has-text("Create Project")');

    // Fill in project form
    await page.fill('input[name="name"]', 'Test Project');
    await page.fill('textarea[name="description"]', 'This is a test project for E2E testing');

    // Submit form
    await page.click('button:has-text("Create")');

    // Wait for modal to close and project to appear
    await page.waitForTimeout(1000);

    // Verify project appears in list
    await expect(page.locator('text=Test Project')).toBeVisible();
    await expect(page.locator('text=This is a test project for E2E testing')).toBeVisible();
  });

  test('PM-002: View project details', async ({ page }) => {
    // Create a project first
    await page.click('button:has-text("Create Project")');
    await page.fill('input[name="name"]', 'View Test Project');
    await page.fill('textarea[name="description"]', 'Project for viewing test');
    await page.click('button:has-text("Create")');
    await page.waitForTimeout(1000);

    // Click on the project card
    await page.click('text=View Test Project');

    // Verify landing page displays
    await expect(page).toHaveURL(/\/projects\/[a-f0-9-]+$/);
    await expect(page.locator('h1:has-text("View Test Project")')).toBeVisible();
    await expect(page.locator('text=Project for viewing test')).toBeVisible();

    // Verify quick start input is visible
    await expect(page.locator('textarea[placeholder*="How can I help"]')).toBeVisible();

    // Verify sidebar sections exist
    await expect(page.locator('text=Agent Configuration')).toBeVisible();
    await expect(page.locator('text=Project Files')).toBeVisible();
  });

  test('PM-003: Delete project', async ({ page }) => {
    // Create a project first
    await page.click('button:has-text("Create Project")');
    await page.fill('input[name="name"]', 'Delete Test Project');
    await page.fill('textarea[name="description"]', 'Project for deletion test');
    await page.click('button:has-text("Create")');
    await page.waitForTimeout(1000);

    // Locate the project card and click delete button
    const projectCard = page.locator('.project-card:has-text("Delete Test Project")');
    const deleteBtn = projectCard.locator('button.delete-btn');

    // Click delete button
    await deleteBtn.click();

    // Wait for project to be removed
    await page.waitForTimeout(1000);

    // Verify project no longer appears
    await expect(page.locator('text=Delete Test Project')).not.toBeVisible();
  });

  test('PM-004: Project list persistence', async ({ page }) => {
    // Create a project
    await page.click('button:has-text("Create Project")');
    await page.fill('input[name="name"]', 'Persistence Test Project');
    await page.fill('textarea[name="description"]', 'Testing data persistence');
    await page.click('button:has-text("Create")');
    await page.waitForTimeout(1000);

    // Reload page
    await page.reload();

    // Verify project still appears
    await expect(page.locator('text=Persistence Test Project')).toBeVisible();
  });

  test('PM-005: Back navigation from project', async ({ page }) => {
    // Create and navigate to a project
    await page.click('button:has-text("Create Project")');
    await page.fill('input[name="name"]', 'Navigation Test');
    await page.fill('textarea[name="description"]', 'Test navigation');
    await page.click('button:has-text("Create")');
    await page.waitForTimeout(1000);
    await page.click('text=Navigation Test');

    // Click back button
    await page.click('button:has-text("Back to Projects")');

    // Verify back at home page
    await expect(page).toHaveURL('/');
    await expect(page.locator('h1:has-text("Projects")')).toBeVisible();
  });
});
