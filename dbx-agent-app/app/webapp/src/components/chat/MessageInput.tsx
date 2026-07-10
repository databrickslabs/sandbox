import { useState, KeyboardEvent } from 'react'
import Button from '../common/Button'
import './MessageInput.css'

interface MessageInputProps {
  onSend: (content: string) => void
  disabled?: boolean
}

export default function MessageInput({ onSend, disabled = false }: MessageInputProps) {
  const [input, setInput] = useState('')

  const handleSend = () => {
    if (input.trim() && !disabled) {
      onSend(input.trim())
      setInput('')
    }
  }

  const handleKeyPress = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="message-input">
      <textarea
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyPress={handleKeyPress}
        placeholder="Ask about tools and agents..."
        disabled={disabled}
        rows={3}
      />
      <Button onClick={handleSend} disabled={disabled || !input.trim()}>
        {disabled ? 'Sending...' : 'Send'}
      </Button>
    </div>
  )
}
