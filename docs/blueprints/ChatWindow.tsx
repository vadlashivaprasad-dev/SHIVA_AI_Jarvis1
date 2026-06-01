// apps/web/src/components/chat/ChatWindow.tsx
/**
 * ChatWindow Component
 * Main chat interface for ShivaAI Jarvis
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useChat } from '@/hooks/useChat';
import { useChatStore } from '@/stores/chatStore';
import { MessageList } from './MessageList';
import { MessageInput } from './MessageInput';
import { StreamingMessage } from './StreamingMessage';
import { ArtifactViewer } from './ArtifactViewer';
import { Spinner } from '@/components/common/Spinner';
import type { Message, Conversation } from '@/types';
import styles from './ChatWindow.module.css';


interface ChatWindowProps {
  conversationId?: string;
  onConversationChange?: (id: string) => void;
}


export const ChatWindow: React.FC<ChatWindowProps> = ({
  conversationId,
  onConversationChange,
}) => {
  // =========================================================================
  // STATE
  // =========================================================================

  const { 
    messages, 
    isLoading, 
    conversation,
    sendMessage, 
    createConversation,
    loadConversation,
  } = useChat();

  const { 
    addMessage, 
    setCurrentConversation,
    currentConversation,
  } = useChatStore();

  const [streaming, setStreaming] = useState(false);
  const [streamingMessage, setStreamingMessage] = useState('');
  const [selectedArtifact, setSelectedArtifact] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textInputRef = useRef<HTMLTextAreaElement>(null);


  // =========================================================================
  // EFFECTS
  // =========================================================================

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingMessage]);

  // Load conversation if ID provided
  useEffect(() => {
    if (conversationId) {
      loadConversation(conversationId);
    } else if (!currentConversation) {
      // Create new conversation if none exists
      handleCreateConversation();
    }
  }, [conversationId]);

  // Focus input on load
  useEffect(() => {
    textInputRef.current?.focus();
  }, []);


  // =========================================================================
  // HANDLERS
  // =========================================================================

  const handleCreateConversation = async () => {
    try {
      const newConversation = await createConversation({
        title: `Chat ${new Date().toLocaleString()}`,
      });
      
      if (newConversation) {
        setCurrentConversation(newConversation);
        onConversationChange?.(newConversation.id);
      }
    } catch (error) {
      console.error('Failed to create conversation:', error);
    }
  };

  const handleSendMessage = useCallback(async (content: string) => {
    if (!currentConversation?.id) {
      await handleCreateConversation();
      return;
    }

    try {
      setStreaming(true);
      setStreamingMessage('');

      // Send message and stream response
      const response = await sendMessage({
        conversation_id: currentConversation.id,
        content,
      });

      // Add user message to store
      addMessage({
        id: `msg-${Date.now()}`,
        conversation_id: currentConversation.id,
        role: 'user',
        content,
        created_at: new Date().toISOString(),
      });

      // Handle streaming (SSE)
      if (response && 'stream' in response) {
        for await (const chunk of response.stream) {
          setStreamingMessage((prev) => prev + chunk.token);
        }
      }

      // Add AI message to store
      addMessage({
        id: response.id,
        conversation_id: currentConversation.id,
        role: 'assistant',
        content: streamingMessage,
        created_at: new Date().toISOString(),
        metadata: response.metadata,
      });

      // Clear input
      if (textInputRef.current) {
        textInputRef.current.value = '';
      }
    } catch (error) {
      console.error('Failed to send message:', error);
    } finally {
      setStreaming(false);
      setStreamingMessage('');
    }
  }, [currentConversation, sendMessage, addMessage, streamingMessage]);

  const handleRegenerateMessage = async (messageId: string) => {
    // Find the message and regenerate
    const message = messages.find((m) => m.id === messageId);
    if (message && message.role === 'assistant') {
      // Find the previous user message
      const messageIndex = messages.indexOf(message);
      const previousMessage = messages[messageIndex - 1];
      
      if (previousMessage && previousMessage.role === 'user') {
        await handleSendMessage(previousMessage.content);
      }
    }
  };

  const handleArtifactView = (artifactId: string) => {
    setSelectedArtifact(artifactId);
  };


  // =========================================================================
  // RENDER
  // =========================================================================

  return (
    <div className={styles.chatWindow}>
      {/* Header */}
      <div className={styles.header}>
        <h1 className={styles.title}>
          {currentConversation?.title || 'New Conversation'}
        </h1>
        <button 
          className={styles.newButton}
          onClick={handleCreateConversation}
          title="Start a new conversation"
        >
          + New Chat
        </button>
      </div>

      {/* Messages Container */}
      <div className={styles.messagesContainer}>
        {messages.length === 0 && !streaming && (
          <div className={styles.emptyState}>
            <div className={styles.logo}>🧠</div>
            <h2>ShivaAI Jarvis</h2>
            <p>Cognitive Operating System Kernel</p>
            <div className={styles.exampleQueries}>
              <button onClick={() => handleSendMessage('Analyze the market for tech stocks')}>
                📈 Trading Analysis
              </button>
              <button onClick={() => handleSendMessage('Generate a Python function')}>
                💻 Code Generation
              </button>
              <button onClick={() => handleSendMessage('Create a learning path')}>
                📚 Learning Path
              </button>
              <button onClick={() => handleSendMessage('Forecast next quarter sales')}>
                🔮 Predictions
              </button>
            </div>
          </div>
        )}

        {/* Message List */}
        {messages.length > 0 && (
          <MessageList 
            messages={messages}
            onRegenerateMessage={handleRegenerateMessage}
            onViewArtifact={handleArtifactView}
          />
        )}

        {/* Streaming Message */}
        {streaming && streamingMessage && (
          <StreamingMessage content={streamingMessage} />
        )}

        {isLoading && !streamingMessage && (
          <div className={styles.loadingContainer}>
            <Spinner />
            <p>Thinking...</p>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Artifact Viewer Modal */}
      {selectedArtifact && (
        <ArtifactViewer 
          artifactId={selectedArtifact}
          onClose={() => setSelectedArtifact(null)}
        />
      )}

      {/* Input Area */}
      <div className={styles.inputArea}>
        <MessageInput 
          ref={textInputRef}
          onSendMessage={handleSendMessage}
          disabled={streaming || isLoading}
          placeholder="Message ShivaAI Jarvis... (Shift+Enter for new line)"
        />
      </div>
    </div>
  );
};


