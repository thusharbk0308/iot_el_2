import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { WebSocketProvider } from './context/WebSocketContext';
import Sidebar from './components/Sidebar';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Logs from './pages/Logs';
import Gallery from './pages/Gallery';
import UserManagement from './pages/UserManagement';

function ProtectedLayout() {
  const { token } = useAuth();
  
  // Redirect to login if user is not authenticated
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  
  return (
    // Wrap authenticated dashboard in WebSocket provider so it links dynamically after login
    <WebSocketProvider>
      <div className="flex h-screen bg-[#0B0F19] text-[#E2E8F0] overflow-hidden">
        <Sidebar />
        <div className="flex-1 min-w-0 flex flex-col h-full bg-[#0B0F19]">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/logs" element={<Logs />} />
            <Route path="/gallery" element={<Gallery />} />
            <Route path="/users" element={<UserManagement />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </div>
    </WebSocketProvider>
  );
}

export default function App() {
  return (
    <Router>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/*" element={<ProtectedLayout />} />
        </Routes>
      </AuthProvider>
    </Router>
  );
}
