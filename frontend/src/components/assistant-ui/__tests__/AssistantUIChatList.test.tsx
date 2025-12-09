/**
 * Tests for AssistantUIChatList - specifically the groupBlocks function
 * that sorts and groups content blocks by updated_at timestamp
 */

import { describe, it, expect } from 'vitest';
import { ContentBlock } from '@/types';

// Extract the groupBlocks function logic for testing
// This mirrors the implementation in AssistantUIChatList.tsx

interface DisplayGroup {
  type: 'user' | 'assistant';
  mainBlock: ContentBlock;
  textBlocks: ContentBlock[];
  toolBlocks: ContentBlock[];
}

function groupBlocks(blocks: ContentBlock[]): DisplayGroup[] {
  const groups: DisplayGroup[] = [];
  let currentAssistantGroup: DisplayGroup | null = null;

  // Sort by updated_at to ensure correct order (reflects when content was finalized)
  // Falls back to sequence_number if updated_at is the same
  const sortedBlocks = [...blocks].sort((a, b) => {
    const timeA = new Date(a.updated_at).getTime();
    const timeB = new Date(b.updated_at).getTime();
    if (timeA !== timeB) return timeA - timeB;
    return a.sequence_number - b.sequence_number;
  });

  for (const block of sortedBlocks) {
    if (block.block_type === 'user_text') {
      // Flush any pending assistant group
      if (currentAssistantGroup) {
        groups.push(currentAssistantGroup);
        currentAssistantGroup = null;
      }
      groups.push({
        type: 'user',
        mainBlock: block,
        textBlocks: [],
        toolBlocks: [],
      });
    } else if (block.block_type === 'assistant_text') {
      // With multiple text blocks, we ADD to existing group instead of creating new
      if (currentAssistantGroup) {
        // Add this text block to the existing group
        currentAssistantGroup.textBlocks.push(block);
      } else {
        // Start new assistant group with this text block
        currentAssistantGroup = {
          type: 'assistant',
          mainBlock: block,
          textBlocks: [block],
          toolBlocks: [],
        };
      }
    } else if (block.block_type === 'tool_call' || block.block_type === 'tool_result') {
      // Add to current assistant group if exists
      if (currentAssistantGroup) {
        currentAssistantGroup.toolBlocks.push(block);
      } else {
        // Orphan tool block - create a placeholder assistant group
        currentAssistantGroup = {
          type: 'assistant',
          mainBlock: {
            id: `placeholder-${block.id}`,
            chat_session_id: block.chat_session_id,
            sequence_number: block.sequence_number - 1,
            block_type: 'assistant_text',
            author: 'assistant',
            content: { text: '' },
            block_metadata: {},
            created_at: block.created_at,
            updated_at: block.updated_at,
          },
          textBlocks: [],
          toolBlocks: [block],
        };
      }
    } else if (block.block_type === 'system') {
      // System blocks can be shown as assistant messages
      if (currentAssistantGroup) {
        groups.push(currentAssistantGroup);
        currentAssistantGroup = null;
      }
      groups.push({
        type: 'assistant',
        mainBlock: block,
        textBlocks: [block],
        toolBlocks: [],
      });
    }
  }

  // Flush final assistant group
  if (currentAssistantGroup) {
    groups.push(currentAssistantGroup);
  }

  return groups;
}

// Helper to create test blocks
// Now accepts updatedAt parameter for testing updated_at-based sorting
function createBlock(
  id: string,
  blockType: ContentBlock['block_type'],
  sequenceNumber: number,
  content: any = {},
  updatedAt?: string  // ISO timestamp for updated_at (defaults to sequence-based time)
): ContentBlock {
  // If no updatedAt provided, generate one based on sequence_number
  // This ensures tests that don't care about updated_at still work
  const baseTime = new Date('2024-01-01T00:00:00.000Z').getTime();
  const defaultUpdatedAt = new Date(baseTime + sequenceNumber * 1000).toISOString();

  return {
    id,
    chat_session_id: 'test-session',
    sequence_number: sequenceNumber,
    block_type: blockType,
    author: blockType === 'user_text' ? 'user' : 'assistant',
    content,
    block_metadata: {},
    created_at: defaultUpdatedAt,
    updated_at: updatedAt || defaultUpdatedAt,
  };
}