// ============================================================================
// STYLES (ChatWindow.module.css)
// ============================================================================

/*
.chatWindow {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--bg-primary);
  color: var(--text-primary);
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border-bottom: 1px solid var(--border-tertiary);
  background: var(--bg-secondary);
}

.title {
  font-size: 1.25rem;
  font-weight: 500;
  margin: 0;
}

.newButton {
  padding: 0.5rem 1rem;
  background: var(--text-primary);
  color: var(--bg-primary);
  border: none;
  border-radius: 0.375rem;
  cursor: pointer;
  font-weight: 500;
  font-size: 0.875rem;
  transition: opacity 0.15s;
}

.newButton:hover {
  opacity: 0.9;
}

.messagesContainer {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.emptyState {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 2rem;
}

.logo {
  font-size: 4rem;
}

.emptyState h2 {
  font-size: 2rem;
  margin: 0;
}

.emptyState p {
  color: var(--text-secondary);
  margin: 0;
}

.exampleQueries {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1rem;
  width: 100%;
  max-width: 600px;
}

.exampleQueries button {
  padding: 1rem;
  background: var(--bg-secondary);
  border: 1px solid var(--border-secondary);
  border-radius: 0.5rem;
  cursor: pointer;
  font-size: 0.875rem;
  color: var(--text-primary);
  transition: all 0.15s;
}

.exampleQueries button:hover {
  background: var(--bg-tertiary);
  border-color: var(--border-primary);
}

.loadingContainer {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  padding: 2rem;
  color: var(--text-secondary);
}

.inputArea {
  padding: 1rem;
  border-top: 1px solid var(--border-tertiary);
  background: var(--bg-secondary);
}
*/
