import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import ProjectCard from '../ProjectCard';
import type { Project } from '@/types';

// Mock useNavigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe('ProjectCard', () => {
  const mockProject: Project = {
    id: 'project-123',
    name: 'Test Project',
    description: 'A test project description',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-06-15T12:30:00Z',
  };

  const mockOnDelete = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderProjectCard = (project: Project = mockProject) => {
    return render(
      <BrowserRouter>
        <ProjectCard project={project} onDelete={mockOnDelete} />
      </BrowserRouter>
    );
  };

  it('should render project name', () => {
    renderProjectCard();
    expect(screen.getByText('Test Project')).toBeInTheDocument();
  });

  it('should render project description', () => {
    renderProjectCard();
    expect(screen.getByText('A test project description')).toBeInTheDocument();
  });

  it('should render "No description" when description is empty', () => {
    const projectWithoutDescription: Project = {
      ...mockProject,
      description: undefined,
    };
    renderProjectCard(projectWithoutDescription);
    expect(screen.getByText('No description')).toBeInTheDocument();
  });

  it('should render formatted date', () => {
    renderProjectCard();
    // The date format should show "Jun 15, 2024"
    expect(screen.getByText(/Updated Jun 15, 2024/)).toBeInTheDocument();
  });

  it('should navigate to project page when card is clicked', () => {
    renderProjectCard();

    const card = screen.getByText('Test Project').closest('.project-card');
    fireEvent.click(card!);

    expect(mockNavigate).toHaveBeenCalledWith('/projects/project-123');
  });

  it('should call onDelete when delete button is clicked', () => {
    renderProjectCard();

    const deleteButton = screen.getByTitle('Delete project');
    fireEvent.click(deleteButton);

    expect(mockOnDelete).toHaveBeenCalledTimes(1);
  });

  it('should not navigate when delete button is clicked', () => {
    renderProjectCard();

    const deleteButton = screen.getByTitle('Delete project');
    fireEvent.click(deleteButton);

    expect(mockNavigate).not.toHaveBeenCalled();
  });

  it('should have correct CSS classes', () => {
    const { container } = renderProjectCard();

    expect(container.querySelector('.project-card')).toBeInTheDocument();
    expect(container.querySelector('.project-card-header')).toBeInTheDocument();
    expect(container.querySelector('.project-name')).toBeInTheDocument();
    expect(container.querySelector('.project-description')).toBeInTheDocument();
    expect(container.querySelector('.project-card-footer')).toBeInTheDocument();
  });

  it('should render delete button with × symbol', () => {
    renderProjectCard();

    const deleteButton = screen.getByTitle('Delete project');
    expect(deleteButton).toHaveTextContent('×');
  });
});
