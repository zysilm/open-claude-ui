import { useState, useRef, useEffect, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import {Message, StreamEvent} from "@/types";

// Industry standard: 30ms interval = 33 updates/second (ChatGPT-like speed)
const FLUSH_INTERVAL_MS = 30;

interface UseOptimizedStreamingProps {
  sessionId: string;
  initialMessages?: Message[];
}

export const useOptimizedStreaming = ({ sessionId, initialMessages = [] }: UseOptimizedStreamingProps) => {
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [streamEvents, setStreamEvents] = useState<StreamEvent[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const queryClient = useQueryClient();

  // Buffers for batching (no re-renders when updated)
  const chunkBufferRef = useRef<string>('');
  const eventBufferRef = useRef<StreamEvent[]>([]);

  // Track the currently streaming message ID
  const streamingMessageIdRef = useRef<string | null>(null);

  // Optimized: 30ms interval for ChatGPT-like streaming speed
  useEffect(() => {
    if (!isStreaming) return;

    console.log('[FLUSH INTERVAL] Starting with message ID:', streamingMessageIdRef.current);

    const flushInterval = setInterval(() => {
      const bufferedContent = chunkBufferRef.current;
      const bufferedEvents = eventBufferRef.current;

      if (!bufferedContent && bufferedEvents.length === 0) {
        return; // Nothing to flush
      }

      // Flush messages
      if (bufferedContent) {
        setMessages(prev => {
          const updated = [...prev];

          // IMPORTANT: Always read the current ref value, not from closure
          const currentMessageId = streamingMessageIdRef.current;

          // Find the message by tracked ID or fallback to last assistant message
          let targetIndex = -1;
          if (currentMessageId) {
            targetIndex = updated.findIndex(m => m.id === currentMessageId);
            if (targetIndex === -1) {
              console.log('[FLUSH] Could not find message with ID:', currentMessageId);
              console.log('[FLUSH] Available message IDs:', updated.map(m => m.id));
            } else {
              console.log('[FLUSH] Found message with ID:', currentMessageId, 'at index:', targetIndex);
            }
          }

          // Fallback to last assistant message if ID not found
          if (targetIndex === -1) {
            for (let i = updated.length - 1; i >= 0; i--) {
              if (updated[i].role === 'assistant') {
                targetIndex = i;
                console.log('[FLUSH] Using fallback assistant message at index:', targetIndex);
                break;
              }
            }
          }

          if (targetIndex !== -1) {
            // Update the target message with buffered content
            updated[targetIndex] = {
              ...updated[targetIndex],
              content: updated[targetIndex].content + bufferedContent
            };
            console.log('[FLUSH] Applied', bufferedContent.length, 'chars to message at index:', targetIndex);
          } else {
            console.warn('[FLUSH] No target message found for buffered content!');
          }

          return updated;
        });
      }

      // Flush stream events
      if (bufferedEvents.length > 0) {
        setStreamEvents(prev => [...prev, ...bufferedEvents]);
      }

      // Clear buffers after flush
      chunkBufferRef.current = '';
      eventBufferRef.current = [];
    }, FLUSH_INTERVAL_MS);

    return () => clearInterval(flushInterval);
  }, [isStreaming]);

  // WebSocket message handler
  const handleWebSocketMessage = useCallback((event: MessageEvent) => {
    const data = JSON.parse(event.data);

    switch (data.type) {
      case 'start':
        setIsStreaming(true);
        setError(null);
        // Clear buffers for new streaming session
        chunkBufferRef.current = '';
        eventBufferRef.current = [];
        setStreamEvents([]);

        // Track the message ID for this stream
        const messageId = data.message_id || 'temp-' + Date.now();
        streamingMessageIdRef.current = messageId;

        // Add new assistant message
        setMessages(prev => [
          ...prev,
          {
            id: messageId,
            chat_session_id: sessionId,
            role: 'assistant',
            content: '',
            created_at: new Date().toISOString(),
            message_metadata: {}
          }
        ]);
        break;

      case 'chunk':
        // Just accumulate in buffer - interval will flush
        const chunkMessageId = streamingMessageIdRef.current;
        console.log('[CHUNK] Received chunk. Current streamingMessageIdRef:', chunkMessageId, 'Content length:', data.content?.length);

        if (!chunkMessageId) {
          console.warn('[CHUNK] No message ID set! This chunk may be lost.');
        }

        chunkBufferRef.current += data.content || '';
        console.log('[CHUNK] Buffer now has', chunkBufferRef.current.length, 'chars total');

        eventBufferRef.current.push({
          type: 'chunk',
          content: data.content,
        });
        break;

      case 'action_streaming':
        eventBufferRef.current.push({
          type: 'action_streaming',
          content: `Preparing ${data.tool}...`,
          tool: data.tool,
          status: data.status,
          step: data.step,
        });
        break;

      case 'action_args_chunk':
        eventBufferRef.current.push({
          type: 'action_args_chunk',
          content: data.partial_args || '',
          tool: data.tool,
          partial_args: data.partial_args,
          step: data.step,
        });
        break;

      case 'action':
        // Remove all action_args_chunk events for this tool from existing state
        // This prevents retroactive filtering during render
        setStreamEvents(prev =>
          prev.filter(e => !(e.type === 'action_args_chunk' && e.tool === data.tool))
        );

        eventBufferRef.current.push({
          type: 'action',
          content: `Using tool: ${data.tool}`,
          tool: data.tool,
          args: data.args,
          step: data.step,
        });
        break;

      case 'observation':
        eventBufferRef.current.push({
          type: 'observation',
          content: data.content,
          success: data.success,
          metadata: data.metadata,
          step: data.step,
        });
        break;

      case 'end':
        // Final flush of any remaining buffered content
        const finalContent = chunkBufferRef.current;
        const finalEvents = eventBufferRef.current;

        if (finalContent) {
          setMessages(prev => {
            const updated = [...prev];

            // Find the message by tracked ID or fallback to last assistant message
            let targetIndex = -1;
            if (streamingMessageIdRef.current) {
              targetIndex = updated.findIndex(m => m.id === streamingMessageIdRef.current);
            }

            // Fallback to last assistant message if ID not found
            if (targetIndex === -1) {
              for (let i = updated.length - 1; i >= 0; i--) {
                if (updated[i].role === 'assistant') {
                  targetIndex = i;
                  break;
                }
              }
            }

            if (targetIndex !== -1) {
              updated[targetIndex] = {
                ...updated[targetIndex],
                content: updated[targetIndex].content + finalContent
              };
            }

            return updated;
          });
        }

        if (finalEvents.length > 0) {
          setStreamEvents(prev => [...prev, ...finalEvents]);
        }

        // Clear buffers and message ID tracking
        chunkBufferRef.current = '';
        eventBufferRef.current = [];
        streamingMessageIdRef.current = null;

        // Stop streaming
        setIsStreaming(false);
        setStreamEvents([]);

        // Refetch messages from API to get persisted version
        queryClient.invalidateQueries({ queryKey: ['messages', sessionId] });
        break;

      case 'cancelled':
        // Flush remaining content
        if (chunkBufferRef.current) {
          setMessages(prev => {
            const updated = [...prev];
            const lastMessage = updated[updated.length - 1];

            if (lastMessage && lastMessage.role === 'assistant') {
              updated[updated.length - 1] = {
                ...lastMessage,
                content: lastMessage.content + chunkBufferRef.current
              };
            }

            return updated;
          });
        }

        chunkBufferRef.current = '';
        eventBufferRef.current = [];
        setIsStreaming(false);
        break;

      case 'error':
        console.error('WebSocket error:', data.content || data.message);
        const errorMessage = data.content || data.message || 'An error occurred';

        // Only set error if it's not about missing task (expected when no active stream)
        if (!errorMessage.includes('No active task found')) {
          setError(errorMessage);
        }

        setIsStreaming(false);
        // Flush any pending content
        if (chunkBufferRef.current) {
          setMessages(prev => {
            const updated = [...prev];
            const lastMessage = updated[updated.length - 1];

            if (lastMessage && lastMessage.role === 'assistant') {
              updated[updated.length - 1] = {
                ...lastMessage,
                content: lastMessage.content + chunkBufferRef.current
              };
            }

            return updated;
          });
        }
        chunkBufferRef.current = '';
        eventBufferRef.current = [];
        break;

      case 'title_updated':
        console.log('[TITLE] Session title updated:', data.title);
        // Invalidate chat sessions query to refresh sidebar with new title
        queryClient.invalidateQueries({ queryKey: ['chatSessions'] });
        // Invalidate current session query to refresh header title
        queryClient.invalidateQueries({ queryKey: ['chatSession', sessionId] });
        break;

      case 'heartbeat':
        // Heartbeat message to keep connection alive - silently ignore
        break;

      case 'resuming_stream':
        // Indicates we're reconnecting to an existing stream
        console.log('[STREAM RESUME] Reconnecting to existing stream:', data.message_id);
        setError(null);

        // Clear buffers for resumed streaming session
        chunkBufferRef.current = '';
        eventBufferRef.current = [];
        setStreamEvents([]);

        // Track the message ID for this resumed stream
        const resumedMessageId = data.message_id || 'temp-resumed-' + Date.now();
        streamingMessageIdRef.current = resumedMessageId;
        console.log('[STREAM RESUME] Set streamingMessageIdRef to:', resumedMessageId);

        // Ensure we have an assistant message to append chunks to
        setMessages(prev => {
          // Check if we already have an assistant message (last message might be it)
          const lastMessage = prev[prev.length - 1];
          const hasAssistantMessage = lastMessage && lastMessage.role === 'assistant';

          // Also check by message ID if provided
          const existingMessage = data.message_id ?
            prev.find(m => m.id === data.message_id) : null;

          if (existingMessage) {
            // Message already exists, no need to add
            console.log('[STREAM RESUME] Found existing message with ID:', data.message_id);
            // Ensure the ref matches
            streamingMessageIdRef.current = existingMessage.id;
            return prev;
          } else if (hasAssistantMessage && !lastMessage.content) {
            // Last message is an empty assistant message, likely from before refresh
            console.log('[STREAM RESUME] Using existing empty assistant message, updating its ID from', lastMessage.id, 'to', resumedMessageId);
            // Update the existing message's ID to match the resumed stream's ID
            const updatedMessages = [...prev];
            const lastIndex = updatedMessages.length - 1;
            updatedMessages[lastIndex] = {
              ...updatedMessages[lastIndex],
              id: resumedMessageId
            };
            return updatedMessages;
          } else {
            // Create a new assistant message for the resumed stream
            console.log('[STREAM RESUME] Creating new assistant message with ID:', resumedMessageId);
            return [
              ...prev,
              {
                id: resumedMessageId,
                chat_session_id: sessionId,
                role: 'assistant',
                content: '', // Will be filled with buffered chunks
                created_at: new Date().toISOString(),
                message_metadata: {}
              }
            ];
          }
        });

        // Set isStreaming to trigger the flush interval
        console.log('[STREAM RESUME] Setting isStreaming to true');
        setIsStreaming(true);
        break;

      default:
        console.warn('Unknown WebSocket message type:', data.type);
    }
  }, [sessionId, queryClient]);

  // WebSocket connection setup
  useEffect(() => {
    if (!sessionId) return;

    const ws = new WebSocket(`ws://127.0.0.1:8000/api/v1/chats/${sessionId}/stream`);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('[useOptimizedStreaming] WebSocket connected');
    };

    ws.onmessage = handleWebSocketMessage;

    ws.onerror = (error) => {
      console.error('[useOptimizedStreaming] WebSocket error:', error);
      setIsStreaming(false);
      setError('Connection error occurred');
    };

    ws.onclose = () => {
      console.log('[useOptimizedStreaming] WebSocket closed');
      setIsStreaming(false);
    };

    // Cleanup on unmount
    return () => {
      console.log('[useOptimizedStreaming] Cleaning up WebSocket');
      ws.close();
    };
  }, [sessionId, handleWebSocketMessage]);

  // Update messages when external data changes
  useEffect(() => {
    if (initialMessages && initialMessages.length > 0) {
      setMessages(initialMessages);
    }
  }, [initialMessages]);

  // Send message via WebSocket
  const sendMessage = useCallback((content: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.error('[useOptimizedStreaming] WebSocket not ready');
      return false;
    }

    if (!content.trim()) {
      return false;
    }

    // Add user message to local state immediately
    const userMessage: Message = {
      id: 'temp-user-' + Date.now(),
      chat_session_id: sessionId,
      role: 'user',
      content: content,
      created_at: new Date().toISOString(),
      message_metadata: {}
    };

    setMessages(prev => [...prev, userMessage]);

    // Send via WebSocket
    wsRef.current.send(JSON.stringify({
      type: 'message',
      content,
    }));

    return true;
  }, []);

  // Cancel streaming
  const cancelStream = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'cancel' }));
    }
  }, []);

  // Clear error
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    messages,
    streamEvents,
    isStreaming,
    error,
    sendMessage,
    cancelStream,
    clearError,
    isWebSocketReady: wsRef.current?.readyState === WebSocket.OPEN,
  };
};
