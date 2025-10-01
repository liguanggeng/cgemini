import React from 'react';

function ChatPanel({ chatHistory }) {
  return (
    <div className="chat-panel">
      <h2>Chat</h2>
      <div className="message-list">
        {chatHistory.map((item, index) => (
          <div key={index} className={`message ${item.sender}`}>
            <strong>{item.sender}: </strong>{item.message}
          </div>
        ))}
      </div>
      <div className="chat-input">
        <input type="text" placeholder="Type your message..." />
        <button>Send</button>
      </div>
    </div>
  );
}

export default ChatPanel;