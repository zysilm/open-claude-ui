# Open Codex GUI - Comprehensive Test Plan

## 1. Test Strategy

### 1.1 Test Levels
- **Unit Tests**: Individual functions and components
- **Integration Tests**: API endpoints, database operations, agent execution
- **End-to-End Tests**: Full user workflows with Playwright
- **Performance Tests**: Load testing, container pool management
- **Security Tests**: Input validation, sandbox isolation

### 1.2 Test Environment
- **Backend**: Python 3.13, Poetry, pytest, pytest-asyncio
- **Frontend**: React 18, Vitest, React Testing Library
- **E2E**: Playwright with Chromium, Firefox, Safari
- **CI/CD**: GitHub Actions (future)

---

## 2. Backend Tests

### 2.1 Unit Tests (`tests/unit/`)

#### 2.1.1 Database Models (`test_models.py`)
- [x] Project creation with valid data
- [x] Project validation (name, description)
- [x] Chat session creation and linking to project
- [x] Message creation with different roles
- [x] Agent configuration CRUD operations
- [x] File upload metadata storage

#### 2.1.2 LLM Providers (`test_llm_providers.py`)
- [ ] OpenAI provider initialization
- [ ] Anthropic provider initialization
- [ ] Azure provider initialization
- [ ] Message formatting for each provider
- [ ] Streaming response handling
- [ ] Error handling for API failures
- [ ] Token counting and limits

#### 2.1.3 Agent Core (`test_agent.py`)
- [ ] ReAct agent initialization
- [ ] Thought generation
- [ ] Action parsing
- [ ] Tool selection logic
- [ ] Observation processing
- [ ] Final answer generation
- [ ] Max iterations handling
- [ ] Error recovery

#### 2.1.4 Sandbox Container (`test_container.py`)
- [ ] Container creation
- [ ] Command execution
- [ ] File read/write operations
- [ ] Container cleanup
- [ ] Resource limits enforcement
- [ ] Network isolation
- [ ] Workspace mounting

#### 2.1.5 Tools (`test_tools.py`)
- [ ] Bash tool execution
- [ ] File read tool with various file types
- [ ] File write tool with permissions
- [ ] File edit tool with replacements
- [ ] Tool error handling
- [ ] Tool timeout handling

### 2.2 Integration Tests (`tests/integration/`)

#### 2.2.1 API Endpoints (`test_api_projects.py`, etc.)
- [ ] `POST /api/v1/projects` - Create project
- [ ] `GET /api/v1/projects` - List projects
- [ ] `GET /api/v1/projects/{id}` - Get project
- [ ] `PUT /api/v1/projects/{id}` - Update project
- [ ] `DELETE /api/v1/projects/{id}` - Delete project
- [ ] `POST /api/v1/projects/{id}/sessions` - Create chat session
- [ ] `GET /api/v1/sessions/{id}` - Get session
- [ ] `POST /api/v1/sessions/{id}/messages` - Send message
- [ ] `GET /api/v1/sessions/{id}/messages` - List messages
- [ ] `GET /api/v1/projects/{id}/agent-config` - Get agent config
- [ ] `PUT /api/v1/projects/{id}/agent-config` - Update agent config
- [ ] `POST /api/v1/files` - Upload file
- [ ] `GET /api/v1/files/{id}` - Download file
- [ ] `DELETE /api/v1/files/{id}` - Delete file

#### 2.2.2 WebSocket Chat (`test_websocket.py`)
- [ ] WebSocket connection establishment
- [ ] User message sending
- [ ] Simple LLM response streaming
- [ ] Agent mode with tool execution
- [ ] Thought/action/observation streaming
- [ ] Error handling during streaming
- [ ] Connection disconnection cleanup
- [ ] Concurrent connections

#### 2.2.3 Container Pool Management (`test_container_pool.py`)
- [ ] Container creation and reuse
- [ ] Container pool size limits
- [ ] Orphaned container cleanup
- [ ] Container lifecycle management
- [ ] Multiple sessions with different containers
- [ ] Container resource monitoring
- [ ] Workspace isolation between sessions

#### 2.2.4 Agent Execution Flow (`test_agent_execution.py`)
- [ ] Simple code execution task
- [ ] File manipulation task
- [ ] Multi-step reasoning task
- [ ] Error recovery during execution
- [ ] Tool chaining
- [ ] Max iteration limits
- [ ] Conversation history usage

