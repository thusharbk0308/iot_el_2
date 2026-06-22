import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useWebSocket } from '../context/WebSocketContext';
import { ShieldAlert, Trash2, Calendar, Clock, Eye, MailCheck, Loader2 } from 'lucide-react';

export default function Gallery() {
  const { token, isAdmin } = useAuth();
  const { latestIntruder } = useWebSocket();
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeImage, setActiveImage] = useState(null);
  const [deletingId, setDeletingId] = useState(null);

  const fetchAlerts = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/alerts?limit=60', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setAlerts(data);
      }
    } catch (err) {
      console.error('Failed to load intruder gallery:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAlerts();
  }, [token]);

  // Sync real-time updates
  useEffect(() => {
    if (latestIntruder) {
      setAlerts((prev) => [
        {
          id: Date.now(),
          timestamp: latestIntruder.timestamp || new Date().toISOString(),
          snapshot_path: latestIntruder.snapshot_path,
          email_sent: true
        },
        ...prev
      ]);
    }
  }, [latestIntruder]);

  const handleDelete = async (id, e) => {
    e.stopPropagation(); // Avoid triggering details modal
    if (!window.confirm("Are you sure you want to delete this security alert snapshot?")) {
      return;
    }
    
    setDeletingId(id);
    try {
      const response = await fetch(`/api/alerts/${id}`, {
        method: 'DELETE',
        headers: { 
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (response.ok) {
        setAlerts((prev) => prev.filter(alert => alert.id !== id));
      }
    } catch (err) {
      console.error("Failed to delete alert record:", err);
    } finally {
      setDeletingId(null);
    }
  };

  const isUserAdmin = isAdmin();

  return (
    <div className="flex flex-col gap-6 p-6 h-full overflow-y-auto">
      <div>
        <h2 className="text-xl font-bold text-white">Security Breaches Gallery</h2>
        <p className="text-xs text-slate-500 font-medium">Archived camera snaps of access denials and unknown faces.</p>
      </div>

      {loading ? (
        <div className="text-center py-20 text-slate-500 text-xs">Loading alert gallery data...</div>
      ) : alerts.length === 0 ? (
        <div className="text-center py-20 text-slate-500 border border-dashed border-dark-border rounded-2xl">
          <ShieldAlert className="mx-auto text-slate-700 mb-2" size={32} />
          <p className="text-xs text-slate-500">No intruder snapshots recorded yet.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-6">
          {alerts.map((alert) => (
            <div 
              key={alert.id}
              onClick={() => setActiveImage(alert)}
              className="bg-dark-card border border-dark-border rounded-2xl overflow-hidden hover:border-slate-700 group cursor-pointer transition-all duration-200"
            >
              {/* Photo */}
              <div className="relative aspect-video bg-black overflow-hidden border-b border-dark-border">
                <img 
                  src={alert.snapshot_path} 
                  alt="Intruder Snapshot"
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                  onError={(e) => {
                    e.target.src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%25232F3E61' stroke-width='1.5'%3E%3Crect width='18' height='18' x='3' y='3' rx='2' ry='2'/%3E%3Ccircle cx='9' cy='9' r='2'/%3E%3Cpath d='m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21'/%3E%3C/svg%3E";
                  }}
                />
                <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity duration-200">
                  <div className="flex items-center gap-1 text-white bg-slate-900/80 px-3 py-1.5 rounded-lg text-xs font-semibold">
                    <Eye size={14} />
                    Inspect Frame
                  </div>
                </div>
              </div>

              {/* Card Metadata */}
              <div className="p-4 flex flex-col gap-3">
                <div className="flex flex-col gap-1">
                  <span className="text-xs text-slate-400 font-semibold flex items-center gap-1">
                    <Calendar size={12} className="text-slate-500" />
                    {new Date(alert.timestamp).toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' })}
                  </span>
                  <span className="text-[10px] text-slate-500 flex items-center gap-1 font-mono">
                    <Clock size={12} />
                    {new Date(alert.timestamp).toLocaleTimeString()}
                  </span>
                </div>

                <div className="flex items-center justify-between border-t border-dark-border/40 pt-3">
                  <span className="inline-flex items-center gap-1 text-[10px] font-bold text-accent-success bg-accent-success/10 px-2 py-0.5 rounded border border-accent-success/10">
                    <MailCheck size={10} />
                    Email Sent
                  </span>
                  
                  {isUserAdmin && (
                    <button
                      onClick={(e) => handleDelete(alert.id, e)}
                      disabled={deletingId === alert.id}
                      className="p-1.5 bg-accent-danger/10 text-accent-danger hover:bg-accent-danger hover:text-white rounded-lg border border-accent-danger/10 transition-colors"
                      title="Delete snapshot"
                    >
                      {deletingId === alert.id ? (
                        <Loader2 className="animate-spin" size={14} />
                      ) : (
                        <Trash2 size={14} />
                      )}
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* High-Resolution Inspection Modal */}
      {activeImage && (
        <div 
          onClick={() => setActiveImage(null)}
          className="fixed inset-0 z-50 bg-black/90 backdrop-blur-sm flex items-center justify-center p-4 cursor-zoom-out"
        >
          <div 
            onClick={(e) => e.stopPropagation()} 
            className="w-full max-w-3xl bg-dark-card border border-dark-border rounded-3xl overflow-hidden shadow-2xl relative"
          >
            <div className="relative aspect-video bg-black flex items-center justify-center">
              <img 
                src={activeImage.snapshot_path} 
                alt="High-Res Inspection Frame"
                className="max-h-[75vh] w-full object-contain"
              />
            </div>
            
            <div className="p-5 flex justify-between items-center bg-dark-bg/60 border-t border-dark-border">
              <div>
                <h4 className="font-bold text-white text-sm">Security Incident Snapshot</h4>
                <p className="text-[10px] text-slate-500 font-mono mt-1">
                  Recorded: {new Date(activeImage.timestamp).toLocaleString()}
                </p>
              </div>
              <button 
                onClick={() => setActiveImage(null)}
                className="px-4 py-2 bg-dark-hover hover:bg-slate-800 text-white rounded-xl text-xs font-semibold border border-dark-border"
              >
                Close Inspector
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
