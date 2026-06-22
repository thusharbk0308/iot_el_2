import React, { useState } from 'react';
import { Lock, Unlock, Loader2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useWebSocket } from '../context/WebSocketContext';

export default function LockToggle() {
  const { getAuthHeaders, isAdmin } = useAuth();
  const { lockState } = useWebSocket();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleLockAction = async (action) => {
    setLoading(true);
    setError('');
    try {
      const response = await fetch('/api/lock/control', {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ action }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || `Failed to execute ${action} command`);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const isUserAdmin = isAdmin();

  return (
    <div className="p-6 bg-dark-card border border-dark-border rounded-2xl flex flex-col h-full justify-between">
      <div>
        <h3 className="text-base font-bold text-white mb-1">Access Control Unit</h3>
        <p className="text-xs text-slate-500 mb-4">
          {!isUserAdmin 
            ? 'Administrator clearance required for manual overrides.' 
            : 'Remotely toggle the lock status of the node.'}
        </p>
      </div>

      <div className="flex flex-col gap-3 my-4">
        {lockState === 'LOCKED' ? (
          <button
            onClick={() => handleLockAction('unlock')}
            disabled={loading || !isUserAdmin}
            className={`w-full py-4 rounded-xl font-bold flex items-center justify-center gap-2 transition-all duration-200 ${
              !isUserAdmin 
                ? 'bg-dark-hover text-slate-600 cursor-not-allowed border border-dark-border'
                : 'bg-accent-success hover:bg-accent-success/90 text-white shadow-lg shadow-accent-success/20'
            }`}
          >
            {loading ? (
              <Loader2 className="animate-spin" size={20} />
            ) : (
              <Unlock size={20} />
            )}
            Manual Unlock (3s)
          </button>
        ) : (
          <button
            onClick={() => handleLockAction('lock')}
            disabled={loading || !isUserAdmin}
            className={`w-full py-4 rounded-xl font-bold flex items-center justify-center gap-2 transition-all duration-200 ${
              !isUserAdmin 
                ? 'bg-dark-hover text-slate-600 cursor-not-allowed border border-dark-border'
                : 'bg-accent-danger hover:bg-accent-danger/90 text-white shadow-lg shadow-accent-danger/20 animate-pulse'
            }`}
          >
            {loading ? (
              <Loader2 className="animate-spin" size={20} />
            ) : (
              <Lock size={20} />
            )}
            Force Lock System
          </button>
        )}
      </div>

      {error && (
        <p className="text-xs text-accent-danger font-medium mt-2 text-center bg-accent-danger/10 p-2 rounded-lg border border-accent-danger/20">
          {error}
        </p>
      )}

      {!isUserAdmin && (
        <div className="text-center py-2 px-3 bg-dark-bg/60 rounded-lg border border-dark-border">
          <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold">Clearance Level: User</span>
        </div>
      )}
    </div>
  );
}
