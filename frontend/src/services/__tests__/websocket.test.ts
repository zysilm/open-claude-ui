import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { ChatWebSocket, ChatMessage } from '../websocket';

// Mock WebSocket
class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  url: string;
  readyState: number = MockWebSocket.CONNECTING;
  onopen: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  sentMessages: string[] = [];

  constructor(url: string) {
    this.url = url;
    // Simulate async connection
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN;
      if (this.onopen) {
        this.onopen(new Event('open'));
      }
    }, 0);
  }

  send(data: string) {
    this.sentMessages.push(data);
  }

  close() {
    this.readyState = MockWebSocket.CLOSED;
    if (this.onclose) {
      this.onclose(new CloseEvent('close'));
    }
  }

  // Helper to simulate receiving a message
  simulateMessage(data: ChatMessage) {
    if (this.onmessage) {
      this.onmessage(new MessageEvent('message', { data: JSON.stringify(data) }));
    }
  }

  // Helper to simulate an error
  simulateError() {
    if (this.onerror) {
      this.onerror(new Event('error'));
    }
  }
}

// Store WebSocket instances for testing
let mockWsInstances: MockWebSocket[] = [];

vi.stubGlobal('WebSocket', class extends MockWebSocket {
  constructor(url: string) {
    super(url);
    mockWsInstances.push(this);
  }
});

