import React, { useState, useRef, useEffect } from 'react';
import styled from 'styled-components';
import { useChat } from '../context/ChatContext';
import sendIconUrl from '../assets/images/send_icon.svg';

interface InputContainerProps {
  'data-testid'?: string;
}

const InputContainer = styled.div<InputContainerProps>`
  width: 100%;
  max-width: 680px;
  min-height: 50px;
  height: 90px;
  position: relative;
  border: 1px solid #C0CDD8;
  border-radius: 12px;
  padding: 10px 12px;
  background-color: white;
  box-shadow: 0px 1px 3px -1px rgba(0, 0, 0, 0.05), 0px 2px 0px 0px rgba(0, 0, 0, 0.05);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 8px;
  margin-top: 10px;
`;

const TextArea = styled.textarea`
  width: 100%;
  border: none;
  outline: none;
  font-size: 15px;
  padding: 6px 0;
  color: #11171C;
  white-space: pre-wrap;
  word-break: break-word;
  overflow-wrap: break-word;
  min-height: 40px;
  max-height: 90px;
  overflow-y: auto;
  display: block;
  background-color: transparent;
  font-family: inherit;
  margin-bottom: 30px;
  resize: none;
  box-sizing: border-box;
`;

const ButtonsRight = styled.div`
  display: flex;
  align-items: center;
  position: absolute;
  bottom: 12px;
  right: 12px;
  z-index: 2;
`;

const InputButton = styled.button`
  width: 24px;
  height: 24px;
  border: none;
  background: transparent;
  display: flex;
  justify-content: center;
  align-items: center;
  cursor: pointer;
  margin: 0 4px;
  
  &:hover {
    background-color: #F0F0F0;
    border-radius: 4px;
  }
`;

const SendButton = styled(InputButton)`
  background-image: url(${sendIconUrl});
  background-size: 16px;
  background-repeat: no-repeat;
  background-position: center;
  &:hover {
    background-color: rgba(34, 114, 180, 0.08);
    color: #0E538B;
  }
`;

const ToggleContainer = styled.div`
  display: flex;
  align-items: center;
  position: absolute;
  bottom: 12px;
  left: 12px;
  z-index: 2;
  gap: 8px;
`;

const ToggleLabel = styled.span`
  font-size: 12px;
  color: #5F7281;
`;

const ToggleSwitch = styled.label`
  position: relative;
  display: inline-block;
  width: 36px;
  height: 20px;
`;

const ToggleSlider = styled.span`
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #C0CDD8;
  transition: .4s;
  border-radius: 20px;

  &:before {
    position: absolute;
    content: "";
    height: 16px;
    width: 16px;
    left: 2px;
    bottom: 2px;
    background-color: white;
    transition: .4s;
    border-radius: 50%;
  }
`;

const ToggleInput = styled.input`
  opacity: 0;
  width: 0;
  height: 0;

  &:checked + ${ToggleSlider} {
    background-color: #2272B4;
  }

  &:checked + ${ToggleSlider}:before {
    transform: translateX(16px);
  }
`;

interface ChatInputProps {
  fixed?: boolean;
  setIsRegenerating: (value: boolean) => void;
  includeHistory: boolean;
  setIncludeHistory: (value: boolean) => void;
}

const ChatInput: React.FC<ChatInputProps> = ({ 
  fixed = false, 
  setIsRegenerating,
  includeHistory,
  setIncludeHistory 
}) => {
  const [inputValue, setInputValue] = useState('');
  const { sendMessage, loading } = useChat();
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      const newHeight = Math.max(50, Math.min(textareaRef.current.scrollHeight, 100));
      textareaRef.current.style.height = `${newHeight}px`;
    }
  }, [inputValue]);
  
  const handleSubmit = async () => {
    if (inputValue.trim() && !loading) {
      setIsRegenerating(false);
      setInputValue('');
      await sendMessage(inputValue, includeHistory);
      if (textareaRef.current) {
        textareaRef.current.style.height = '50px';
      }
    }
  };
  
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };
  
  return (
    <InputContainer data-testid="chat-input-container">
      <TextArea
        ref={textareaRef}
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        placeholder="Ask anything"
        onKeyDown={handleKeyDown}
        data-testid="chat-input-textarea"
      />
      <ToggleContainer>
        <ToggleLabel>Include History</ToggleLabel>
        <ToggleSwitch>
          <ToggleInput
            type="checkbox"
            checked={includeHistory}
            onChange={(e) => setIncludeHistory(e.target.checked)}
          />
          <ToggleSlider />
        </ToggleSwitch>
      </ToggleContainer>
      <ButtonsRight data-testid="buttons-right">
        <SendButton onClick={handleSubmit} disabled={loading} data-testid="send-button" />
      </ButtonsRight>
    </InputContainer>
  );
};

export default ChatInput; 