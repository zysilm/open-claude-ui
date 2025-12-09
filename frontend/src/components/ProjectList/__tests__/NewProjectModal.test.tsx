import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import NewProjectModal from '../NewProjectModal';
import { projectsAPI } from '@/services/api';

// Mock the API
vi.mock('@/services/api', () => ({
  projectsAPI: {
    create: vi.fn(),
  },
}));

describe('NewProjectModal', () => {
  const mockOnClose = vi.fn();
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

  const renderModal = () => {
    return render(
      <QueryClientProvider client={queryClient}>
        <NewProjectModal onClose={mockOnClose} />
      </QueryClientProvider>
    );
  };

  it('should render modal with title', () => {
    renderModal();
    expect(screen.getByText('Create New Project')).toBeInTheDocument();
  });

  it('should render project name input', () => {
    renderModal();
    expect(screen.getByLabelText('Project Name *')).toBeInTheDocument();
  });

  it('should render description textarea', () => {
    renderModal();
    expect(screen.getByLabelText('Description')).toBeInTheDocument();
  });

  it('should render Create Project button', () => {
    renderModal();
    expect(screen.getByRole('button', { name: 'Create Project' })).toBeInTheDocument();
  });

  it('should render Cancel button', () => {
    renderModal();
    expect(screen.getByRole('button', { name: 'Cancel' })).toBeInTheDocument();
  });

  it('should call onClose when Cancel is clicked', async () => {
    renderModal();

    const cancelButton = screen.getByRole('button', { name: 'Cancel' });
    await userEvent.click(cancelButton);

    expect(mockOnClose).toHaveBeenCalledTimes(1);
  });

  it('should call onClose when close button (×) is clicked', async () => {
    renderModal();

    const closeButton = screen.getByText('×');
    await userEvent.click(closeButton);

    expect(mockOnClose).toHaveBeenCalledTimes(1);
  });

  it('should call onClose when overlay is clicked', async () => {
    const { container } = renderModal();

    const overlay = container.querySelector('.modal-overlay');
    fireEvent.click(overlay!);

    expect(mockOnClose).toHaveBeenCalledTimes(1);
  });

  it('should not call onClose when modal content is clicked', async () => {
    const { container } = renderModal();

    const modalContent = container.querySelector('.modal-content');
    fireEvent.click(modalContent!);

    expect(mockOnClose).not.toHaveBeenCalled();
  });

  it('should disable Create button when name is empty', () => {
    renderModal();

    const createButton = screen.getByRole('button', { name: 'Create Project' });
    expect(createButton).toBeDisabled();
  });

  it('should enable Create button when name is provided', async () => {
    renderModal();

    const nameInput = screen.getByLabelText('Project Name *');
    await userEvent.type(nameInput, 'My Project');

    const createButton = screen.getByRole('button', { name: 'Create Project' });
    expect(createButton).toBeEnabled();
  });

  it('should call API create when form is submitted', async () => {
    vi.mocked(projectsAPI.create).mockResolvedValueOnce({
      id: 'new-project-id',
      name: 'My Project',
      created_at: '2024-01-01',
      updated_at: '2024-01-01',
    });

    renderModal();

    const nameInput = screen.getByLabelText('Project Name *');
    await userEvent.type(nameInput, 'My Project');

    const createButton = screen.getByRole('button', { name: 'Create Project' });
    await userEvent.click(createButton);

    await waitFor(() => {
      expect(projectsAPI.create).toHaveBeenCalled();
      const call = vi.mocked(projectsAPI.create).mock.calls[0];
      expect(call[0]).toEqual({
        name: 'My Project',
        description: undefined,
      });
    });
  });

  it('should call API create with description when provided', async () => {
    vi.mocked(projectsAPI.create).mockResolvedValueOnce({
      id: 'new-project-id',
      name: 'My Project',
      description: 'Test description',
      created_at: '2024-01-01',
      updated_at: '2024-01-01',
    });

    renderModal();

    const nameInput = screen.getByLabelText('Project Name *');
    const descInput = screen.getByLabelText('Description');

    await userEvent.type(nameInput, 'My Project');
    await userEvent.type(descInput, 'Test description');

    const createButton = screen.getByRole('button', { name: 'Create Project' });
    await userEvent.click(createButton);

    await waitFor(() => {
      expect(projectsAPI.create).toHaveBeenCalled();
      const call = vi.mocked(projectsAPI.create).mock.calls[0];
      expect(call[0]).toEqual({
        name: 'My Project',
        description: 'Test description',
      });
    });
  });

  it('should close modal on successful creation', async () => {
    vi.mocked(projectsAPI.create).mockResolvedValueOnce({
      id: 'new-project-id',
      name: 'My Project',
      created_at: '2024-01-01',
      updated_at: '2024-01-01',
    });

    renderModal();

    const nameInput = screen.getByLabelText('Project Name *');
    await userEvent.type(nameInput, 'My Project');

    const createButton = screen.getByRole('button', { name: 'Create Project' });
    await userEvent.click(createButton);

    await waitFor(() => {
      expect(mockOnClose).toHaveBeenCalled();
    });
  });

  it('should show error message on creation failure', async () => {
    vi.mocked(projectsAPI.create).mockRejectedValueOnce(new Error('Failed to create'));

    renderModal();

    const nameInput = screen.getByLabelText('Project Name *');
    await userEvent.type(nameInput, 'My Project');

    const createButton = screen.getByRole('button', { name: 'Create Project' });
    await userEvent.click(createButton);

    await waitFor(() => {
      expect(screen.getByText(/Error creating project/)).toBeInTheDocument();
    });
  });

  it('should trim whitespace from name before submitting', async () => {
    vi.mocked(projectsAPI.create).mockResolvedValueOnce({
      id: 'new-project-id',
      name: 'Trimmed Name',
      created_at: '2024-01-01',
      updated_at: '2024-01-01',
    });

    renderModal();

    const nameInput = screen.getByLabelText('Project Name *');
    await userEvent.type(nameInput, '  Trimmed Name  ');

    const createButton = screen.getByRole('button', { name: 'Create Project' });
    await userEvent.click(createButton);

    await waitFor(() => {
      expect(projectsAPI.create).toHaveBeenCalled();
      const call = vi.mocked(projectsAPI.create).mock.calls[0];
      expect(call[0]).toEqual({
        name: 'Trimmed Name',
        description: undefined,
      });
    });
  });

  it('should not submit when name is only whitespace', async () => {
    renderModal();

    const nameInput = screen.getByLabelText('Project Name *');
    await userEvent.type(nameInput, '   ');

    const createButton = screen.getByRole('button', { name: 'Create Project' });
    expect(createButton).toBeDisabled();
  });

  it('should show Creating... text while pending', async () => {
    // Make the API call hang
    vi.mocked(projectsAPI.create).mockImplementation(() => new Promise(() => {}));

    renderModal();

    const nameInput = screen.getByLabelText('Project Name *');
    await userEvent.type(nameInput, 'My Project');

    const createButton = screen.getByRole('button', { name: 'Create Project' });
    await userEvent.click(createButton);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Creating...' })).toBeInTheDocument();
    });
  });
});
