import React from 'react';
import LogCard from './LogCard';

function OrchestratorLog({ orchestratorLog }) {
  return (
    <div className="orchestrator-log">
      <h2>Orchestrator Log</h2>
      <div className="log-list">
        {orchestratorLog.map((logEntry, index) => (
          <LogCard key={index} logEntry={logEntry} />
        ))}
      </div>
    </div>
  );
}

export default OrchestratorLog;