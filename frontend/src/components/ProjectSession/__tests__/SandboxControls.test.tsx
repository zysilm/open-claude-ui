import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import SandboxControls from '../SandboxControls';
import { sandboxAPI } from '@/services/api';

// Mock the API
vi.mock('@/services/api', () => ({
  sandboxAPI: {
    status: vi.fn(),
    start: vi.fn(),
    stop: vi.fn(),
    reset: vi.fn(),
    execute: vi.fn(),
  },
}));

describe('SandboxControls', () => {
  let queryClient: QueryClient;
  const sessionId = 'session-123';

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
  });

  const renderControls = () => {
    return render(
      <QueryClientProvider client={queryClient}>
        <SandboxControls sessionId={sessionId} />
      </QueryClientProvider>
    );
  };

  describe('when sandbox is stopped', () => {
    beforeEach(() => {
      vi.mocked(sandboxAPI.status).mockResolvedValue({ running: false });
    });

    it('should show stopped status', async () => {
      renderControls();

      await waitFor(() => {
        expect(screen.getByText('Sandbox Stopped')).toBeInTheDocument();
      });
    });

    it('should show Start Sandbox button', async () => {
      renderControls();

      await waitFor(() => {
        expect(screen.getByText('Start Sandbox')).toBeInTheDocument();
      });
    });

    it('should not show Reset, Execute, or Stop buttons', async () => {
      renderControls();

      await waitFor(() => {
        expect(screen.queryByText('Reset')).not.toBeInTheDocument();
        expect(screen.queryByText('Execute')).not.toBeInTheDocument();
        expect(screen.queryByText('Stop')).not.toBeInTheDocument();
      });
    });

    it('should call start API when Start button is clicked', async () => {
      vi.mocked(sandboxAPI.start).mockResolvedValueOnce({ status: 'started' });

      renderControls();

      await waitFor(() => {
        expect(screen.getByText('Start Sandbox')).toBeInTheDocument();
      });

      const startButton = screen.getByText('Start Sandbox');
      await userEvent.click(startButton);

      expect(sandboxAPI.start).toHaveBeenCalledWith(sessionId);
    });

    it('should show Starting... while mutation is pending', async () => {
      vi.mocked(sandboxAPI.start).mockImplementation(() => new Promise(() => {}));

      renderControls();

      await waitFor(() => {
        expect(screen.getByText('Start Sandbox')).toBeInTheDocument();
      });

      const startButton = screen.getByText('Start Sandbox');
      await userEvent.click(startButton);

      await waitFor(() => {
        expect(screen.getByText('Starting...')).toBeInTheDocument();
      });
    });
  });

  describe('when sandbox is running', () => {
    beforeEach(() => {
      vi.mocked(sandboxAPI.status).mockResolvedValue({ running: true });
    });

    it('should show running status', async () => {
      renderControls();

      await waitFor(() => {
        expect(screen.getByText('Sandbox Running')).toBeInTheDocument();
      });
    });

    it('should show Reset, Execute, and Stop buttons', async () => {
      renderControls();

      await waitFor(() => {
        expect(screen.getByText('Reset')).toBeInTheDocument();
        expect(screen.getByText('Execute')).toBeInTheDocument();
        expect(screen.getByText('Stop')).toBeInTheDocument();
      });
    });

    it('should not show Start Sandbox button', async () => {
      renderControls();

      await waitFor(() => {
        expect(screen.queryByText('Start Sandbox')).not.toBeInTheDocument();
      });
    });

    it('should call stop API when Stop button is clicked', async () => {
      vi.mocked(sandboxAPI.stop).mockResolvedValueOnce({ status: 'stopped' });

      renderControls();

      await waitFor(() => {
        expect(screen.getByText('Stop')).toBeInTheDocument();
      });

      const stopButton = screen.getByText('Stop');
      await userEvent.click(stopButton);

      expect(sandboxAPI.stop).toHaveBeenCalledWith(sessionId);
    });

    it('should call reset API when Reset button is clicked', async () => {
      vi.mocked(sandboxAPI.reset).mockResolvedValueOnce({ status: 'reset' });

      renderControls();

      await waitFor(() => {
        expect(screen.getByText('Reset')).toBeInTheDocument();
      });

      const resetButton = screen.getByText('Reset');
      await userEvent.click(resetButton);

      expect(sandboxAPI.reset).toHaveBeenCalledWith(sessionId);
    });

    it('should toggle command input when Execute button is clicked', async () => {
      renderControls();

      await waitFor(() => {
        expect(screen.getByText('Execute')).toBeInTheDocument();
      });

      // Initially no command input
      expect(screen.queryByPlaceholderText(/Enter command/)).not.toBeInTheDocument();

      // Click Execute to show input
      const executeButton = screen.getByText('Execute');
      await userEvent.click(executeButton);

      expect(screen.getByPlaceholderText(/Enter command/)).toBeInTheDocument();

      // Click again to hide
      await userEvent.click(executeButton);

      expect(screen.queryByPlaceholderText(/Enter command/)).not.toBeInTheDocument();
    });

    it('should execute command when Run button is clicked', async () => {
      vi.mocked(sandboxAPI.execute).mockResolvedValueOnce({
        exit_code: 0,
        stdout: 'output',
        stderr: '',
      });

      renderControls();

      await waitFor(() => {
        expect(screen.getByText('Execute')).toBeInTheDocument();
      });

      // Show command input
      const executeButton = screen.getByText('Execute');
      await userEvent.click(executeButton);

      // Type command
      const commandInput = screen.getByPlaceholderText(/Enter command/);
      await userEvent.type(commandInput, 'ls -la');

      // Click Run
      const runButton = screen.getByText('Run');
      await userEvent.click(runButton);

      expect(sandboxAPI.execute).toHaveBeenCalledWith(sessionId, 'ls -la');
    });

    it('should execute command on Enter key', async () => {
      vi.mocked(sandboxAPI.execute).mockResolvedValueOnce({
        exit_code: 0,
        stdout: 'output',
        stderr: '',
      });

      renderControls();

      await waitFor(() => {
        expect(screen.getByText('Execute')).toBeInTheDocument();
      });

      // Show command input
      const executeButton = screen.getByText('Execute');
      await userEvent.click(executeButton);

      // Type command and press Enter
      const commandInput = screen.getByPlaceholderText(/Enter command/);
      await userEvent.type(commandInput, 'pwd{enter}');

      expect(sandboxAPI.execute).toHaveBeenCalledWith(sessionId, 'pwd');
    });

    it('should disable Run button when command is empty', async () => {
      renderControls();

      await waitFor(() => {
        expect(screen.getByText('Execute')).toBeInTheDocument();
      });

      const executeButton = screen.getByText('Execute');
      await userEvent.click(executeButton);

      const runButton = screen.getByText('Run');
      expect(runButton).toBeDisabled();
    });

    it('should show execution result', async () => {
      vi.mocked(sandboxAPI.execute).mockResolvedValueOnce({
        exit_code: 0,
        stdout: 'Hello World',
        stderr: '',
      });

      renderControls();

      await waitFor(() => {
        expect(screen.getByText('Execute')).toBeInTheDocument();
      });

      const executeButton = screen.getByText('Execute');
      await userEvent.click(executeButton);

      const commandInput = screen.getByPlaceholderText(/Enter command/);
      await userEvent.type(commandInput, 'echo "Hello World"');

      const runButton = screen.getByText('Run');
      await userEvent.click(runButton);

      await waitFor(() => {
        expect(screen.getByText(/Command Result/)).toBeInTheDocument();
        expect(screen.getByText('Hello World')).toBeInTheDocument();
      });
    });

    it('should show stderr in result', async () => {
      vi.mocked(sandboxAPI.execute).mockResolvedValueOnce({
        exit_code: 1,
        stdout: '',
        stderr: 'Error occurred',
      });

      renderControls();

      await waitFor(() => {
        expect(screen.getByText('Execute')).toBeInTheDocument();
      });

      const executeButton = screen.getByText('Execute');
      await userEvent.click(executeButton);

      const commandInput = screen.getByPlaceholderText(/Enter command/);
      await userEvent.type(commandInput, 'invalid-cmd');

      const runButton = screen.getByText('Run');
      await userEvent.click(runButton);

      await waitFor(() => {
        expect(screen.getByText('Error occurred')).toBeInTheDocument();
      });
    });
  });

  it('should have correct CSS classes', async () => {
    vi.mocked(sandboxAPI.status).mockResolvedValue({ running: true });

    const { container } = renderControls();

    await waitFor(() => {
      expect(container.querySelector('.sandbox-controls')).toBeInTheDocument();
      expect(container.querySelector('.sandbox-status')).toBeInTheDocument();
      expect(container.querySelector('.status-indicator')).toBeInTheDocument();
      expect(container.querySelector('.sandbox-actions')).toBeInTheDocument();
    });
  });

  it('should have running status indicator class when running', async () => {
    vi.mocked(sandboxAPI.status).mockResolvedValue({ running: true });

    const { container } = renderControls();

    await waitFor(() => {
      expect(container.querySelector('.status-indicator.running')).toBeInTheDocument();
    });
  });

  it('should have stopped status indicator class when stopped', async () => {
    vi.mocked(sandboxAPI.status).mockResolvedValue({ running: false });

    const { container } = renderControls();

    await waitFor(() => {
      expect(container.querySelector('.status-indicator.stopped')).toBeInTheDocument();
    });
  });
});
