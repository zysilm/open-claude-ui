import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ChatSessionTabs from '../ChatSessionTabs';
import { chatSessionsAPI } from '@/services/api';
import type { ChatSession } from '@/types';

// Mock the API
vi.mock('@/services/api', () => ({
  chatSessionsAPI: {
    delete: vi.fn(),
  },
}));

// Mock window.confirm
vi.stubGlobal('confirm', vi.fn());

describe('ChatSessionTabs', () => {
  let queryClient: QueryClient;
  const mockOnSelectSession = vi.fn();

  const mockSessions: ChatSession[] = [
    {
      id: 'session-1',
      name: 'Session 1',
      project_id: 'project-1',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    },
    {
      id: 'session-2',
      name: 'Session 2',
      project_id: 'project-1',
      created_at: '2024-01-02T00:00:00Z',
      updated_at: '2024-01-02T00:00:00Z',
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
  });

  const renderTabs = (
    sessions: ChatSession[] = mockSessions,
    activeSessionId: string | null = null
  ) => {
    return render(
      <QueryClientProvider client={queryClient}>
        <ChatSessionTabs
          sessions={sessions}
          activeSessionId={activeSessionId}
          onSelectSession={mockOnSelectSession}
        />
      </QueryClientProvider>
    );
  };

  it('should render session tabs', () => {
    renderTabs();

    expect(screen.getByText('Session 1')).toBeInTheDocument();
    expect(screen.getByText('Session 2')).toBeInTheDocument();
  });

  it('should show empty message when no sessions', () => {
    renderTabs([]);

    expect(screen.getByText('No chat sessions yet')).toBeInTheDocument();
  });

  it('should highlight active session', () => {
    const { container } = renderTabs(mockSessions, 'session-1');

    const activeTab = container.querySelector('.chat-session-tab.active');
    expect(activeTab).toBeInTheDocument();
    expect(activeTab).toHaveTextContent('Session 1');
  });

  it('should not highlight any session when activeSessionId is null', () => {
    const { container } = renderTabs(mockSessions, null);

    const activeTab = container.querySelector('.chat-session-tab.active');
    expect(activeTab).not.toBeInTheDocument();
  });

  it('should call onSelectSession when tab is clicked', async () => {
    renderTabs();

    const sessionTab = screen.getByText('Session 1').closest('.chat-session-tab');
    await userEvent.click(sessionTab!);

    expect(mockOnSelectSession).toHaveBeenCalledWith('session-1');
  });

  it('should render delete button for each session', () => {
    renderTabs();

    const deleteButtons = screen.getAllByTitle('Delete session');
    expect(deleteButtons).toHaveLength(2);
  });

  it('should confirm before deleting session', async () => {
    vi.mocked(window.confirm).mockReturnValue(false);

    renderTabs();

    const deleteButtons = screen.getAllByTitle('Delete session');
    await userEvent.click(deleteButtons[0]);

    expect(window.confirm).toHaveBeenCalledWith('Delete this chat session?');
    expect(chatSessionsAPI.delete).not.toHaveBeenCalled();
  });

  it('should call delete API when confirmed', async () => {
    vi.mocked(window.confirm).mockReturnValue(true);
    vi.mocked(chatSessionsAPI.delete).mockResolvedValueOnce(undefined);

    renderTabs();

    const deleteButtons = screen.getAllByTitle('Delete session');
    await userEvent.click(deleteButtons[0]);

    expect(chatSessionsAPI.delete).toHaveBeenCalled();
    const call = vi.mocked(chatSessionsAPI.delete).mock.calls[0];
    expect(call[0]).toBe('session-1');
  });

  it('should not trigger tab selection when delete button is clicked', async () => {
    vi.mocked(window.confirm).mockReturnValue(false);

    renderTabs();

    const deleteButtons = screen.getAllByTitle('Delete session');
    await userEvent.click(deleteButtons[0]);

    // onSelectSession should not be called because stopPropagation is used
    expect(mockOnSelectSession).not.toHaveBeenCalled();
  });

  it('should clear selection when active session is deleted', async () => {
    vi.mocked(window.confirm).mockReturnValue(true);
    vi.mocked(chatSessionsAPI.delete).mockResolvedValueOnce(undefined);

    renderTabs(mockSessions, 'session-1');

    const deleteButtons = screen.getAllByTitle('Delete session');
    await userEvent.click(deleteButtons[0]);

    await waitFor(() => {
      expect(mockOnSelectSession).toHaveBeenCalledWith(null);
    });
  });

  it('should not clear selection when deleting non-active session', async () => {
    vi.mocked(window.confirm).mockReturnValue(true);
    vi.mocked(chatSessionsAPI.delete).mockResolvedValueOnce(undefined);

    renderTabs(mockSessions, 'session-1');

    // Delete session-2 (not active)
    const deleteButtons = screen.getAllByTitle('Delete session');
    await userEvent.click(deleteButtons[1]);

    await waitFor(() => {
      expect(chatSessionsAPI.delete).toHaveBeenCalled();
    });

    // Should not call onSelectSession with null
    expect(mockOnSelectSession).not.toHaveBeenCalledWith(null);
  });

  it('should have correct CSS classes', () => {
    const { container } = renderTabs();

    expect(container.querySelector('.chat-session-tabs')).toBeInTheDocument();
    expect(container.querySelectorAll('.chat-session-tab')).toHaveLength(2);
    expect(container.querySelectorAll('.session-name')).toHaveLength(2);
    expect(container.querySelectorAll('.delete-session-btn')).toHaveLength(2);
  });
});
