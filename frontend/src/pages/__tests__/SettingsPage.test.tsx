import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import SettingsPage from '../SettingsPage';
import { settingsAPI } from '@/services/api';

// Mock the API
vi.mock('@/services/api', () => ({
  settingsAPI: {
    listApiKeys: vi.fn(),
    setApiKey: vi.fn(),
    deleteApiKey: vi.fn(),
    testApiKey: vi.fn(),
  },
}));

// Mock useNavigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock window.confirm
vi.stubGlobal('confirm', vi.fn());

describe('SettingsPage', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
  });

  const renderPage = () => {
    return render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <SettingsPage />
        </BrowserRouter>
      </QueryClientProvider>
    );
  };

  it('should render page title and description', async () => {
    vi.mocked(settingsAPI.listApiKeys).mockResolvedValueOnce({ api_keys: [] });

    renderPage();

    expect(screen.getByText('Settings')).toBeInTheDocument();
    expect(screen.getByText(/Manage your API keys/)).toBeInTheDocument();
  });

  it('should render back button', async () => {
    vi.mocked(settingsAPI.listApiKeys).mockResolvedValueOnce({ api_keys: [] });

    renderPage();

    expect(screen.getByText('← Back to Projects')).toBeInTheDocument();
  });

  it('should navigate back when back button is clicked', async () => {
    vi.mocked(settingsAPI.listApiKeys).mockResolvedValueOnce({ api_keys: [] });

    renderPage();

    const backButton = screen.getByText('← Back to Projects');
    await userEvent.click(backButton);

    expect(mockNavigate).toHaveBeenCalledWith('/');
  });

  it('should show security notice', async () => {
    vi.mocked(settingsAPI.listApiKeys).mockResolvedValueOnce({ api_keys: [] });

    renderPage();

    expect(screen.getByText(/Security Notice/)).toBeInTheDocument();
    expect(screen.getByText(/API keys are encrypted/)).toBeInTheDocument();
  });

  it('should render all three provider cards', async () => {
    vi.mocked(settingsAPI.listApiKeys).mockResolvedValueOnce({ api_keys: [] });

    renderPage();

    await waitFor(() => {
      expect(screen.getByText('OpenAI')).toBeInTheDocument();
      expect(screen.getByText('Anthropic (Claude)')).toBeInTheDocument();
      expect(screen.getByText('Azure OpenAI')).toBeInTheDocument();
    });
  });

  it('should show configured status for configured providers', async () => {
    vi.mocked(settingsAPI.listApiKeys).mockResolvedValueOnce({
      api_keys: [
        {
          provider: 'openai',
          is_configured: true,
          last_used_at: null,
          created_at: '2024-01-01T00:00:00Z',
        },
      ],
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByText(/✓ Configured/)).toBeInTheDocument();
    });
  });

  it('should show not configured status for unconfigured providers', async () => {
    vi.mocked(settingsAPI.listApiKeys).mockResolvedValueOnce({ api_keys: [] });

    renderPage();

    await waitFor(() => {
      expect(screen.getAllByText('Not configured')).toHaveLength(3);
    });
  });

  it('should show Add Key button for unconfigured providers', async () => {
    vi.mocked(settingsAPI.listApiKeys).mockResolvedValueOnce({ api_keys: [] });

    renderPage();

    await waitFor(() => {
      expect(screen.getAllByText('Add Key')).toHaveLength(3);
    });
  });

  it('should show Update and Delete buttons for configured providers', async () => {
    vi.mocked(settingsAPI.listApiKeys).mockResolvedValueOnce({
      api_keys: [
        {
          provider: 'openai',
          is_configured: true,
          last_used_at: null,
          created_at: '2024-01-01T00:00:00Z',
        },
      ],
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Update')).toBeInTheDocument();
      expect(screen.getByText('Delete')).toBeInTheDocument();
    });
  });

  it('should open edit form when Add Key is clicked', async () => {
    vi.mocked(settingsAPI.listApiKeys).mockResolvedValueOnce({ api_keys: [] });

    renderPage();

    await waitFor(() => {
      expect(screen.getAllByText('Add Key')).toHaveLength(3);
    });

    const addKeyButtons = screen.getAllByText('Add Key');
    await userEvent.click(addKeyButtons[0]);

    expect(screen.getByPlaceholderText('sk-...')).toBeInTheDocument();
    expect(screen.getByText('Test Connection')).toBeInTheDocument();
    expect(screen.getByText('Save Key')).toBeInTheDocument();
    expect(screen.getByText('Cancel')).toBeInTheDocument();
  });

  it('should close edit form when Cancel is clicked', async () => {
    vi.mocked(settingsAPI.listApiKeys).mockResolvedValueOnce({ api_keys: [] });

    renderPage();

    await waitFor(() => {
      expect(screen.getAllByText('Add Key')).toHaveLength(3);
    });

    const addKeyButtons = screen.getAllByText('Add Key');
    await userEvent.click(addKeyButtons[0]);

    const cancelButton = screen.getByText('Cancel');
    await userEvent.click(cancelButton);

    expect(screen.queryByLabelText('API Key')).not.toBeInTheDocument();
  });

  it('should call test API when Test Connection is clicked', async () => {
    vi.mocked(settingsAPI.listApiKeys).mockResolvedValueOnce({ api_keys: [] });
    vi.mocked(settingsAPI.testApiKey).mockResolvedValueOnce({
      valid: true,
      message: 'API key is valid',
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getAllByText('Add Key')).toHaveLength(3);
    });

    const addKeyButtons = screen.getAllByText('Add Key');
    await userEvent.click(addKeyButtons[0]);

    const keyInput = screen.getByPlaceholderText('sk-...');
    await userEvent.type(keyInput, 'sk-test-key');

    const testButton = screen.getByText('Test Connection');
    await userEvent.click(testButton);

    await waitFor(() => {
      expect(settingsAPI.testApiKey).toHaveBeenCalledWith('openai', 'sk-test-key');
    });
  });

  it('should show test result after testing', async () => {
    vi.mocked(settingsAPI.listApiKeys).mockResolvedValueOnce({ api_keys: [] });
    vi.mocked(settingsAPI.testApiKey).mockResolvedValueOnce({
      valid: true,
      message: 'API key is valid',
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getAllByText('Add Key')).toHaveLength(3);
    });

    const addKeyButtons = screen.getAllByText('Add Key');
    await userEvent.click(addKeyButtons[0]);

    const keyInput = screen.getByPlaceholderText('sk-...');
    await userEvent.type(keyInput, 'sk-test-key');

    const testButton = screen.getByText('Test Connection');
    await userEvent.click(testButton);

    await waitFor(() => {
      expect(screen.getByText('API key is valid')).toBeInTheDocument();
    });
  });

  it('should call save API when Save Key is clicked', async () => {
    vi.mocked(settingsAPI.listApiKeys).mockResolvedValueOnce({ api_keys: [] });
    vi.mocked(settingsAPI.setApiKey).mockResolvedValueOnce({ message: 'Saved' });

    renderPage();

    await waitFor(() => {
      expect(screen.getAllByText('Add Key')).toHaveLength(3);
    });

    const addKeyButtons = screen.getAllByText('Add Key');
    await userEvent.click(addKeyButtons[0]);

    const keyInput = screen.getByPlaceholderText('sk-...');
    await userEvent.type(keyInput, 'sk-test-key');

    const saveButton = screen.getByText('Save Key');
    await userEvent.click(saveButton);

    await waitFor(() => {
      expect(settingsAPI.setApiKey).toHaveBeenCalledWith({
        provider: 'openai',
        api_key: 'sk-test-key',
      });
    });
  });

  it('should show success message after saving', async () => {
    vi.mocked(settingsAPI.listApiKeys).mockResolvedValue({ api_keys: [] });
    vi.mocked(settingsAPI.setApiKey).mockResolvedValueOnce({ message: 'Saved' });

    renderPage();

    await waitFor(() => {
      expect(screen.getAllByText('Add Key')).toHaveLength(3);
    });

    const addKeyButtons = screen.getAllByText('Add Key');
    await userEvent.click(addKeyButtons[0]);

    const keyInput = screen.getByPlaceholderText('sk-...');
    await userEvent.type(keyInput, 'sk-test-key');

    const saveButton = screen.getByText('Save Key');
    await userEvent.click(saveButton);

    await waitFor(() => {
      expect(screen.getByText(/saved successfully/)).toBeInTheDocument();
    });
  });

  it('should confirm before deleting', async () => {
    vi.mocked(settingsAPI.listApiKeys).mockResolvedValueOnce({
      api_keys: [
        {
          provider: 'openai',
          is_configured: true,
          last_used_at: null,
          created_at: '2024-01-01T00:00:00Z',
        },
      ],
    });
    vi.mocked(window.confirm).mockReturnValue(false);

    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Delete')).toBeInTheDocument();
    });

    const deleteButton = screen.getByText('Delete');
    await userEvent.click(deleteButton);

    expect(window.confirm).toHaveBeenCalled();
    expect(settingsAPI.deleteApiKey).not.toHaveBeenCalled();
  });

  it('should delete when confirmed', async () => {
    vi.mocked(settingsAPI.listApiKeys).mockResolvedValue({
      api_keys: [
        {
          provider: 'openai',
          is_configured: true,
          last_used_at: null,
          created_at: '2024-01-01T00:00:00Z',
        },
      ],
    });
    vi.mocked(window.confirm).mockReturnValue(true);
    vi.mocked(settingsAPI.deleteApiKey).mockResolvedValueOnce(undefined);

    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Delete')).toBeInTheDocument();
    });

    const deleteButton = screen.getByText('Delete');
    await userEvent.click(deleteButton);

    await waitFor(() => {
      expect(settingsAPI.deleteApiKey).toHaveBeenCalledWith('openai');
    });
  });

  it('should disable Test Connection button when no key entered', async () => {
    vi.mocked(settingsAPI.listApiKeys).mockResolvedValueOnce({ api_keys: [] });

    renderPage();

    await waitFor(() => {
      expect(screen.getAllByText('Add Key')).toHaveLength(3);
    });

    const addKeyButtons = screen.getAllByText('Add Key');
    await userEvent.click(addKeyButtons[0]);

    const testButton = screen.getByText('Test Connection');
    expect(testButton).toBeDisabled();
  });

  it('should disable Save Key button when no key entered', async () => {
    vi.mocked(settingsAPI.listApiKeys).mockResolvedValueOnce({ api_keys: [] });

    renderPage();

    await waitFor(() => {
      expect(screen.getAllByText('Add Key')).toHaveLength(3);
    });

    const addKeyButtons = screen.getAllByText('Add Key');
    await userEvent.click(addKeyButtons[0]);

    const saveButton = screen.getByText('Save Key');
    expect(saveButton).toBeDisabled();
  });
});
