# Testing Guide for Open Codex GUI

## Overview

This project uses Playwright for end-to-end testing to ensure all user workflows function correctly across different browsers.

## Test Structure

```
tests/
├── e2e/                          # End-to-end tests
│   ├── project-management.spec.ts  # Project CRUD operations
│   ├── chat-session.spec.ts       # Chat functionality
│   └── agent-config.spec.ts       # Agent configuration
└── README.md                     # This file
```

## Prerequisites

1. **Docker Desktop** must be running (for backend sandbox containers)
2. **Backend server** running on port 8000
3. **Frontend dev server** running on port 5173
4. **Node.js** 18+ and **npm** installed

## Installation

```bash
# Install Playwright and dependencies
npm install -D @playwright/test

# Install browser binaries
npx playwright install
```

## Running Tests

### Run all E2E tests
```bash
npx playwright test
```

### Run specific test file
```bash
npx playwright test tests/e2e/project-management.spec.ts
```

### Run in headed mode (see browser)
```bash
npx playwright test --headed
```

### Run in debug mode
```bash
npx playwright test --debug
```

### Run specific browser
```bash
# Chromium only
npx playwright test --project=chromium

# Firefox only
npx playwright test --project=firefox

# Mobile Chrome
npx playwright test --project="Mobile Chrome"
```

### Run with UI
```bash
npx playwright test --ui
```

## Viewing Test Results

### Generate HTML report
```bash
npx playwright show-report
```

The report will open in your browser showing:
- Test pass/fail status
- Screenshots of failures
- Execution traces
- Test duration

### View traces
```bash
npx playwright show-trace trace.zip
```

## Writing New Tests

### Test Structure
```typescript
import { test, expect } from '@playwright/test';

test.describe('Feature Name', () => {
  test.beforeEach(async ({ page }) => {
    // Setup before each test
    await page.goto('/');
  });

  test('TEST-001: Description', async ({ page }) => {
    // Test implementation
    await page.click('button:has-text("Click Me")');
    await expect(page.locator('text=Success')).toBeVisible();
  });
});
```

### Best Practices

1. **Use semantic locators**
   ```typescript
   // Good
   await page.click('button:has-text("Submit")');
   await expect(page.locator('[data-testid="result"]')).toBeVisible();

   // Avoid
   await page.click('.btn-primary.large');
   ```

2. **Wait for elements properly**
   ```typescript
   // Wait for element to be visible
   await expect(page.locator('text=Success')).toBeVisible();

   // Wait for navigation
   await page.waitForURL(/\/projects\/[a-f0-9-]+$/);

   // Wait for network request
   await page.waitForResponse(resp => resp.url().includes('/api/v1/projects'));
   ```

3. **Use descriptive test IDs**
   ```typescript
   test('PM-001: Create new project', async ({ page }) => {
     // PM = Project Management
     // 001 = Test number
   });
   ```

4. **Clean up after tests**
   ```typescript
   test.afterEach(async ({ page }) => {
     // Clean up if needed
   });
   ```

5. **Handle async operations**
   ```typescript
   // Wait for element
   await page.waitForSelector('.loading', { state: 'hidden' });

   // Wait for timeout (use sparingly)
   await page.waitForTimeout(1000);
   ```

## Test Coverage

### Project Management (PM-)
- PM-001: Create new project
- PM-002: View project details
- PM-003: Delete project
- PM-004: Project list persistence
- PM-005: Back navigation from project

### Chat Session (CS-)
- CS-001: Quick start chat
- CS-002: Send message in existing session
- CS-003: View conversation history
- CS-004: Navigate between sessions
- CS-005: Send button disabled for empty input
- CS-006: Auto-scroll to latest message

### Agent Configuration (AC-)
- AC-001: Change LLM provider and model
- AC-002: Enable and disable tools
- AC-003: Update system instructions
- AC-004: Change environment type
- AC-005: Adjust temperature slider
- AC-006: Reset changes
- AC-007: Collapsible panel behavior

## Debugging Tests

### Take screenshots
```typescript
await page.screenshot({ path: 'screenshot.png' });
```

### Pause execution
```typescript
await page.pause(); // Opens Playwright Inspector
```

### Console output
```typescript
page.on('console', msg => console.log(msg.text()));
```

### Network requests
```typescript
page.on('request', request => console.log('>>', request.method(), request.url()));
page.on('response', response => console.log('<<', response.status(), response.url()));
```

## CI/CD Integration

The tests are configured to run in CI environments:

```yaml
# .github/workflows/test.yml
- name: Run Playwright tests
  run: npx playwright test
  env:
    CI: true

- name: Upload test results
  if: always()
  uses: actions/upload-artifact@v3
  with:
    name: playwright-report
    path: playwright-report/
```

## Troubleshooting

### Tests failing due to timing
- Increase timeout: `test.setTimeout(60000)`
- Add explicit waits: `await page.waitForTimeout(1000)`
- Wait for network idle: `await page.waitForLoadState('networkidle')`

### Element not found
- Check if element is in iframe: `page.frameLocator('iframe').locator(...)`
- Wait for element: `await page.waitForSelector('selector')`
- Check visibility: `await expect(locator).toBeVisible()`

### WebSocket issues
- Wait for WebSocket connection: `await page.waitForTimeout(2000)`
- Listen to WebSocket events in browser console

### Container issues
- Ensure Docker is running
- Check backend logs
- Verify container creation in Docker Desktop

## Performance Tips

1. **Run tests in parallel** (default)
   ```bash
   npx playwright test --workers=4
   ```

2. **Skip slow tests during development**
   ```typescript
   test.skip('slow test', async ({ page }) => {
     // ...
   });
   ```

3. **Focus on specific tests**
   ```typescript
   test.only('focus on this test', async ({ page }) => {
     // ...
   });
   ```

4. **Use test fixtures for common setup**
   ```typescript
   const test = base.extend({
     loggedInPage: async ({ page }, use) => {
       await page.goto('/login');
       // ... login logic
       await use(page);
     },
   });
   ```

## Resources

- [Playwright Documentation](https://playwright.dev/)
- [Playwright Best Practices](https://playwright.dev/docs/best-practices)
- [Playwright API Reference](https://playwright.dev/docs/api/class-playwright)
- [Test Plan Document](../../../TEST_PLAN.md)
