import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import axios from 'axios';
import {
  projectsAPI,
  chatSessionsAPI,
  contentBlocksAPI,
  filesAPI,
  workspaceAPI,
  sandboxAPI,
  settingsAPI,
} from '../api';

// Mock axios
vi.mock('axios', () => {
  const mockAxiosInstance = {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  };
  return {
    default: {
      create: vi.fn(() => mockAxiosInstance),
    },
  };
});

describe('API Services', () => {
  let mockApi: {
    get: ReturnType<typeof vi.fn>;
    post: ReturnType<typeof vi.fn>;
    put: ReturnType<typeof vi.fn>;
    delete: ReturnType<typeof vi.fn>;
  };

  beforeEach(() => {
    mockApi = (axios.create as ReturnType<typeof vi.fn>)();
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('projectsAPI', () => {
    it('should list projects', async () => {
      const mockResponse = { projects: [{ id: '1', name: 'Test' }], total: 1 };
      mockApi.get.mockResolvedValueOnce({ data: mockResponse });

      const result = await projectsAPI.list();

      expect(mockApi.get).toHaveBeenCalledWith('/projects');
      expect(result).toEqual(mockResponse);
    });

    it('should create a project', async () => {
      const newProject = { name: 'New Project', description: 'Test description' };
      const mockResponse = { id: '1', ...newProject, created_at: '2024-01-01', updated_at: '2024-01-01' };
      mockApi.post.mockResolvedValueOnce({ data: mockResponse });

      const result = await projectsAPI.create(newProject);

      expect(mockApi.post).toHaveBeenCalledWith('/projects', newProject);
      expect(result).toEqual(mockResponse);
    });

    it('should get a project by id', async () => {
      const mockResponse = { id: '1', name: 'Test', created_at: '2024-01-01', updated_at: '2024-01-01' };
      mockApi.get.mockResolvedValueOnce({ data: mockResponse });

      const result = await projectsAPI.get('1');

      expect(mockApi.get).toHaveBeenCalledWith('/projects/1');
      expect(result).toEqual(mockResponse);
    });

    it('should update a project', async () => {
      const updateData = { name: 'Updated Name' };
      const mockResponse = { id: '1', name: 'Updated Name', created_at: '2024-01-01', updated_at: '2024-01-02' };
      mockApi.put.mockResolvedValueOnce({ data: mockResponse });

      const result = await projectsAPI.update('1', updateData);

      expect(mockApi.put).toHaveBeenCalledWith('/projects/1', updateData);
      expect(result).toEqual(mockResponse);
    });

    it('should delete a project', async () => {
      mockApi.delete.mockResolvedValueOnce({});

      await projectsAPI.delete('1');

      expect(mockApi.delete).toHaveBeenCalledWith('/projects/1');
    });

    it('should get agent config', async () => {
      const mockResponse = { agent_type: 'code_agent', llm_provider: 'openai' };
      mockApi.get.mockResolvedValueOnce({ data: mockResponse });

      const result = await projectsAPI.getAgentConfig('project-1');

      expect(mockApi.get).toHaveBeenCalledWith('/projects/project-1/agent-config');
      expect(result).toEqual(mockResponse);
    });

    it('should update agent config', async () => {
      const updateConfig = { llm_model: 'gpt-4o' };
      const mockResponse = { agent_type: 'code_agent', llm_provider: 'openai', llm_model: 'gpt-4o' };
      mockApi.put.mockResolvedValueOnce({ data: mockResponse });

      const result = await projectsAPI.updateAgentConfig('project-1', updateConfig);

      expect(mockApi.put).toHaveBeenCalledWith('/projects/project-1/agent-config', updateConfig);
      expect(result).toEqual(mockResponse);
    });

    it('should list agent templates', async () => {
      const mockResponse = [{ id: 'default', name: 'Default Template' }];
      mockApi.get.mockResolvedValueOnce({ data: mockResponse });

      const result = await projectsAPI.listAgentTemplates();

      expect(mockApi.get).toHaveBeenCalledWith('/projects/templates/list');
      expect(result).toEqual(mockResponse);
    });

    it('should get agent template', async () => {
      const mockResponse = { id: 'default', name: 'Default Template', agent_type: 'code_agent' };
      mockApi.get.mockResolvedValueOnce({ data: mockResponse });

      const result = await projectsAPI.getAgentTemplate('default');

      expect(mockApi.get).toHaveBeenCalledWith('/projects/templates/default');
      expect(result).toEqual(mockResponse);
    });

    it('should apply agent template', async () => {
      const mockResponse = { agent_type: 'code_agent', llm_provider: 'openai' };
      mockApi.post.mockResolvedValueOnce({ data: mockResponse });

      const result = await projectsAPI.applyAgentTemplate('project-1', 'default');

      expect(mockApi.post).toHaveBeenCalledWith('/projects/project-1/agent-config/apply-template/default');
      expect(result).toEqual(mockResponse);
    });
  });

  describe('chatSessionsAPI', () => {
    it('should list chat sessions without project filter', async () => {
      const mockResponse = { chat_sessions: [], total: 0 };
      mockApi.get.mockResolvedValueOnce({ data: mockResponse });

      const result = await chatSessionsAPI.list();

      expect(mockApi.get).toHaveBeenCalledWith('/chats', { params: {} });
      expect(result).toEqual(mockResponse);
    });

    it('should list chat sessions with project filter', async () => {
      const mockResponse = { chat_sessions: [{ id: '1', name: 'Session 1' }], total: 1 };
      mockApi.get.mockResolvedValueOnce({ data: mockResponse });

      const result = await chatSessionsAPI.list('project-1');

      expect(mockApi.get).toHaveBeenCalledWith('/chats', { params: { project_id: 'project-1' } });
      expect(result).toEqual(mockResponse);
    });

    it('should create a chat session', async () => {
      const sessionData = { name: 'New Session' };
      const mockResponse = { id: '1', name: 'New Session', project_id: 'project-1' };
      mockApi.post.mockResolvedValueOnce({ data: mockResponse });

      const result = await chatSessionsAPI.create('project-1', sessionData);

      expect(mockApi.post).toHaveBeenCalledWith('/chats?project_id=project-1', sessionData);
      expect(result).toEqual(mockResponse);
    });

    it('should get a chat session', async () => {
      const mockResponse = { id: '1', name: 'Session 1', project_id: 'project-1' };
      mockApi.get.mockResolvedValueOnce({ data: mockResponse });

      const result = await chatSessionsAPI.get('1');

      expect(mockApi.get).toHaveBeenCalledWith('/chats/1');
      expect(result).toEqual(mockResponse);
    });

    it('should update a chat session', async () => {
      const updateData = { name: 'Updated Session' };
      const mockResponse = { id: '1', name: 'Updated Session', project_id: 'project-1' };
      mockApi.put.mockResolvedValueOnce({ data: mockResponse });

      const result = await chatSessionsAPI.update('1', updateData);

      expect(mockApi.put).toHaveBeenCalledWith('/chats/1', updateData);
      expect(result).toEqual(mockResponse);
    });

    it('should delete a chat session', async () => {
      mockApi.delete.mockResolvedValueOnce({});

      await chatSessionsAPI.delete('1');

      expect(mockApi.delete).toHaveBeenCalledWith('/chats/1');
    });
  });

  describe('contentBlocksAPI', () => {
    it('should list content blocks', async () => {
      const mockResponse = { content_blocks: [], total: 0 };
      mockApi.get.mockResolvedValueOnce({ data: mockResponse });

      const result = await contentBlocksAPI.list('session-1');

      expect(mockApi.get).toHaveBeenCalledWith('/chats/session-1/blocks');
      expect(result).toEqual(mockResponse);
    });

    it('should get a content block', async () => {
      const mockResponse = { id: 'block-1', type: 'user', content: 'Hello' };
      mockApi.get.mockResolvedValueOnce({ data: mockResponse });

      const result = await contentBlocksAPI.get('session-1', 'block-1');

      expect(mockApi.get).toHaveBeenCalledWith('/chats/session-1/blocks/block-1');
      expect(result).toEqual(mockResponse);
    });
  });

  describe('filesAPI', () => {
    it('should upload a file', async () => {
      const mockFile = new File(['content'], 'test.txt', { type: 'text/plain' });
      const mockResponse = { id: '1', filename: 'test.txt' };
      mockApi.post.mockResolvedValueOnce({ data: mockResponse });

      const result = await filesAPI.upload('project-1', mockFile);

      expect(mockApi.post).toHaveBeenCalled();
      const [url, formData, config] = mockApi.post.mock.calls[0];
      expect(url).toBe('/files/upload/project-1');
      expect(formData).toBeInstanceOf(FormData);
      expect(config.headers['Content-Type']).toBe('multipart/form-data');
      expect(result).toEqual(mockResponse);
    });

    it('should list files for a project', async () => {
      const mockResponse = { files: [{ id: '1', filename: 'test.txt' }] };
      mockApi.get.mockResolvedValueOnce({ data: mockResponse });

      const result = await filesAPI.list('project-1');

      expect(mockApi.get).toHaveBeenCalledWith('/files/project/project-1');
      expect(result).toEqual(mockResponse);
    });

    it('should download a file', async () => {
      const mockBlob = new Blob(['content']);
      mockApi.get.mockResolvedValueOnce({ data: mockBlob });

      const result = await filesAPI.download('file-1');

      expect(mockApi.get).toHaveBeenCalledWith('/files/file-1/download', { responseType: 'blob' });
      expect(result).toEqual(mockBlob);
    });

    it('should delete a file', async () => {
      mockApi.delete.mockResolvedValueOnce({});

      await filesAPI.delete('file-1');

      expect(mockApi.delete).toHaveBeenCalledWith('/files/file-1');
    });
  });

  describe('workspaceAPI', () => {
    it('should list workspace files', async () => {
      const mockResponse = { uploaded: [], output: [] };
      mockApi.get.mockResolvedValueOnce({ data: mockResponse });

      const result = await workspaceAPI.listFiles('session-1');

      expect(mockApi.get).toHaveBeenCalledWith('/chats/session-1/workspace/files');
      expect(result).toEqual(mockResponse);
    });

    it('should get file content', async () => {
      const mockResponse = { path: '/test.txt', content: 'Hello', is_binary: false, mime_type: 'text/plain' };
      mockApi.get.mockResolvedValueOnce({ data: mockResponse });

      const result = await workspaceAPI.getFileContent('session-1', '/test.txt');

      expect(mockApi.get).toHaveBeenCalledWith('/chats/session-1/workspace/files/content', {
        params: { path: '/test.txt' },
      });
      expect(result).toEqual(mockResponse);
    });

    it('should download workspace file', async () => {
      const mockBlob = new Blob(['content']);
      mockApi.get.mockResolvedValueOnce({ data: mockBlob });

      const result = await workspaceAPI.downloadFile('session-1', '/test.txt');

      expect(mockApi.get).toHaveBeenCalledWith('/chats/session-1/workspace/files/download', {
        params: { path: '/test.txt' },
        responseType: 'blob',
      });
      expect(result).toEqual(mockBlob);
    });

    it('should download all files', async () => {
      const mockBlob = new Blob(['zip content']);
      mockApi.get.mockResolvedValueOnce({ data: mockBlob });

      const result = await workspaceAPI.downloadAll('session-1', 'output');

      expect(mockApi.get).toHaveBeenCalledWith('/chats/session-1/workspace/download-all', {
        params: { type: 'output' },
        responseType: 'blob',
      });
      expect(result).toEqual(mockBlob);
    });

    it('should upload file to project', async () => {
      const mockResponse = { id: '1', filename: 'test.txt' };
      mockApi.post.mockResolvedValueOnce({ data: mockResponse });

      const result = await workspaceAPI.uploadToProject('session-1', '/output/test.txt', 'project-1');

      expect(mockApi.post).toHaveBeenCalledWith('/chats/session-1/workspace/files/upload-to-project', {
        path: '/output/test.txt',
        project_id: 'project-1',
      });
      expect(result).toEqual(mockResponse);
    });
  });

  describe('sandboxAPI', () => {
    it('should start sandbox', async () => {
      const mockResponse = { status: 'started', container_id: 'abc123' };
      mockApi.post.mockResolvedValueOnce({ data: mockResponse });

      const result = await sandboxAPI.start('session-1');

      expect(mockApi.post).toHaveBeenCalledWith('/sandbox/session-1/start');
      expect(result).toEqual(mockResponse);
    });

    it('should stop sandbox', async () => {
      const mockResponse = { status: 'stopped' };
      mockApi.post.mockResolvedValueOnce({ data: mockResponse });

      const result = await sandboxAPI.stop('session-1');

      expect(mockApi.post).toHaveBeenCalledWith('/sandbox/session-1/stop');
      expect(result).toEqual(mockResponse);
    });

    it('should reset sandbox', async () => {
      const mockResponse = { status: 'reset', container_id: 'xyz789' };
      mockApi.post.mockResolvedValueOnce({ data: mockResponse });

      const result = await sandboxAPI.reset('session-1');

      expect(mockApi.post).toHaveBeenCalledWith('/sandbox/session-1/reset');
      expect(result).toEqual(mockResponse);
    });

    it('should get sandbox status', async () => {
      const mockResponse = { status: 'running', container_id: 'abc123' };
      mockApi.get.mockResolvedValueOnce({ data: mockResponse });

      const result = await sandboxAPI.status('session-1');

      expect(mockApi.get).toHaveBeenCalledWith('/sandbox/session-1/status');
      expect(result).toEqual(mockResponse);
    });

    it('should execute command with default workdir', async () => {
      const mockResponse = { exit_code: 0, stdout: 'output', stderr: '' };
      mockApi.post.mockResolvedValueOnce({ data: mockResponse });

      const result = await sandboxAPI.execute('session-1', 'ls -la');

      expect(mockApi.post).toHaveBeenCalledWith('/sandbox/session-1/execute', {
        command: 'ls -la',
        workdir: '/workspace',
      });
      expect(result).toEqual(mockResponse);
    });

    it('should execute command with custom workdir', async () => {
      const mockResponse = { exit_code: 0, stdout: 'output', stderr: '' };
      mockApi.post.mockResolvedValueOnce({ data: mockResponse });

      const result = await sandboxAPI.execute('session-1', 'cat file.txt', '/home/user');

      expect(mockApi.post).toHaveBeenCalledWith('/sandbox/session-1/execute', {
        command: 'cat file.txt',
        workdir: '/home/user',
      });
      expect(result).toEqual(mockResponse);
    });
  });

  describe('settingsAPI', () => {
    it('should list API keys', async () => {
      const mockResponse = { api_keys: [{ provider: 'openai', is_configured: true }] };
      mockApi.get.mockResolvedValueOnce({ data: mockResponse });

      const result = await settingsAPI.listApiKeys();

      expect(mockApi.get).toHaveBeenCalledWith('/settings/api-keys');
      expect(result).toEqual(mockResponse);
    });

    it('should set API key', async () => {
      const keyData = { provider: 'openai', api_key: 'sk-test' };
      const mockResponse = { message: 'API key saved' };
      mockApi.post.mockResolvedValueOnce({ data: mockResponse });

      const result = await settingsAPI.setApiKey(keyData);

      expect(mockApi.post).toHaveBeenCalledWith('/settings/api-keys', keyData);
      expect(result).toEqual(mockResponse);
    });

    it('should delete API key', async () => {
      mockApi.delete.mockResolvedValueOnce({});

      await settingsAPI.deleteApiKey('openai');

      expect(mockApi.delete).toHaveBeenCalledWith('/settings/api-keys/openai');
    });

    it('should test API key', async () => {
      const mockResponse = { valid: true, message: 'API key is valid' };
      mockApi.post.mockResolvedValueOnce({ data: mockResponse });

      const result = await settingsAPI.testApiKey('openai', 'sk-test');

      expect(mockApi.post).toHaveBeenCalledWith('/settings/api-keys/test', {
        provider: 'openai',
        api_key: 'sk-test',
      });
      expect(result).toEqual(mockResponse);
    });
  });
});
