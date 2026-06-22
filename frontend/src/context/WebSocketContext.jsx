import React, { createContext, useContext, useEffect, useState, useRef } from 'react';

const WebSocketContext = createContext(null);

export const WebSocketProvider = ({ children }) => {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState(null);
  
  // Specific real-time state registers
  const [latestAccess, setLatestAccess] = useState(null);
  const [latestIntruder, setLatestIntruder] = useState(null);
  const [lockState, setLockState] = useState("LOCKED");
  const [healthState, setHealthState] = useState({
    pi: "Offline",
    camera: "Offline",
    ai_server: "Online",
    database: "Online",
    lock: "Offline"
  });
  const [enrollmentState, setEnrollmentState] = useState(null);
  
  const ws = useRef(null);
  const reconnectTimeout = useRef(null);

  const connect = () => {
    // Generate relative WebSocket protocol based on browser environment
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    // In dev, window.location.host is localhost:3000, Vite proxies /ws to localhost:8000.
    // In prod, window.location.host is localhost:8000 (FastAPI serves everything).
    const url = `${proto}//${window.location.host}/ws`;
    
    console.log(`[WEBSOCKET] Connecting to ${url}...`);
    ws.current = new WebSocket(url);

    ws.current.onopen = () => {
      console.log('[WEBSOCKET] Connected successfully.');
      setIsConnected(true);
      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current);
      }
    };

    ws.current.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        setLastMessage(message);
        
        // Dispatch by message category
        switch (message.type) {
          case 'ACCESS':
            setLatestAccess(message);
            break;
          case 'INTRUDER':
            setLatestIntruder(message);
            break;
          case 'LOCK':
            setLockState(message.status);
            break;
          case 'HEALTH':
            setHealthState({
              pi: message.pi,
              camera: message.camera,
              ai_server: message.ai_server,
              database: message.database,
              lock: message.lock
            });
            break;
          case 'ENROLLMENT':
            setEnrollmentState(message);
            break;
          default:
            break;
        }
      } catch (err) {
        console.error('[WEBSOCKET] Failed to parse message body:', err);
      }
    };

    ws.current.onclose = () => {
      console.warn('[WEBSOCKET] Connection closed. Retrying in 3 seconds...');
      setIsConnected(false);
      reconnectTimeout.current = setTimeout(() => {
        connect();
      }, 3000);
    };

    ws.current.onerror = (error) => {
      console.error('[WEBSOCKET] Connection error:', error);
      ws.current.close();
    };
  };

  useEffect(() => {
    connect();
    return () => {
      if (ws.current) {
        ws.current.close();
      }
      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current);
      }
    };
  }, []);

  return (
    <WebSocketContext.Provider value={{ 
      isConnected, 
      lastMessage, 
      latestAccess, 
      latestIntruder, 
      lockState, 
      healthState, 
      enrollmentState,
      setEnrollmentState
    }}>
      {children}
    </WebSocketContext.Provider>
  );
};

export const useWebSocket = () => {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
};
