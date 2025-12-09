import { describe, it, expect, beforeEach } from 'vitest';
import { useProjectStore } from '../projectStore';
import type { Project } from '@/types';

describe('projectStore', () => {
  const mockProject: Project = {
    id: 'project-123',
    name: 'Test Project',
    description: 'A test project',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  };

  beforeEach(() => {
    // Reset store state before each test
    useProjectStore.setState({ selectedProject: null });
  });

  describe('initial state', () => {
    it('should have null as initial selectedProject', () => {
      const state = useProjectStore.getState();
      expect(state.selectedProject).toBeNull();
    });
  });

  describe('setSelectedProject', () => {
    it('should set the selected project', () => {
      const { setSelectedProject } = useProjectStore.getState();

      setSelectedProject(mockProject);

      const state = useProjectStore.getState();
      expect(state.selectedProject).toEqual(mockProject);
    });

    it('should clear the selected project when set to null', () => {
      const { setSelectedProject } = useProjectStore.getState();

      // First set a project
      setSelectedProject(mockProject);
      expect(useProjectStore.getState().selectedProject).toEqual(mockProject);

      // Then clear it
      setSelectedProject(null);
      expect(useProjectStore.getState().selectedProject).toBeNull();
    });

    it('should replace the selected project with a new one', () => {
      const { setSelectedProject } = useProjectStore.getState();
      const newProject: Project = {
        id: 'project-456',
        name: 'Another Project',
        description: 'Another test project',
        created_at: '2024-01-02T00:00:00Z',
        updated_at: '2024-01-02T00:00:00Z',
      };

      setSelectedProject(mockProject);
      setSelectedProject(newProject);

      const state = useProjectStore.getState();
      expect(state.selectedProject).toEqual(newProject);
      expect(state.selectedProject?.id).toBe('project-456');
    });
  });

  describe('state persistence', () => {
    it('should maintain state across multiple getState calls', () => {
      const { setSelectedProject } = useProjectStore.getState();

      setSelectedProject(mockProject);

      // Multiple getState calls should return the same state
      expect(useProjectStore.getState().selectedProject).toEqual(mockProject);
      expect(useProjectStore.getState().selectedProject).toEqual(mockProject);
    });
  });
});