#### 2.2.5 Database Operations (`test_database.py`)
- [ ] Database migrations
- [ ] Concurrent writes
- [ ] Transaction rollbacks
- [ ] Cascade deletes
- [ ] Query performance
- [ ] Connection pooling

---

## 3. Frontend Tests

### 3.1 Unit Tests (Vitest + React Testing Library)

#### 3.1.1 Component Tests (`src/components/**/__tests__/`)
- [ ] ProjectList rendering
- [ ] ProjectCard interactions
- [ ] NewProjectModal form validation
- [ ] ProjectLandingPage layout
- [ ] ChatSessionPage message display
- [ ] AgentConfigPanel configuration
- [ ] FilePanel upload/download

#### 3.1.2 Store Tests (`src/stores/__tests__/`)
- [ ] Chat store state management
- [ ] Agent actions tracking
- [ ] Active session management

#### 3.1.3 API Service Tests (`src/services/__tests__/`)
- [ ] API client request formatting
- [ ] Error handling
- [ ] Response parsing

### 3.2 Integration Tests
- [ ] React Query data fetching
- [ ] WebSocket connection management
- [ ] Route navigation
- [ ] Form submissions

---

## 4. End-to-End Tests (Playwright)

### 4.1 User Workflows (`tests/e2e/`)

#### 4.1.1 Project Management (`test_project_management.spec.ts`)
- [ ] **PM-001**: Create new project
  - Navigate to home
  - Click "Create Project"
  - Fill form (name, description)
  - Submit and verify project appears

- [ ] **PM-002**: View project details
  - Click on project card
  - Verify landing page displays
  - Verify project name and description

- [ ] **PM-003**: Delete project
  - Click delete button on project card
  - Confirm deletion
  - Verify project removed from list

#### 4.1.2 Chat Session (`test_chat_session.spec.ts`)
- [ ] **CS-001**: Quick start chat
  - Navigate to project landing page
  - Type message in quick start input
  - Click send
  - Verify redirected to chat session
  - Verify message appears

- [ ] **CS-002**: Send message in existing session
  - Open existing chat session
  - Type and send message
  - Verify message appears
  - Verify response streaming

- [ ] **CS-003**: View conversation history
  - Open chat session with history
  - Verify all messages displayed
  - Verify scroll to bottom

- [ ] **CS-004**: Navigate between sessions
  - Go to project landing
  - Click on different sessions
  - Verify correct history loads

#### 4.1.3 Agent Configuration (`test_agent_config.spec.ts`)
- [ ] **AC-001**: Change LLM provider
  - Open agent config panel
  - Change provider dropdown
  - Verify model list updates
  - Save configuration

- [ ] **AC-002**: Enable/disable tools
  - Open tools tab
  - Toggle tool checkboxes
  - Save configuration
  - Verify changes persist

- [ ] **AC-003**: Update system instructions
  - Open instructions tab
  - Enter custom instructions
  - Save configuration
  - Verify persisted

- [ ] **AC-004**: Apply template
  - Open templates tab
  - Click "Apply Template"
  - Confirm override
  - Verify configuration updated

#### 4.1.4 File Management (`test_file_management.spec.ts`)
- [ ] **FM-001**: Upload file
  - Open file panel
  - Click upload
  - Select file
  - Verify file appears in list

- [ ] **FM-002**: Download file
  - Click download button on file
  - Verify file downloads

- [ ] **FM-003**: Delete file
  - Click delete button
  - Confirm deletion
  - Verify file removed

#### 4.1.5 Agent Execution (`test_agent_execution.spec.ts`)
- [ ] **AE-001**: Execute bash command
  - Enable bash tool
  - Send message: "Run 'echo hello world'"
  - Verify thinking steps displayed
  - Verify action block shows bash tool
  - Verify observation shows output
  - Verify final answer

- [ ] **AE-002**: Write and read file
  - Enable file tools
  - Send: "Create a file test.py with 'print(hello)'"
  - Verify file_write action
  - Send: "Read the test.py file"
  - Verify file_read action
  - Verify correct content displayed

- [ ] **AE-003**: Multi-step task
  - Enable all tools
  - Send: "Create a Python script that prints numbers 1-10, save it, and run it"
  - Verify multiple tool uses
  - Verify final output

#### 4.1.6 Error Handling (`test_error_handling.spec.ts`)
- [ ] **EH-001**: Network error recovery
  - Disconnect network
  - Try to send message
  - Verify error message
  - Reconnect network
  - Retry successfully

