import { describe, it, expect, beforeEach } from 'vitest';
import { useChatStore } from '../chatStore';
import type { AgentAction, StreamEvent } from '@/types';

describe('chatStore', () => {
  beforeEach(() => {
    // Reset store state before each test
    useChatStore.setState({
      activeSessionId: null,
      streamingMessage: '',
      isStreaming: false,
      agentActions: [],
      streamEvents: [],
      error: null,
    });
  });

  describe('initial state', () => {
    it('should have correct initial state', () => {
      const state = useChatStore.getState();

      expect(state.activeSessionId).toBeNull();
      expect(state.streamingMessage).toBe('');
      expect(state.isStreaming).toBe(false);
      expect(state.agentActions).toEqual([]);
      expect(state.streamEvents).toEqual([]);
      expect(state.error).toBeNull();
    });
  });

  describe('setActiveSession', () => {
    it('should set the active session ID', () => {
      const { setActiveSession } = useChatStore.getState();

      setActiveSession('session-123');

      expect(useChatStore.getState().activeSessionId).toBe('session-123');
    });

    it('should clear the active session when set to null', () => {
      const { setActiveSession } = useChatStore.getState();

      setActiveSession('session-123');
      setActiveSession(null);

      expect(useChatStore.getState().activeSessionId).toBeNull();
    });
  });

  describe('streamingMessage', () => {
    it('should append chunks to streaming message', () => {
      const { appendStreamingMessage } = useChatStore.getState();

      appendStreamingMessage('Hello ');
      appendStreamingMessage('World');

      expect(useChatStore.getState().streamingMessage).toBe('Hello World');
    });

    it('should clear streaming message', () => {
      const { appendStreamingMessage, clearStreamingMessage } = useChatStore.getState();

      appendStreamingMessage('Some content');
      clearStreamingMessage();

      expect(useChatStore.getState().streamingMessage).toBe('');
    });

    it('should handle empty chunks', () => {
      const { appendStreamingMessage } = useChatStore.getState();

      appendStreamingMessage('');
      appendStreamingMessage('Hello');
      appendStreamingMessage('');

      expect(useChatStore.getState().streamingMessage).toBe('Hello');
    });
  });

  describe('setStreaming', () => {
    it('should set streaming to true', () => {
      const { setStreaming } = useChatStore.getState();

      setStreaming(true);

      expect(useChatStore.getState().isStreaming).toBe(true);
    });

    it('should set streaming to false', () => {
      const { setStreaming } = useChatStore.getState();

      setStreaming(true);
      setStreaming(false);

      expect(useChatStore.getState().isStreaming).toBe(false);
    });
  });

  describe('agentActions', () => {
    it('should add agent actions', () => {
      const { addAgentAction } = useChatStore.getState();
      const action: AgentAction = {
        type: 'action',
        content: 'Executing command',
        tool: 'bash',
        args: { command: 'ls' },
        step: 1,
      };

      addAgentAction(action);

      expect(useChatStore.getState().agentActions).toHaveLength(1);
      expect(useChatStore.getState().agentActions[0]).toEqual(action);
    });

    it('should accumulate multiple agent actions', () => {
      const { addAgentAction } = useChatStore.getState();
      const action1: AgentAction = {
        type: 'thought',
        content: 'Thinking...',
        step: 1,
      };
      const action2: AgentAction = {
        type: 'action',
        content: 'Running command',
        tool: 'bash',
        step: 2,
      };

      addAgentAction(action1);
      addAgentAction(action2);

      expect(useChatStore.getState().agentActions).toHaveLength(2);
    });

    it('should clear agent actions', () => {
      const { addAgentAction, clearAgentActions } = useChatStore.getState();
      const action: AgentAction = {
        type: 'action',
        content: 'Test',
        step: 1,
      };

      addAgentAction(action);
      clearAgentActions();

      expect(useChatStore.getState().agentActions).toEqual([]);
    });
  });

  describe('streamEvents', () => {
    it('should add stream events', () => {
      const { addStreamEvent } = useChatStore.getState();
      const event: StreamEvent = {
        type: 'chunk',
        content: 'Hello',
      };

      addStreamEvent(event);

      expect(useChatStore.getState().streamEvents).toHaveLength(1);
      expect(useChatStore.getState().streamEvents[0]).toEqual(event);
    });

    it('should accumulate multiple stream events', () => {
      const { addStreamEvent } = useChatStore.getState();
      const events: StreamEvent[] = [
        { type: 'assistant_text_start' },
        { type: 'chunk', content: 'Hello' },
        { type: 'chunk', content: ' World' },
        { type: 'assistant_text_end' },
      ];

      events.forEach(addStreamEvent);

      expect(useChatStore.getState().streamEvents).toHaveLength(4);
    });

    it('should clear stream events', () => {
      const { addStreamEvent, clearStreamEvents } = useChatStore.getState();

      addStreamEvent({ type: 'chunk', content: 'Test' });
      clearStreamEvents();

      expect(useChatStore.getState().streamEvents).toEqual([]);
    });

    it('should handle tool call events', () => {
      const { addStreamEvent } = useChatStore.getState();
      const event: StreamEvent = {
        type: 'action',
        tool: 'bash',
        args: { command: 'ls -la' },
        step: 1,
      };

      addStreamEvent(event);

      const state = useChatStore.getState();
      expect(state.streamEvents[0].tool).toBe('bash');
      expect(state.streamEvents[0].args).toEqual({ command: 'ls -la' });
    });
  });

  describe('error handling', () => {
    it('should set error message', () => {
      const { setError } = useChatStore.getState();

      setError('Connection failed');

      expect(useChatStore.getState().error).toBe('Connection failed');
    });

    it('should clear error', () => {
      const { setError, clearError } = useChatStore.getState();

      setError('Some error');
      clearError();

      expect(useChatStore.getState().error).toBeNull();
    });

    it('should replace existing error', () => {
      const { setError } = useChatStore.getState();

      setError('First error');
      setError('Second error');

      expect(useChatStore.getState().error).toBe('Second error');
    });
  });

  describe('combined operations', () => {
    it('should handle a complete streaming session lifecycle', () => {
      const state = useChatStore.getState();

      // Start session
      state.setActiveSession('session-1');
      state.setStreaming(true);

      // Receive chunks
      state.appendStreamingMessage('Hello ');
      state.addStreamEvent({ type: 'chunk', content: 'Hello ' });
      state.appendStreamingMessage('World');
      state.addStreamEvent({ type: 'chunk', content: 'World' });

      // Verify mid-stream state
      expect(useChatStore.getState().isStreaming).toBe(true);
      expect(useChatStore.getState().streamingMessage).toBe('Hello World');
      expect(useChatStore.getState().streamEvents).toHaveLength(2);

      // End streaming
      state.setStreaming(false);
      state.clearStreamingMessage();
      state.clearStreamEvents();

      // Verify end state
      expect(useChatStore.getState().isStreaming).toBe(false);
      expect(useChatStore.getState().streamingMessage).toBe('');
      expect(useChatStore.getState().streamEvents).toEqual([]);
    });
  });
});
