import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { projectsAPI } from '@/services/api';
import { useUIStore } from '@/stores/uiStore';
import ProjectCard from './ProjectCard';
import ProjectSearch from './ProjectSearch';
import NewProjectModal from './NewProjectModal';
import './ProjectList.css';

export default function ProjectList() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [searchQuery, setSearchQuery] = useState('');
  const { isCreateProjectModalOpen, setCreateProjectModalOpen } = useUIStore();

  // Fetch projects
  const { data, isLoading, error } = useQuery({
    queryKey: ['projects'],
    queryFn: projectsAPI.list,
  });

  // Delete project mutation
  const deleteMutation = useMutation({
    mutationFn: projectsAPI.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
    },
  });

  // Filter projects based on search query
  const filteredProjects = data?.projects.filter((project) =>
    project.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    project.description?.toLowerCase().includes(searchQuery.toLowerCase())
  ) || [];

  const handleDeleteProject = (id: string) => {
    if (confirm('Are you sure you want to delete this project?')) {
      deleteMutation.mutate(id);
    }
  };

  return (
    <div className="project-list-container">
      <div className="project-list-header">
        <h1>Projects</h1>
        <div className="header-actions">
          <button
            className="settings-btn"
            onClick={() => navigate('/settings')}
            title="Manage API Keys"
          >
            ⚙️ Settings
          </button>
          <button
            className="create-project-btn"
            onClick={() => setCreateProjectModalOpen(true)}
          >
            + New Project
          </button>
        </div>
      </div>

      <ProjectSearch value={searchQuery} onChange={setSearchQuery} />

      {isLoading && (
        <div className="loading">Loading projects...</div>
      )}

      {error && (
        <div className="error">
          Error loading projects: {error instanceof Error ? error.message : 'Unknown error'}
        </div>
      )}

      <div className="projects-grid">
        {filteredProjects.map((project) => (
          <ProjectCard
            key={project.id}
            project={project}
            onDelete={() => handleDeleteProject(project.id)}
          />
        ))}

        {filteredProjects.length === 0 && !isLoading && (
          <div className="no-projects">
            {searchQuery
              ? 'No projects found matching your search.'
              : 'No projects yet. Create your first project to get started!'}
          </div>
        )}
      </div>

      {isCreateProjectModalOpen && (
        <NewProjectModal
          onClose={() => setCreateProjectModalOpen(false)}
        />
      )}
    </div>
  );
}
