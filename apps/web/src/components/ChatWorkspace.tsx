import type { FormEvent, RefObject } from 'react'
import { Mic, MicOff, Send, Square, Volume2 } from 'lucide-react'
import type { Message } from '../types'

type ChatWorkspaceProps = {
  messages: Message[]
  messageListRef: RefObject<HTMLDivElement | null>
  feedbackStatus: Record<string, string>
  input: string
  isSending: boolean
  isListening: boolean
  autoSpeak: boolean
  continuousVoice: boolean
  voiceStatus: string
  isModuleEnabled: (moduleId: string) => boolean
  setInput: (value: string) => void
  setAutoSpeak: (value: boolean) => void
  setContinuousVoice: (value: boolean) => void
  setVoiceStatus: (value: string) => void
  sendMessage: (event: FormEvent<HTMLFormElement>) => void
  toggleVoiceInput: () => void
  sendFeedback: (message: Message, rating: 'positive' | 'negative') => void
}

export function ChatWorkspace({
  messages,
  messageListRef,
  feedbackStatus,
  input,
  isSending,
  isListening,
  autoSpeak,
  continuousVoice,
  voiceStatus,
  isModuleEnabled,
  setInput,
  setAutoSpeak,
  setContinuousVoice,
  setVoiceStatus,
  sendMessage,
  toggleVoiceInput,
  sendFeedback,
}: ChatWorkspaceProps) {
  const voiceEnabled = isModuleEnabled('voice')

  return (
    <section className="chat-panel" aria-label="Chat workspace">
      <div className="message-list" ref={messageListRef}>
        {messages.length === 0 ? (
          <div className="empty-state">
            <h2>Ask Jarvis to plan, code, research, or reason.</h2>
            <p>The frontend is connected to the new gateway service layout.</p>
          </div>
        ) : (
          messages.map((message) => (
            <article key={message.id} className={`message ${message.role}`}>
              <strong>{message.role === 'user' ? 'You' : 'Jarvis'}</strong>
              <p>
                {message.content}
                {message.isStreaming ? <span className="stream-cursor">|</span> : null}
              </p>
              {message.role === 'assistant' ? (
                <div className="feedback-actions">
                  <button
                    type="button"
                    disabled={message.isStreaming || Boolean(feedbackStatus[message.id])}
                    onClick={() => sendFeedback(message, 'positive')}
                  >
                    Good
                  </button>
                  <button
                    type="button"
                    disabled={message.isStreaming || Boolean(feedbackStatus[message.id])}
                    onClick={() => sendFeedback(message, 'negative')}
                  >
                    Fix
                  </button>
                  {feedbackStatus[message.id] ? <small>Saved</small> : null}
                </div>
              ) : null}
            </article>
          ))
        )}
      </div>

      <form className="composer" onSubmit={sendMessage}>
        <input
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder="Message ShivaAI Jarvis"
          aria-label="Message ShivaAI Jarvis"
        />
        <button
          className={`voice-button ${isListening ? 'listening' : ''}`}
          type="button"
          onClick={toggleVoiceInput}
          disabled={!voiceEnabled}
          aria-label={isListening ? 'Stop voice input' : 'Start voice input'}
          title={isListening ? 'Stop voice input' : 'Start voice input'}
        >
          {isListening ? <MicOff size={17} aria-hidden="true" /> : <Mic size={17} aria-hidden="true" />}
          <span>{isListening ? 'Stop' : 'Mic'}</span>
        </button>
        <button type="submit" disabled={isSending}>
          <Send size={17} aria-hidden="true" />
          <span>{isSending ? 'Sending' : 'Send'}</span>
        </button>
      </form>

      <div className="voice-controls" aria-label="Voice controls">
        <label>
          <input
            type="checkbox"
            checked={autoSpeak}
            disabled={!voiceEnabled}
            onChange={(event) => {
              setAutoSpeak(event.target.checked)
              if (!event.target.checked) window.speechSynthesis?.cancel()
            }}
          />
          <Volume2 size={14} aria-hidden="true" />
          Speak replies
        </label>
        <label>
          <input
            type="checkbox"
            checked={continuousVoice}
            disabled={!voiceEnabled}
            onChange={(event) => setContinuousVoice(event.target.checked)}
          />
          Continuous voice
        </label>
        <button
          type="button"
          onClick={() => {
            window.speechSynthesis?.cancel()
            setVoiceStatus('Speech stopped.')
          }}
        >
          <Square size={13} aria-hidden="true" />
          <span>Stop audio</span>
        </button>
      </div>
      {voiceStatus ? <p className="voice-status">{voiceStatus}</p> : null}
    </section>
  )
}
