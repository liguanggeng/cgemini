import React from 'react';
import './LogCard.css';

function LogCard({ logEntry }) {
  const { type, agent, source, content } = logEntry;

  const renderContent = () => {
    if (typeof content === 'object' && content !== null) {
      return <pre>{JSON.stringify(content, null, 2)}</pre>;
    }
    return content;
  };

  return (
    <div className={`log-card ${type}`}>
      <div className="log-card-header">
        <strong>{type.toUpperCase()}</strong>
        <span>{agent || source}</span>
      </div>
      <div className="log-card-content">
        {renderContent()}
      </div>
    </div>
  );
}

export default LogCard;
