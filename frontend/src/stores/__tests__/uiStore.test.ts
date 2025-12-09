import { describe, it, expect, beforeEach } from 'vitest';
import { useUIStore } from '../uiStore';

describe('uiStore', () => {
  beforeEach(() => {
    // Reset store state before each test
    useUIStore.setState({ isCreateProjectModalOpen: false });
  });

  describe('initial state', () => {
    it('should have isCreateProjectModalOpen as false initially', () => {
      const state = useUIStore.getState();
      expect(state.isCreateProjectModalOpen).toBe(false);
    });
  });

  describe('setCreateProjectModalOpen', () => {
    it('should open the modal when set to true', () => {
      const { setCreateProjectModalOpen } = useUIStore.getState();

      setCreateProjectModalOpen(true);

      expect(useUIStore.getState().isCreateProjectModalOpen).toBe(true);
    });

    it('should close the modal when set to false', () => {
      const { setCreateProjectModalOpen } = useUIStore.getState();

      // First open the modal
      setCreateProjectModalOpen(true);
      expect(useUIStore.getState().isCreateProjectModalOpen).toBe(true);

      // Then close it
      setCreateProjectModalOpen(false);
      expect(useUIStore.getState().isCreateProjectModalOpen).toBe(false);
    });

    it('should toggle modal state correctly', () => {
      const { setCreateProjectModalOpen } = useUIStore.getState();

      // Toggle on
      setCreateProjectModalOpen(true);
      expect(useUIStore.getState().isCreateProjectModalOpen).toBe(true);

      // Toggle off
      setCreateProjectModalOpen(false);
      expect(useUIStore.getState().isCreateProjectModalOpen).toBe(false);

      // Toggle on again
      setCreateProjectModalOpen(true);
      expect(useUIStore.getState().isCreateProjectModalOpen).toBe(true);
    });
  });

  describe('state persistence', () => {
    it('should maintain state across multiple getState calls', () => {
      const { setCreateProjectModalOpen } = useUIStore.getState();

      setCreateProjectModalOpen(true);

      // Multiple getState calls should return the same state
      expect(useUIStore.getState().isCreateProjectModalOpen).toBe(true);
      expect(useUIStore.getState().isCreateProjectModalOpen).toBe(true);
    });
  });
});