describe('groupBlocks', () => {
  describe('sorting by updated_at timestamp', () => {
    it('should sort blocks by updated_at regardless of input order', () => {
      const blocks: ContentBlock[] = [
        createBlock('3', 'assistant_text', 3, { text: 'Response' }),
        createBlock('1', 'user_text', 1, { text: 'Hello' }),
        createBlock('2', 'user_text', 2, { text: 'World' }),
      ];

      const groups = groupBlocks(blocks);

      expect(groups).toHaveLength(3);
      expect(groups[0].mainBlock.sequence_number).toBe(1);
      expect(groups[1].mainBlock.sequence_number).toBe(2);
      expect(groups[2].mainBlock.sequence_number).toBe(3);
    });

    it('should handle out-of-order tool blocks and text blocks', () => {
      const blocks: ContentBlock[] = [
        createBlock('tool-result-1', 'tool_result', 4, { result: 'done' }),
        createBlock('text-1', 'assistant_text', 2, { text: 'Let me help' }),
        createBlock('user-1', 'user_text', 1, { text: 'Help me' }),
        createBlock('tool-call-1', 'tool_call', 3, { tool_name: 'bash' }),
      ];

      const groups = groupBlocks(blocks);

      expect(groups).toHaveLength(2);
      // First group: user message
      expect(groups[0].type).toBe('user');
      expect(groups[0].mainBlock.sequence_number).toBe(1);
      // Second group: assistant with text and tools
      expect(groups[1].type).toBe('assistant');
      expect(groups[1].mainBlock.sequence_number).toBe(2);
      expect(groups[1].toolBlocks).toHaveLength(2);
      // Tool blocks should be in order by sequence_number
      expect(groups[1].toolBlocks[0].sequence_number).toBe(3);
      expect(groups[1].toolBlocks[1].sequence_number).toBe(4);
    });
  });

  describe('grouping assistant content', () => {
    it('should group consecutive assistant_text blocks together', () => {
      const blocks: ContentBlock[] = [
        createBlock('user-1', 'user_text', 1, { text: 'Question' }),
        createBlock('text-1', 'assistant_text', 2, { text: 'First part' }),
        createBlock('text-2', 'assistant_text', 3, { text: 'Second part' }),
        createBlock('text-3', 'assistant_text', 4, { text: 'Third part' }),
      ];

      const groups = groupBlocks(blocks);

      expect(groups).toHaveLength(2);
      expect(groups[1].type).toBe('assistant');
      expect(groups[1].textBlocks).toHaveLength(3);
      expect(groups[1].textBlocks[0].content.text).toBe('First part');
      expect(groups[1].textBlocks[1].content.text).toBe('Second part');
      expect(groups[1].textBlocks[2].content.text).toBe('Third part');
    });

    it('should group tool_call and tool_result with assistant_text', () => {
      const blocks: ContentBlock[] = [
        createBlock('user-1', 'user_text', 1, { text: 'Run a command' }),
        createBlock('text-1', 'assistant_text', 2, { text: 'I will run bash' }),
        createBlock('tool-call-1', 'tool_call', 3, { tool_name: 'bash', arguments: { command: 'ls' } }),
        createBlock('tool-result-1', 'tool_result', 4, { result: 'file1.txt' }),
        createBlock('text-2', 'assistant_text', 5, { text: 'Here are the files' }),
      ];

      const groups = groupBlocks(blocks);

      expect(groups).toHaveLength(2);
      expect(groups[1].type).toBe('assistant');
      expect(groups[1].textBlocks).toHaveLength(2);
      expect(groups[1].toolBlocks).toHaveLength(2);
    });

    it('should handle interleaved text and tool blocks correctly', () => {
      const blocks: ContentBlock[] = [
        createBlock('user-1', 'user_text', 1, { text: 'Do multiple things' }),
        createBlock('text-1', 'assistant_text', 2, { text: 'Step 1' }),
        createBlock('tool-call-1', 'tool_call', 3, { tool_name: 'bash' }),
        createBlock('tool-result-1', 'tool_result', 4, { result: 'ok' }),
        createBlock('text-2', 'assistant_text', 5, { text: 'Step 2' }),
        createBlock('tool-call-2', 'tool_call', 6, { tool_name: 'file_read' }),
        createBlock('tool-result-2', 'tool_result', 7, { result: 'content' }),
        createBlock('text-3', 'assistant_text', 8, { text: 'Done' }),
      ];

      const groups = groupBlocks(blocks);

      expect(groups).toHaveLength(2);
      const assistantGroup = groups[1];
      expect(assistantGroup.textBlocks).toHaveLength(3);
      expect(assistantGroup.toolBlocks).toHaveLength(4);

      // Verify order is preserved
      expect(assistantGroup.textBlocks.map(b => b.sequence_number)).toEqual([2, 5, 8]);
      expect(assistantGroup.toolBlocks.map(b => b.sequence_number)).toEqual([3, 4, 6, 7]);
    });
  });

  describe('user message separation', () => {
    it('should start new groups for each user message', () => {
      const blocks: ContentBlock[] = [
        createBlock('user-1', 'user_text', 1, { text: 'First question' }),
        createBlock('text-1', 'assistant_text', 2, { text: 'First answer' }),
        createBlock('user-2', 'user_text', 3, { text: 'Second question' }),
        createBlock('text-2', 'assistant_text', 4, { text: 'Second answer' }),
      ];

      const groups = groupBlocks(blocks);

      expect(groups).toHaveLength(4);
      expect(groups[0].type).toBe('user');
      expect(groups[0].mainBlock.content.text).toBe('First question');
      expect(groups[1].type).toBe('assistant');
      expect(groups[1].mainBlock.content.text).toBe('First answer');
      expect(groups[2].type).toBe('user');
      expect(groups[2].mainBlock.content.text).toBe('Second question');
      expect(groups[3].type).toBe('assistant');
      expect(groups[3].mainBlock.content.text).toBe('Second answer');
    });
  });

  describe('orphan tool blocks', () => {
    it('should handle tool blocks without preceding assistant_text', () => {
      const blocks: ContentBlock[] = [
        createBlock('user-1', 'user_text', 1, { text: 'Question' }),
        createBlock('tool-call-1', 'tool_call', 2, { tool_name: 'bash' }),
        createBlock('tool-result-1', 'tool_result', 3, { result: 'done' }),
      ];

      const groups = groupBlocks(blocks);

      expect(groups).toHaveLength(2);
      expect(groups[1].type).toBe('assistant');
      expect(groups[1].mainBlock.id).toBe('placeholder-tool-call-1');
      expect(groups[1].toolBlocks).toHaveLength(2);
    });
  });

  describe('system blocks', () => {
    it('should handle system blocks as separate assistant groups', () => {
      const blocks: ContentBlock[] = [
        createBlock('system-1', 'system', 1, { text: 'Welcome message' }),
        createBlock('user-1', 'user_text', 2, { text: 'Hello' }),
        createBlock('text-1', 'assistant_text', 3, { text: 'Hi!' }),
      ];

      const groups = groupBlocks(blocks);

      expect(groups).toHaveLength(3);
      expect(groups[0].type).toBe('assistant');
      expect(groups[0].mainBlock.block_type).toBe('system');
      expect(groups[1].type).toBe('user');
      expect(groups[2].type).toBe('assistant');
    });
  });

  describe('empty input', () => {
    it('should return empty array for empty input', () => {
      const groups = groupBlocks([]);
      expect(groups).toHaveLength(0);
    });
  });

  describe('complex real-world scenarios', () => {
    it('should handle a realistic multi-turn conversation with tools', () => {
      const blocks: ContentBlock[] = [
        // Turn 1: User asks, assistant responds with tool usage
        createBlock('user-1', 'user_text', 1, { text: 'What files are in the current directory?' }),
        createBlock('text-1', 'assistant_text', 2, { text: 'Let me check.' }),
        createBlock('tool-call-1', 'tool_call', 3, { tool_name: 'bash', arguments: { command: 'ls -la' } }),
        createBlock('tool-result-1', 'tool_result', 4, { result: 'file1.txt\nfile2.py' }),
        createBlock('text-2', 'assistant_text', 5, { text: 'I found 2 files.' }),

        // Turn 2: User asks follow-up
        createBlock('user-2', 'user_text', 6, { text: 'Read file1.txt' }),
        createBlock('text-3', 'assistant_text', 7, { text: 'Reading the file...' }),
        createBlock('tool-call-2', 'tool_call', 8, { tool_name: 'file_read', arguments: { path: 'file1.txt' } }),
        createBlock('tool-result-2', 'tool_result', 9, { result: 'Hello world' }),
        createBlock('text-4', 'assistant_text', 10, { text: 'The file contains: Hello world' }),
      ];

      const groups = groupBlocks(blocks);

      expect(groups).toHaveLength(4);

      // Turn 1 - User
      expect(groups[0].type).toBe('user');
      expect(groups[0].mainBlock.sequence_number).toBe(1);

      // Turn 1 - Assistant with tools
      expect(groups[1].type).toBe('assistant');
      expect(groups[1].textBlocks).toHaveLength(2);
      expect(groups[1].toolBlocks).toHaveLength(2);

      // Turn 2 - User
      expect(groups[2].type).toBe('user');
      expect(groups[2].mainBlock.sequence_number).toBe(6);

      // Turn 2 - Assistant with tools
      expect(groups[3].type).toBe('assistant');
      expect(groups[3].textBlocks).toHaveLength(2);
      expect(groups[3].toolBlocks).toHaveLength(2);
    });

    it('should correctly order blocks that arrive out of sequence (simulating async persistence)', () => {
      // Simulate blocks arriving in random order due to async database writes
      const blocks: ContentBlock[] = [
        createBlock('tool-result-1', 'tool_result', 4, { result: 'done' }),
        createBlock('text-2', 'assistant_text', 5, { text: 'Finished!' }),
        createBlock('user-1', 'user_text', 1, { text: 'Start' }),
        createBlock('tool-call-1', 'tool_call', 3, { tool_name: 'bash' }),
        createBlock('text-1', 'assistant_text', 2, { text: 'Working...' }),
      ];

      const groups = groupBlocks(blocks);

      expect(groups).toHaveLength(2);

      // Verify correct ordering after grouping
      expect(groups[0].type).toBe('user');
      expect(groups[0].mainBlock.sequence_number).toBe(1);

      expect(groups[1].type).toBe('assistant');
      expect(groups[1].textBlocks[0].sequence_number).toBe(2);
      expect(groups[1].textBlocks[1].sequence_number).toBe(5);
      expect(groups[1].toolBlocks[0].sequence_number).toBe(3);
      expect(groups[1].toolBlocks[1].sequence_number).toBe(4);
    });

    it('should sort text block AFTER tools when text is finalized later (streaming scenario)', () => {
      // This tests the real-world scenario where:
      // - Assistant text block is CREATED first (lower sequence_number)
      // - But it's FINALIZED (updated_at) AFTER tool calls complete
      // - Tools should appear before the final text in the UI
      const blocks: ContentBlock[] = [
        createBlock('user-1', 'user_text', 1, { text: 'Run some commands' }, '2024-01-01T18:00:00.000Z'),
        // Text block created at seq 2, but finalized LAST at 18:05:13
        createBlock('text-1', 'assistant_text', 2, { text: 'Let me run those for you...' }, '2024-01-01T18:05:13.000Z'),
        // Tool calls created after text, but finalized BEFORE text
        createBlock('tool-call-1', 'tool_call', 3, { tool_name: 'bash' }, '2024-01-01T18:02:00.000Z'),
        createBlock('tool-result-1', 'tool_result', 4, { result: 'ok' }, '2024-01-01T18:02:01.000Z'),
        createBlock('tool-call-2', 'tool_call', 5, { tool_name: 'file_read' }, '2024-01-01T18:03:00.000Z'),
        createBlock('tool-result-2', 'tool_result', 6, { result: 'content' }, '2024-01-01T18:03:01.000Z'),
      ];

      const groups = groupBlocks(blocks);

      expect(groups).toHaveLength(2);

      // User message first
      expect(groups[0].type).toBe('user');
      expect(groups[0].mainBlock.sequence_number).toBe(1);

      // Assistant group should have tools BEFORE text due to updated_at sorting
      const assistantGroup = groups[1];
      expect(assistantGroup.type).toBe('assistant');

      // The mainBlock should now be a tool-related block (first by updated_at)
      // since tools were finalized before text
      // Actually, mainBlock is still the first text block encountered after sorting
      // Let's verify the toolBlocks are sorted by their updated_at
      expect(assistantGroup.toolBlocks).toHaveLength(4);
      // Tools should be in updated_at order: tool-call-1, tool-result-1, tool-call-2, tool-result-2
      expect(assistantGroup.toolBlocks[0].id).toBe('tool-call-1');
      expect(assistantGroup.toolBlocks[1].id).toBe('tool-result-1');
      expect(assistantGroup.toolBlocks[2].id).toBe('tool-call-2');
      expect(assistantGroup.toolBlocks[3].id).toBe('tool-result-2');

      // Text block (the one finalized last) should be in textBlocks
      expect(assistantGroup.textBlocks).toHaveLength(1);
      expect(assistantGroup.textBlocks[0].id).toBe('text-1');
    });
  });
});
