import React, { useState, useEffect } from 'react';
import './App.css';
import ChatPanel from './components/ChatPanel';
import OrchestratorLog from './components/OrchestratorLog';

function App() {
  const [chatHistory, setChatHistory] = useState([]);
  const [orchestratorLog, setOrchestratorLog] = useState([]);

  useEffect(() => {
    // Fetch data from the backend API
    fetch('http://localhost:8000/api/state')
      .then(response => response.json())
      .then(data => {
        setChatHistory(data.chatHistory);
        setOrchestratorLog(data.orchestratorLog);
      })
      .catch(error => console.error('Error fetching data:', error));
  }, []); // The empty dependency array ensures this effect runs only once on mount

  return (
    <div className="App">
      <ChatPanel chatHistory={chatHistory} />
      <OrchestratorLog orchestratorLog={orchestratorLog} />
    </div>
  );
}

export default App;
