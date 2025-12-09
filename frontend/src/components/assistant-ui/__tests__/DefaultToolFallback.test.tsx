import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { DefaultToolFallback } from '../DefaultToolFallback';

// Mock lucide-react icons
vi.mock('lucide-react', () => ({
  ChevronRight: () => <div data-testid="chevron-right" />,
  ChevronDown: () => <div data-testid="chevron-down" />,
}));

// Mock syntax highlighter
vi.mock('react-syntax-highlighter', () => ({
  Prism: ({ children }: { children: string }) => <pre data-testid="syntax-highlighter">{children}</pre>,
}));

vi.mock('react-syntax-highlighter/dist/esm/styles/prism', () => ({
  oneLight: {},
}));

// Mock MessageHelpers
vi.mock('@/components/ProjectSession/components/MessageHelpers.tsx', () => ({
  ObservationContent: ({ content }: { content: string }) => <div data-testid="observation-content">{content}</div>,
}));

describe('DefaultToolFallback', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const defaultProps = {
    toolName: 'test_tool',
    args: { key: 'value' },
    argsText: '{"key": "value"}',
    result: undefined,
    isError: false,
    status: undefined,
  };

  it('should render tool name', () => {
    render(<DefaultToolFallback {...defaultProps} />);

    expect(screen.getByText('test_tool')).toBeInTheDocument();
  });

  it('should render chevron right when collapsed', () => {
    render(<DefaultToolFallback {...defaultProps} />);

    expect(screen.getByTestId('chevron-right')).toBeInTheDocument();
  });

  it('should expand when clicked', () => {
    render(<DefaultToolFallback {...defaultProps} />);

    const header = screen.getByText('test_tool').closest('.tool-call-header');
    fireEvent.click(header!);

    expect(screen.getByTestId('chevron-down')).toBeInTheDocument();
    expect(screen.getByText('Arguments')).toBeInTheDocument();
  });

  it('should show arguments when expanded', () => {
    render(<DefaultToolFallback {...defaultProps} />);

    const header = screen.getByText('test_tool').closest('.tool-call-header');
    fireEvent.click(header!);

    expect(screen.getByText(/key.*value/)).toBeInTheDocument();
  });

  it('should show Running... when status is running', () => {
    render(
      <DefaultToolFallback
        {...defaultProps}
        status={{ type: 'running' }}
      />
    );

    expect(screen.getByText('Running...')).toBeInTheDocument();
  });

  it('should auto-expand when running', () => {
    render(
      <DefaultToolFallback
        {...defaultProps}
        status={{ type: 'running' }}
      />
    );

    // Should be expanded and show Arguments
    expect(screen.getByText('Arguments (streaming...)')).toBeInTheDocument();
  });

  it('should show running icon when running', () => {
    render(
      <DefaultToolFallback
        {...defaultProps}
        status={{ type: 'running' }}
      />
    );

    // Should be expanded and show Arguments
    expect(screen.getByText('Arguments (streaming...)')).toBeInTheDocument();
  });

  it('should show error icon when error', () => {
    render(
      <DefaultToolFallback
        {...defaultProps}
        result="Error message"
        isError={true}
      />
    );

    const header = screen.getByText('test_tool').closest('.tool-call-header');
    fireEvent.click(header!);

    expect(screen.getByText('Error')).toBeInTheDocument();
    expect(screen.getByText('Error message')).toBeInTheDocument();
  });

  it('should show result when available', () => {
    render(
      <DefaultToolFallback
        {...defaultProps}
        result="Success result"
      />
    );

    const header = screen.getByText('test_tool').closest('.tool-call-header');
    fireEvent.click(header!);

    expect(screen.getByText('Result')).toBeInTheDocument();
    expect(screen.getByText('Success result')).toBeInTheDocument();
  });

  it('should auto-expand when running and show arguments', () => {
    render(
      <DefaultToolFallback
        {...defaultProps}
        status={{ type: 'running' }}
      />
    );

    // Should be auto-expanded because running
    expect(screen.getByTestId('chevron-down')).toBeInTheDocument();
  });

  describe('file_read tool', () => {
    it('should show file path in summary', () => {
      render(
        <DefaultToolFallback
          toolName="file_read"
          args={{ path: '/workspace/test.txt' }}
          argsText='{"path": "/workspace/test.txt"}'
          result={undefined}
          isError={false}
          status={undefined}
        />
      );

      expect(screen.getByText('/workspace/test.txt')).toBeInTheDocument();
    });
  });

  describe('bash tool', () => {
    it('should show command in summary', () => {
      render(
        <DefaultToolFallback
          toolName="bash"
          args={{ command: 'ls -la' }}
          argsText='{"command": "ls -la"}'
          result={undefined}
          isError={false}
          status={undefined}
        />
      );

      expect(screen.getByText('ls -la')).toBeInTheDocument();
    });

    it('should truncate long commands', () => {
      const longCommand = 'a'.repeat(100);
      render(
        <DefaultToolFallback
          toolName="bash"
          args={{ command: longCommand }}
          argsText={`{"command": "${longCommand}"}`}
          result={undefined}
          isError={false}
          status={undefined}
        />
      );

      expect(screen.getByText(longCommand.slice(0, 60) + '...')).toBeInTheDocument();
    });
  });

  describe('file_write tool', () => {
    it('should show file write with syntax highlighting', () => {
      render(
        <DefaultToolFallback
          toolName="file_write"
          args={{ path: '/workspace/test.js', content: 'console.log("hello")' }}
          argsText='{"path": "/workspace/test.js", "content": "console.log(\\"hello\\")"}'
          result={undefined}
          isError={false}
          status={undefined}
        />
      );

      const header = screen.getByText('file_write').closest('.tool-call-header');
      fireEvent.click(header!);

      expect(screen.getByText('File:')).toBeInTheDocument();
      expect(screen.getByTestId('syntax-highlighter')).toBeInTheDocument();
    });
  });

  describe('search tool', () => {
    it('should show search query and path in summary', () => {
      render(
        <DefaultToolFallback
          toolName="search"
          args={{ query: 'test', path: '/workspace' }}
          argsText='{"query": "test", "path": "/workspace"}'
          result={undefined}
          isError={false}
          status={undefined}
        />
      );

      expect(screen.getByText('"test" in /workspace')).toBeInTheDocument();
    });
  });

  describe('status handling', () => {
    it('should show incomplete status', () => {
      render(
        <DefaultToolFallback
          {...defaultProps}
          status={{ type: 'incomplete', reason: 'Timeout' }}
        />
      );

      const header = screen.getByText('test_tool').closest('.tool-call-header');
      fireEvent.click(header!);

      expect(screen.getByText('Incomplete:')).toBeInTheDocument();
      expect(screen.getByText('Timeout')).toBeInTheDocument();
    });

    it('should show requires-action status', () => {
      render(
        <DefaultToolFallback
          {...defaultProps}
          status={{ type: 'requires-action', reason: 'User approval needed' }}
        />
      );

      const header = screen.getByText('test_tool').closest('.tool-call-header');
      fireEvent.click(header!);

      expect(screen.getByText('Action Required:')).toBeInTheDocument();
      expect(screen.getByText('User approval needed')).toBeInTheDocument();
    });
  });

  it('should handle binary result', () => {
    render(
      <DefaultToolFallback
        {...defaultProps}
        result={{ is_binary: true, text: 'Binary content' }}
      />
    );

    const header = screen.getByText('test_tool').closest('.tool-call-header');
    fireEvent.click(header!);

    expect(screen.getByTestId('observation-content')).toBeInTheDocument();
    expect(screen.getByText('Binary content')).toBeInTheDocument();
  });

  it('should toggle expand/collapse', () => {
    render(<DefaultToolFallback {...defaultProps} />);

    const header = screen.getByText('test_tool').closest('.tool-call-header');

    // Expand
    fireEvent.click(header!);
    expect(screen.getByTestId('chevron-down')).toBeInTheDocument();

    // Collapse
    fireEvent.click(header!);
    expect(screen.getByTestId('chevron-right')).toBeInTheDocument();
  });
});