- [ ] **EH-002**: Invalid input handling
  - Submit empty message
  - Verify send button disabled
  - Submit very long message (>10000 chars)
  - Verify handled gracefully

- [ ] **EH-003**: Container creation failure
  - Stop Docker
  - Try to use agent mode
  - Verify clear error message
  - Start Docker
  - Verify recovery

#### 4.1.7 UI/UX Tests (`test_ui_ux.spec.ts`)
- [ ] **UI-001**: Responsive design
  - Test on mobile viewport (375px)
  - Test on tablet viewport (768px)
  - Test on desktop viewport (1920px)
  - Verify layout adapts

- [ ] **UI-002**: Theme consistency
  - Verify all pages use light theme
  - Verify consistent colors
  - Verify button hover states

- [ ] **UI-003**: Collapsible panels
  - Expand/collapse agent config
  - Expand/collapse file panel
  - Verify state persists

- [ ] **UI-004**: Loading states
  - Verify spinners during loading
  - Verify skeleton screens
  - Verify proper transitions

#### 4.1.8 Performance Tests (`test_performance.spec.ts`)
- [ ] **PF-001**: Large conversation history
  - Load session with 100+ messages
  - Measure render time (<2s)
  - Verify smooth scrolling

- [ ] **PF-002**: Multiple concurrent chats
  - Open 5 chat sessions
  - Send messages concurrently
  - Verify all respond correctly

- [ ] **PF-003**: File upload limits
  - Upload 10MB file
  - Verify progress indicator
  - Verify upload completes

---

## 5. Test Execution

### 5.1 Backend Tests
```bash
# Run all backend tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=app --cov-report=html

# Run specific test file
poetry run pytest tests/unit/test_models.py

# Run integration tests only
poetry run pytest tests/integration/
```

### 5.2 Frontend Tests
```bash
# Run all frontend tests
npm test

# Run with coverage
npm run test:coverage

# Run specific test
npm test ProjectList.test.tsx
```

### 5.3 E2E Tests
```bash
# Install Playwright
npm install -D @playwright/test

# Run E2E tests
npx playwright test

# Run in headed mode (see browser)
npx playwright test --headed

# Run specific test
npx playwright test tests/e2e/test_chat_session.spec.ts

# Debug mode
npx playwright test --debug

# Generate test report
npx playwright show-report
```

---

## 6. Test Data Management

### 6.1 Test Fixtures
- Sample projects with different configurations
- Chat sessions with various message histories
- Agent configurations for each environment type
- Sample files for upload/download testing

### 6.2 Database Seeding
- Reset database before each test suite
- Seed with consistent test data
- Clean up after tests complete

### 6.3 Mock Data
- Mock LLM responses for predictable testing
- Mock file system for isolation
- Mock Docker containers for speed

---

## 7. CI/CD Integration (Future)

### 7.1 GitHub Actions Workflow
```yaml
name: Tests

on: [push, pull_request]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - Checkout code
      - Setup Python 3.13
      - Install dependencies
      - Run pytest
      - Upload coverage

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - Checkout code
      - Setup Node.js
      - Install dependencies
      - Run tests

  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - Checkout code
      - Setup Docker
      - Start services
      - Run Playwright tests
      - Upload test artifacts
```

---

## 8. Test Metrics

### 8.1 Coverage Goals
- Backend: >80% code coverage
- Frontend: >70% code coverage
- E2E: All critical user paths covered

### 8.2 Performance Benchmarks
- API response time: <200ms (95th percentile)
- WebSocket latency: <100ms
- Page load time: <2s
- Agent execution: <30s per task

### 8.3 Test Execution Time
- Unit tests: <30s
- Integration tests: <2min
- E2E tests: <10min
- Full suite: <15min

---

## 9. Bug Tracking

### 9.1 Issues Found
- [FIXED] Container name conflict on repeated chat sessions
- [FIXED] Messages state not managed properly in ChatSessionPage
- [FIXED] Dark theme remnants in UI components

### 9.2 Known Limitations
- Container cleanup requires Docker daemon running
- WebSocket reconnection not implemented
- File upload size limited to 10MB

---

## 10. Test Maintenance

### 10.1 Regular Updates
- Update tests when features change
- Review and refactor flaky tests
- Update test data regularly
- Keep dependencies updated

### 10.2 Test Review Process
- All new features require tests
- PRs must maintain or improve coverage
- E2E tests for user-facing changes
- Performance tests for critical paths
