import { test, expect } from '@playwright/test';

test.describe('Chat Session', () => {
  let projectId: string;

  test.beforeEach(async ({ page }) => {
    // Create a project before each test
    await page.goto('/');
    await page.click('button:has-text("Create Project")');
    await page.fill('input[name="name"]', 'Chat Test Project');
    await page.fill('textarea[name="description"]', 'Project for chat testing');
    await page.click('button:has-text("Create")');
    await page.waitForTimeout(1000);

    // Navigate to project landing page
    await page.click('text=Chat Test Project');
    await page.waitForTimeout(500);

    // Extract project ID from URL
    const url = page.url();
    const match = url.match(/\/projects\/([a-f0-9-]+)/);
    if (match) {
      projectId = match[1];
    }
  });

  test('CS-001: Quick start chat', async ({ page }) => {
    // Type message in quick start input
    await page.fill('textarea[placeholder*="How can I help"]', 'Hello, this is a test message');

    // Click send button
    await page.click('button.send-btn');

    // Verify redirected to chat session
    await expect(page).toHaveURL(/\/projects\/[a-f0-9-]+\/chat\/[a-f0-9-]+$/);

    // Wait for message to appear
    await page.waitForTimeout(2000);

    // Verify user message appears
    await expect(page.locator('text=Hello, this is a test message')).toBeVisible();

    // Verify session name appears in header
    await expect(page.locator('.session-title')).toContainText('Chat');
  });

  test('CS-002: Send message in existing session', async ({ page }) => {
    // Create a session first using quick start
    await page.fill('textarea[placeholder*="How can I help"]', 'First message');
    await page.click('button.send-btn');
    await page.waitForTimeout(2000);

    // Now send another message
    await page.fill('.chat-input', 'Second message in the same session');
    await page.press('.chat-input', 'Enter');

    // Wait for message to appear
    await page.waitForTimeout(1000);

    // Verify both messages appear
    await expect(page.locator('text=First message')).toBeVisible();
    await expect(page.locator('text=Second message in the same session')).toBeVisible();
  });

  test('CS-003: View conversation history', async ({ page }) => {
    // Create a session with multiple messages
    await page.fill('textarea[placeholder*="How can I help"]', 'Message 1');
    await page.click('button.send-btn');
    await page.waitForTimeout(2000);

    await page.fill('.chat-input', 'Message 2');
    await page.press('.chat-input', 'Enter');
    await page.waitForTimeout(1000);

    await page.fill('.chat-input', 'Message 3');
    await page.press('.chat-input', 'Enter');
    await page.waitForTimeout(1000);

    // Reload page
    await page.reload();
    await page.waitForTimeout(1000);

    // Verify all messages still visible
    await expect(page.locator('text=Message 1')).toBeVisible();
    await expect(page.locator('text=Message 2')).toBeVisible();
    await expect(page.locator('text=Message 3')).toBeVisible();
  });

  test('CS-004: Navigate between sessions', async ({ page }) => {
    // Create first session
    await page.fill('textarea[placeholder*="How can I help"]', 'First session message');
    await page.click('button.send-btn');
    await page.waitForTimeout(2000);

    // Go back to project
    await page.click('button:has-text("Back to Project")');
    await page.waitForTimeout(500);

    // Create second session
    await page.fill('textarea[placeholder*="How can I help"]', 'Second session message');
    await page.click('button.send-btn');
    await page.waitForTimeout(2000);

    // Go back to project
    await page.click('button:has-text("Back to Project")');
    await page.waitForTimeout(500);

    // Verify two sessions appear in list
    const sessions = page.locator('.session-card');
    await expect(sessions).toHaveCount(2);

    // Click on first session
    await sessions.first().click();
    await page.waitForTimeout(1000);

    // Verify first session message appears
    await expect(page.locator('text=First session message')).toBeVisible();
    await expect(page.locator('text=Second session message')).not.toBeVisible();
  });

  test('CS-005: Send button disabled for empty input', async ({ page }) => {
    // Create a session
    await page.fill('textarea[placeholder*="How can I help"]', 'Test');
    await page.click('button.send-btn');
    await page.waitForTimeout(2000);

    // Verify send button is disabled when input is empty
    const sendBtn = page.locator('.chat-input-wrapper .send-btn');
    await expect(sendBtn).toBeDisabled();

    // Type message
    await page.fill('.chat-input', 'New message');

    // Verify send button is now enabled
    await expect(sendBtn).toBeEnabled();

    // Clear input
    await page.fill('.chat-input', '');

    // Verify send button is disabled again
    await expect(sendBtn).toBeDisabled();
  });

  test('CS-006: Auto-scroll to latest message', async ({ page }) => {
    // Create session and send multiple messages
    await page.fill('textarea[placeholder*="How can I help"]', 'Start conversation');
    await page.click('button.send-btn');
    await page.waitForTimeout(2000);

    // Send several more messages
    for (let i = 1; i <= 5; i++) {
      await page.fill('.chat-input', `Message ${i}`);
      await page.press('.chat-input', 'Enter');
      await page.waitForTimeout(800);
    }

    // Check that the last message is visible (scrolled into view)
    await expect(page.locator('text=Message 5')).toBeVisible();
  });
});
