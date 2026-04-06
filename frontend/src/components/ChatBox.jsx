import { useState, useRef, useEffect } from 'react';
import { apiClient } from '../api/client';
import './ChatBox.css';

export default function ChatBox({ menuId, restaurantName }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const messagesEndRef = useRef(null);

  // Auto-scroll to bottom mapping
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const fetchHistory = async (sid) => {
    try {
      const data = await apiClient.get(`/chat/sessions/${sid}/history`);
      if (data && data.messages) {
        setMessages(data.messages);
      }
    } catch (err) {
      console.error("Could not fetch history:", err);
    }
  };

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setIsLoading(true);

    try {
      // Use a consistent static user ID for demonstration, 
      // in reality this would come from an auth context.
      const payload = {
        message: userMessage,
        menu_id: menuId,
        user_id: 'web-user-demo', 
      };
      
      if (sessionId) {
        payload.session_id = sessionId;
      }

      const response = await apiClient.post('/chat', payload);
      
      if (response.session_id && !sessionId) {
        setSessionId(response.session_id);
      }

      setMessages(prev => [...prev, { role: 'model', content: response.response }]);
    } catch (error) {
      setMessages(prev => [...prev, { role: 'model', content: '⚠️ Error: Could not connect to AI Agent. (' + error.message + ')' }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="chat-box panel">
      <div className="chat-header">
        <h3>Chat Context: {restaurantName || 'Menu'}</h3>
        {sessionId && <span className="session-badge">Session Active</span>}
      </div>

      <div className="chat-messages">
        {messages.length === 0 ? (
          <div className="chat-empty">
            <p>Ask anything about the menu! e.g., "أغلى طبق في المنيو؟"</p>
          </div>
        ) : (
          messages.map((msg, idx) => (
            <div key={idx} className={`message ${msg.role}`}>
              <div className="bubble">
                {msg.content}
              </div>
            </div>
          ))
        )}
        {isLoading && (
          <div className="message model">
            <div className="bubble typing">
              Agent is thinking <span className="dots">...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <form className="chat-input-area" onSubmit={handleSend}>
        <input
          type="text"
          placeholder="Ask about the menu..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={isLoading}
        />
        <button type="submit" className="btn-primary" disabled={!input.trim() || isLoading}>
          Send
        </button>
      </form>
    </div>
  );
}