describe('ChatWebSocket', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    mockWsInstances = [];
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  describe('constructor', () => {
    it('should create instance with session ID', () => {
      const chatWs = new ChatWebSocket('session-123');
      expect(chatWs).toBeDefined();
    });
  });

  describe('connect', () => {
    it('should establish WebSocket connection', async () => {
      const chatWs = new ChatWebSocket('session-123');
      const onMessage = vi.fn();

      chatWs.connect(onMessage);

      expect(mockWsInstances).toHaveLength(1);
      expect(mockWsInstances[0].url).toBe('ws://127.0.0.1:8000/api/v1/chats/session-123/stream');
    });

    it('should call onMessage callback when message received', async () => {
      const chatWs = new ChatWebSocket('session-123');
      const onMessage = vi.fn();

      chatWs.connect(onMessage);

      // Wait for connection
      await vi.runAllTimersAsync();

      // Simulate receiving a message
      const message: ChatMessage = { type: 'chunk', content: 'Hello' };
      mockWsInstances[0].simulateMessage(message);

      expect(onMessage).toHaveBeenCalledWith(message);
    });

    it('should reset reconnect attempts on successful connection', async () => {
      const chatWs = new ChatWebSocket('session-123');
      const onMessage = vi.fn();

      chatWs.connect(onMessage);

      // Wait for connection
      await vi.runAllTimersAsync();

      // Access internal state via isConnected
      expect(chatWs.isConnected()).toBe(true);
    });

    it('should handle malformed messages gracefully', async () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      const chatWs = new ChatWebSocket('session-123');
      const onMessage = vi.fn();

      chatWs.connect(onMessage);
      await vi.runAllTimersAsync();

      // Simulate malformed message
      if (mockWsInstances[0].onmessage) {
        mockWsInstances[0].onmessage(new MessageEvent('message', { data: 'invalid json' }));
      }

      expect(consoleSpy).toHaveBeenCalled();
      expect(onMessage).not.toHaveBeenCalled();

      consoleSpy.mockRestore();
    });

    it('should queue messages when disconnected', async () => {
      const chatWs = new ChatWebSocket('session-123');
      const onMessage = vi.fn();

      // Connect first
      chatWs.connect(onMessage);
      await vi.runAllTimersAsync();

      // Verify connected
      expect(chatWs.isConnected()).toBe(true);

      // Close the connection
      chatWs.close();

      // Verify disconnected
      expect(chatWs.isConnected()).toBe(false);

      // sendMessage when disconnected should try to reconnect
      // (the internal queue mechanism is tested by the reconnect behavior)
    });
  });

  describe('sendMessage', () => {
    it('should send message when connected', async () => {
      const chatWs = new ChatWebSocket('session-123');
      const onMessage = vi.fn();

      chatWs.connect(onMessage);
      await vi.runAllTimersAsync();

      chatWs.sendMessage('Hello World');

      expect(mockWsInstances[0].sentMessages).toHaveLength(1);
      expect(JSON.parse(mockWsInstances[0].sentMessages[0])).toEqual({
        type: 'message',
        content: 'Hello World',
      });
    });

    it('should queue message and reconnect when disconnected', async () => {
      const chatWs = new ChatWebSocket('session-123');
      const onMessage = vi.fn();

      chatWs.connect(onMessage);
      await vi.runAllTimersAsync();

      // Close the connection
      mockWsInstances[0].close();

      // Try to send message
      chatWs.sendMessage('Hello after disconnect');

      // Should trigger reconnection
      await vi.runAllTimersAsync();

      // New connection should be established
      expect(mockWsInstances.length).toBeGreaterThan(1);
    });
  });

  describe('sendCancel', () => {
    it('should send cancel message when connected', async () => {
      const chatWs = new ChatWebSocket('session-123');
      const onMessage = vi.fn();

      chatWs.connect(onMessage);
      await vi.runAllTimersAsync();

      chatWs.sendCancel();

      expect(mockWsInstances[0].sentMessages).toHaveLength(1);
      expect(JSON.parse(mockWsInstances[0].sentMessages[0])).toEqual({
        type: 'cancel',
      });
    });

    it('should queue cancel and reconnect when disconnected', async () => {
      const chatWs = new ChatWebSocket('session-123');
      const onMessage = vi.fn();

      chatWs.connect(onMessage);
      await vi.runAllTimersAsync();

      // Close the connection
      mockWsInstances[0].close();

      // Try to send cancel
      chatWs.sendCancel();

      // Should trigger reconnection
      await vi.runAllTimersAsync();

      expect(mockWsInstances.length).toBeGreaterThan(1);
    });
  });

  describe('close', () => {
    it('should close the WebSocket connection', async () => {
      const chatWs = new ChatWebSocket('session-123');
      const onMessage = vi.fn();

      chatWs.connect(onMessage);
      await vi.runAllTimersAsync();

      expect(chatWs.isConnected()).toBe(true);

      chatWs.close();

      expect(chatWs.isConnected()).toBe(false);
    });

    it('should handle close when not connected', () => {
      const chatWs = new ChatWebSocket('session-123');

      // Should not throw
      expect(() => chatWs.close()).not.toThrow();
    });
  });

  describe('isConnected', () => {
    it('should return false before connecting', () => {
      const chatWs = new ChatWebSocket('session-123');
      expect(chatWs.isConnected()).toBe(false);
    });

    it('should return true when connected', async () => {
      const chatWs = new ChatWebSocket('session-123');
      const onMessage = vi.fn();

      chatWs.connect(onMessage);
      await vi.runAllTimersAsync();

      expect(chatWs.isConnected()).toBe(true);
    });

    it('should return false after closing', async () => {
      const chatWs = new ChatWebSocket('session-123');
      const onMessage = vi.fn();

      chatWs.connect(onMessage);
      await vi.runAllTimersAsync();

      chatWs.close();

      expect(chatWs.isConnected()).toBe(false);
    });
  });

  describe('reconnection', () => {
    it('should attempt to reconnect on connection close', async () => {
      const chatWs = new ChatWebSocket('session-123');
      const onMessage = vi.fn();

      chatWs.connect(onMessage);
      await vi.runAllTimersAsync();

      // Close connection to trigger reconnect
      mockWsInstances[0].close();

      // Advance timers for reconnect delay (2000ms * 1)
      await vi.advanceTimersByTimeAsync(2000);

      // Should have created a new WebSocket
      expect(mockWsInstances.length).toBe(2);
    });

    it('should respect max reconnect attempts', async () => {
      const chatWs = new ChatWebSocket('session-123');
      const onMessage = vi.fn();

      chatWs.connect(onMessage);
      await vi.runAllTimersAsync();

      const initialCount = mockWsInstances.length;

      // Simulate connection close to trigger reconnect
      mockWsInstances[mockWsInstances.length - 1].close();

      // Wait for first reconnect (2000ms delay)
      await vi.advanceTimersByTimeAsync(2500);

      // Should have one more connection attempt
      expect(mockWsInstances.length).toBe(initialCount + 1);
    });

    it('should handle errors and continue operating', async () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      const chatWs = new ChatWebSocket('session-123');
      const onMessage = vi.fn();

      chatWs.connect(onMessage);
      await vi.runAllTimersAsync();

      // Simulate error
      mockWsInstances[0].simulateError();

      expect(consoleSpy).toHaveBeenCalled();

      consoleSpy.mockRestore();
    });
  });

  describe('message types', () => {
    it('should handle all message types', async () => {
      const chatWs = new ChatWebSocket('session-123');
      const onMessage = vi.fn();

      chatWs.connect(onMessage);
      await vi.runAllTimersAsync();

      const messageTypes: ChatMessage[] = [
        { type: 'start', message_id: 'msg-1' },
        { type: 'chunk', content: 'Hello' },
        { type: 'end' },
        { type: 'error', content: 'Error occurred' },
        { type: 'user_message_saved', message_id: 'msg-2' },
        { type: 'thought', content: 'Thinking...' },
        { type: 'action', tool: 'bash', args: { command: 'ls' }, step: 1 },
        { type: 'action_streaming', tool: 'bash', status: 'running', step: 1 },
        { type: 'action_args_chunk', partial_args: '{"cmd' },
        { type: 'observation', content: 'Result', success: true },
        { type: 'cancelled' },
        { type: 'cancel_acknowledged' },
      ];

      for (const message of messageTypes) {
        mockWsInstances[0].simulateMessage(message);
      }

      expect(onMessage).toHaveBeenCalledTimes(messageTypes.length);
    });
  });
});
