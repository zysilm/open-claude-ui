import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import ProjectList from '../ProjectList';
import { projectsAPI } from '@/services/api';
import { useUIStore } from '@/stores/uiStore';

// Mock the API
vi.mock('@/services/api', () => ({
  projectsAPI: {
    list: vi.fn(),
    delete: vi.fn(),
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

describe('ProjectList', () => {
  let queryClient: QueryClient;

  const mockProjects = [
    {
      id: 'project-1',
      name: 'First Project',
      description: 'Description 1',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    },
    {
      id: 'project-2',
      name: 'Second Project',
      description: 'Description 2',
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
    // Reset UI store
    useUIStore.setState({ isCreateProjectModalOpen: false });
  });

  const renderProjectList = () => {
    return render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <ProjectList />
        </BrowserRouter>
      </QueryClientProvider>
    );
  };

  it('should render header with title', async () => {
    vi.mocked(projectsAPI.list).mockResolvedValueOnce({ projects: [], total: 0 });

    renderProjectList();

    expect(screen.getByText('Projects')).toBeInTheDocument();
  });

  it('should render New Project button', async () => {
    vi.mocked(projectsAPI.list).mockResolvedValueOnce({ projects: [], total: 0 });

    renderProjectList();

    expect(screen.getByText('+ New Project')).toBeInTheDocument();
  });

  it('should render Settings button', async () => {
    vi.mocked(projectsAPI.list).mockResolvedValueOnce({ projects: [], total: 0 });

    renderProjectList();

    expect(screen.getByTitle('Manage API Keys')).toBeInTheDocument();
  });

  it('should show loading state', () => {
    vi.mocked(projectsAPI.list).mockImplementation(() => new Promise(() => {}));

    renderProjectList();

    expect(screen.getByText('Loading projects...')).toBeInTheDocument();
  });

  it('should render projects after loading', async () => {
    vi.mocked(projectsAPI.list).mockResolvedValueOnce({
      projects: mockProjects,
      total: 2,
    });

    renderProjectList();

    await waitFor(() => {
      expect(screen.getByText('First Project')).toBeInTheDocument();
      expect(screen.getByText('Second Project')).toBeInTheDocument();
    });
  });

  it('should show error message on fetch failure', async () => {
    vi.mocked(projectsAPI.list).mockRejectedValueOnce(new Error('Network error'));

    renderProjectList();

    await waitFor(() => {
      expect(screen.getByText(/Error loading projects/)).toBeInTheDocument();
    });
  });

  it('should show empty state when no projects', async () => {
    vi.mocked(projectsAPI.list).mockResolvedValueOnce({ projects: [], total: 0 });

    renderProjectList();

    await waitFor(() => {
      expect(screen.getByText(/No projects yet/)).toBeInTheDocument();
    });
  });

  it('should filter projects by search query', async () => {
    vi.mocked(projectsAPI.list).mockResolvedValueOnce({
      projects: mockProjects,
      total: 2,
    });

    renderProjectList();

    await waitFor(() => {
      expect(screen.getByText('First Project')).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText('Search projects...');
    await userEvent.type(searchInput, 'First');

    expect(screen.getByText('First Project')).toBeInTheDocument();
    expect(screen.queryByText('Second Project')).not.toBeInTheDocument();
  });

  it('should show no results message when search has no matches', async () => {
    vi.mocked(projectsAPI.list).mockResolvedValueOnce({
      projects: mockProjects,
      total: 2,
    });

    renderProjectList();

    await waitFor(() => {
      expect(screen.getByText('First Project')).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText('Search projects...');
    await userEvent.type(searchInput, 'nonexistent');

    expect(screen.getByText(/No projects found matching your search/)).toBeInTheDocument();
  });

  it('should filter by description as well', async () => {
    vi.mocked(projectsAPI.list).mockResolvedValueOnce({
      projects: mockProjects,
      total: 2,
    });

    renderProjectList();

    await waitFor(() => {
      expect(screen.getByText('First Project')).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText('Search projects...');
    await userEvent.type(searchInput, 'Description 2');

    expect(screen.queryByText('First Project')).not.toBeInTheDocument();
    expect(screen.getByText('Second Project')).toBeInTheDocument();
  });

  it('should navigate to settings when Settings button is clicked', async () => {
    vi.mocked(projectsAPI.list).mockResolvedValueOnce({ projects: [], total: 0 });

    renderProjectList();

    const settingsButton = screen.getByTitle('Manage API Keys');
    await userEvent.click(settingsButton);

    expect(mockNavigate).toHaveBeenCalledWith('/settings');
  });

  it('should open modal when New Project is clicked', async () => {
    vi.mocked(projectsAPI.list).mockResolvedValueOnce({ projects: [], total: 0 });

    renderProjectList();

    const newProjectButton = screen.getByText('+ New Project');
    await userEvent.click(newProjectButton);

    expect(useUIStore.getState().isCreateProjectModalOpen).toBe(true);
  });

  it('should call delete API with confirmation', async () => {
    vi.mocked(projectsAPI.list).mockResolvedValueOnce({
      projects: mockProjects,
      total: 2,
    });
    vi.mocked(projectsAPI.delete).mockResolvedValueOnce(undefined);
    vi.mocked(window.confirm).mockReturnValue(true);

    renderProjectList();

    await waitFor(() => {
      expect(screen.getByText('First Project')).toBeInTheDocument();
    });

    const deleteButtons = screen.getAllByTitle('Delete project');
    await userEvent.click(deleteButtons[0]);

    expect(window.confirm).toHaveBeenCalledWith('Are you sure you want to delete this project?');
    expect(projectsAPI.delete).toHaveBeenCalled();
    const call = vi.mocked(projectsAPI.delete).mock.calls[0];
    expect(call[0]).toBe('project-1');
  });

  it('should not call delete API when confirmation is cancelled', async () => {
    vi.mocked(projectsAPI.list).mockResolvedValueOnce({
      projects: mockProjects,
      total: 2,
    });
    vi.mocked(window.confirm).mockReturnValue(false);

    renderProjectList();

    await waitFor(() => {
      expect(screen.getByText('First Project')).toBeInTheDocument();
    });

    const deleteButtons = screen.getAllByTitle('Delete project');
    await userEvent.click(deleteButtons[0]);

    expect(window.confirm).toHaveBeenCalled();
    expect(projectsAPI.delete).not.toHaveBeenCalled();
  });

  it('should render modal when isCreateProjectModalOpen is true', async () => {
    vi.mocked(projectsAPI.list).mockResolvedValueOnce({ projects: [], total: 0 });

    // Set modal to open
    useUIStore.setState({ isCreateProjectModalOpen: true });

    renderProjectList();

    await waitFor(() => {
      expect(screen.getByText('Create New Project')).toBeInTheDocument();
    });
  });
});
