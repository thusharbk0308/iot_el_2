import React, { useEffect, useState } from 'react';
import { 
  Activity, 
  CheckCircle2, 
  XCircle, 
  AlertTriangle, 
  Calendar, 
  Clock, 
  ShieldAlert,
  Bell
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useWebSocket } from '../context/WebSocketContext';
import HealthPanel from '../components/HealthPanel';
import LockToggle from '../components/LockToggle';

export default function Dashboard() {
  const { token } = useAuth();
  const { latestAccess, latestIntruder } = useWebSocket();
  const [logs, setLogs] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [alertOverlay, setAlertOverlay] = useState(null);

  // Fetch initial logs and notifications on mount
  useEffect(() => {
    const fetchData = async () => {
      try {
        const headers = { 'Authorization': `Bearer ${token}` };
        
        // Logs
        const logsRes = await fetch('/api/logs?limit=8', { headers });
        if (logsRes.ok) {
          const logsData = await logsRes.ok ? await logsRes.json() : [];
          setLogs(logsData);
        }
        
        // Notifications
        const notifRes = await fetch('/api/notifications?limit=5', { headers });
        if (notifRes.ok) {
          const notifData = await notifRes.json();
          setNotifications(notifData);
        }
      } catch (err) {
        console.error('Failed to fetch dashboard feed data:', err);
      }
    };
    fetchData();
  }, [token]);

  // Sync real-time ACCESS logs from WebSockets
  useEffect(() => {
    if (latestAccess) {
      // Add to list and truncate to limit
      setLogs((prevLogs) => {
        const newLog = {
          id: Date.now(), // temporary ID
          timestamp: latestAccess.timestamp || new Date().toISOString(),
          name: latestAccess.name,
          status: latestAccess.status,
          confidence: latestAccess.confidence,
          signal_sent: latestAccess.signal_sent
        };
        return [newLog, ...prevLogs.slice(0, 7)];
      });
    }
  }, [latestAccess]);

  // Sync real-time INTRUDER alarms from WebSockets
  useEffect(() => {
    if (latestIntruder) {
      setAlertOverlay({
        timestamp: latestIntruder.timestamp,
        snapshot_path: latestIntruder.snapshot_path
      });
      
      // Auto dismiss overlay after 8 seconds
      const timer = setTimeout(() => {
        setAlertOverlay(null);
      }, 8000);
      
      // Add notification to list
      setNotifications((prev) => [
        {
          id: Date.now(),
          timestamp: new Date().toISOString(),
          message: "SECURITY WARNING: Unknown intruder detected. Snapshot dispatched.",
          type: "Alert",
          is_read: false
        },
        ...prev.slice(0, 4)
      ]);
      
      return () => clearTimeout(timer);
    }
  }, [latestIntruder]);

  const formatTime = (isoString) => {
    try {
      const date = new Date(isoString);
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
      return '';
    }
  };

  const formatDate = (isoString) => {
    try {
      const date = new Date(isoString);
      return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
    } catch {
      return '';
    }
  };

  return (
    <div className="flex flex-col gap-6 p-6 h-full overflow-y-auto">
      
      {/* Real-time Alert Overlay Alert (Toast style) */}
      {alertOverlay && (
        <div className="bg-accent-danger text-white border border-accent-danger/20 p-4 rounded-2xl shadow-xl shadow-accent-danger/30 flex items-center justify-between animate-bounce gap-4 relative z-50">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-white/20 rounded-xl">
              <ShieldAlert size={24} className="animate-pulse" />
            </div>
            <div>
              <h4 className="font-bold text-base leading-tight">INTRUDER DETECTED!</h4>
              <p className="text-xs text-white/80">Security breach snapshot recorded at {alertOverlay.timestamp}</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <a 
              href={alertOverlay.snapshot_path}
              target="_blank"
              rel="noreferrer"
              className="px-3.5 py-1.5 bg-white text-accent-danger text-xs font-bold rounded-lg hover:bg-white/90 transition-colors"
            >
              View Image
            </a>
            <button 
              onClick={() => setAlertOverlay(null)}
              className="text-white/70 hover:text-white font-bold text-sm px-2 py-1"
            >
              Dismiss
            </button>
          </div>
        </div>
      )}

      {/* Header section */}
      <div>
        <h2 className="text-xl font-bold text-white">Security Command Station</h2>
        <p className="text-xs text-slate-500">Real-time surveillance & biometric access management.</p>
      </div>

      {/* System Health Indicators */}
      <HealthPanel />

      {/* Live Stream and Controls */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Stream */}
        <div className="lg:col-span-2 p-4 bg-dark-card border border-dark-border rounded-3xl flex flex-col gap-3">
          <div className="flex items-center justify-between px-2">
            <div className="flex items-center gap-2">
              <span className="h-2.5 w-2.5 rounded-full bg-accent-danger animate-ping" />
              <span className="text-xs font-bold uppercase tracking-wider text-slate-300">Live Surveillance Feed</span>
            </div>
            <span className="text-[10px] bg-dark-border px-2 py-1 rounded text-slate-400 font-mono">1080p stream</span>
          </div>
          
          <div className="relative aspect-video bg-black rounded-2xl overflow-hidden border border-dark-border flex items-center justify-center">
            <img 
              src="/api/camera/stream" 
              alt="Security Feed"
              className="w-full h-full object-contain"
              onError={(e) => {
                e.target.src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%25232F3E61' stroke-width='1.5'%3E%3Crect width='18' height='18' x='3' y='3' rx='2' ry='2'/%3E%3Cpath d='m16 8-4.5 4.5L9 10l-4 4'/%3E%3Ccircle cx='17' cy='8' r='1'/%3E%3C/svg%3E";
              }}
            />
          </div>
        </div>

        {/* Lock Controls */}
        <div className="lg:col-span-1">
          <LockToggle />
        </div>
      </div>

      {/* Access Activity Feed & Notifications */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Logs Feed */}
        <div className="lg:col-span-2 p-6 bg-dark-card border border-dark-border rounded-3xl">
          <div className="flex items-center gap-2 mb-4">
            <Activity size={18} className="text-primary" />
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">Access Attempt Activity Log</h3>
          </div>
          
          <div className="space-y-2 max-h-[300px] overflow-y-auto pr-2">
            {logs.length === 0 ? (
              <p className="text-xs text-slate-500 text-center py-8">No access logs collected yet.</p>
            ) : (
              logs.map((log) => {
                const granted = log.status === 'Granted';
                return (
                  <div 
                    key={log.id} 
                    className="p-3 bg-dark-bg/40 border border-dark-border/50 rounded-xl flex items-center justify-between"
                  >
                    <div className="flex items-center gap-3">
                      {granted ? (
                        <div className="text-accent-success">
                          <CheckCircle2 size={18} />
                        </div>
                      ) : (
                        <div className="text-accent-danger">
                          <XCircle size={18} />
                        </div>
                      )}
                      <div>
                        <p className="text-sm font-semibold text-white">
                          {log.name === 'Unknown' ? 'Access Denied' : log.name}
                        </p>
                        <p className="text-[10px] text-slate-500">
                          Confidence: {log.name === 'Unknown' ? 'N/A' : `${(log.confidence * 100).toFixed(1)}%`} | Pi Signal: {log.signal_sent}
                        </p>
                      </div>
                    </div>
                    <div className="flex flex-col items-end gap-0.5">
                      <span className="text-xs font-semibold text-slate-400 flex items-center gap-1">
                        <Clock size={12} />
                        {formatTime(log.timestamp)}
                      </span>
                      <span className="text-[9px] text-slate-600 flex items-center gap-1">
                        <Calendar size={10} />
                        {formatDate(log.timestamp)}
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Notifications list */}
        <div className="lg:col-span-1 p-6 bg-dark-card border border-dark-border rounded-3xl">
          <div className="flex items-center gap-2 mb-4">
            <Bell size={18} className="text-accent-warning" />
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">System Alerts</h3>
          </div>
          
          <div className="space-y-3 max-h-[300px] overflow-y-auto pr-2">
            {notifications.length === 0 ? (
              <p className="text-xs text-slate-500 text-center py-8">No active notifications.</p>
            ) : (
              notifications.map((notif) => (
                <div 
                  key={notif.id}
                  className="p-3 bg-dark-bg/20 rounded-xl border border-dark-border/40 flex items-start gap-2.5"
                >
                  <span className="mt-1 flex-shrink-0">
                    {notif.type === 'Alert' ? (
                      <AlertTriangle size={14} className="text-accent-danger" />
                    ) : (
                      <div className="h-1.5 w-1.5 rounded-full bg-primary mt-1" />
                    )}
                  </span>
                  <div>
                    <p className="text-xs text-slate-300 leading-normal">{notif.message}</p>
                    <span className="text-[9px] text-slate-600 block mt-1">{formatTime(notif.timestamp)}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
