import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useWebSocket } from '../context/WebSocketContext';
import { 
  UserCheck, 
  UserPlus, 
  Trash2, 
  Loader2, 
  Calendar, 
  Sparkles,
  Camera,
  XCircle,
  CheckCircle2
} from 'lucide-react';

export default function UserManagement() {
  const { token, isAdmin } = useAuth();
  const { enrollmentState, setEnrollmentState } = useWebSocket();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Modal & Enrollment States
  const [modalOpen, setModalOpen] = useState(false);
  const [enrollName, setEnrollName] = useState('');
  const [enrollStatus, setEnrollStatus] = useState('idle'); // 'idle', 'submitting', 'capturing', 'rebuilding', 'success', 'failed'
  const [enrollProgress, setEnrollProgress] = useState(0);
  const [error, setError] = useState('');
  const [actionLoading, setActionLoading] = useState(false);

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/users', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setUsers(data);
      }
    } catch (err) {
      console.error('Failed to fetch authorized users list:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, [token]);

  // Handle real-time WebSocket enrollment status packets
  useEffect(() => {
    if (enrollmentState) {
      const { status, progress, name } = enrollmentState;
      if (status === 'Progress') {
        setEnrollStatus('capturing');
        setEnrollProgress(progress);
      } else if (status === 'Success') {
        setEnrollStatus('success');
        fetchUsers(); // Refresh the list
        // Reset enrollment websocket packet from state context to prevent loop re-triggers
        setEnrollmentState(null);
      } else if (status === 'Failed') {
        setEnrollStatus('failed');
        setEnrollmentState(null);
      }
    }
  }, [enrollmentState]);

  const handleEnrollSubmit = async (e) => {
    e.preventDefault();
    if (!enrollName.trim()) return;
    
    setEnrollStatus('submitting');
    setError('');
    try {
      const response = await fetch(`/api/users/enroll?name=${encodeURIComponent(enrollName)}`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to initialize face capture session.');
      }
      
      setEnrollStatus('capturing');
      setEnrollProgress(0);
    } catch (err) {
      setError(err.message);
      setEnrollStatus('failed');
    }
  };

  const handleDelete = async (name) => {
    if (!window.confirm(`Are you sure you want to completely remove authorized user '${name}'? This deletes their face dataset.`)) {
      return;
    }
    
    setActionLoading(true);
    try {
      const response = await fetch(`/api/users/${encodeURIComponent(name)}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        setUsers((prev) => prev.filter(user => user.name !== name));
      } else {
        const data = await response.json();
        alert(data.detail || 'Failed to remove user');
      }
    } catch (err) {
      console.error(err);
    } finally {
      setActionLoading(false);
    }
  };

  const isUserAdmin = isAdmin();

  return (
    <div className="flex flex-col gap-6 p-6 h-full overflow-y-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white">Authorized Security Profiles</h2>
          <p className="text-xs text-slate-500 font-medium">Verify credentials and manage facial recognition enrollments.</p>
        </div>
        
        {isUserAdmin && (
          <button
            onClick={() => {
              setEnrollName('');
              setEnrollStatus('idle');
              setEnrollProgress(0);
              setError('');
              setModalOpen(true);
            }}
            className="px-4 py-2.5 bg-primary hover:bg-primary/95 text-white font-bold rounded-xl text-xs flex items-center gap-2 transition-all duration-200 shadow-lg shadow-primary/10"
          >
            <UserPlus size={16} />
            Enroll New Profile
          </button>
        )}
      </div>

      {/* Users List Card Grid */}
      {loading ? (
        <div className="text-center py-20 text-slate-500 text-xs">Loading profile registries...</div>
      ) : users.length === 0 ? (
        <div className="text-center py-20 text-slate-500 border border-dashed border-dark-border rounded-2xl">
          <UserCheck className="mx-auto text-slate-700 mb-2" size={32} />
          <p className="text-xs text-slate-500">No authorized faces enrolled in database.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {users.map((item) => (
            <div 
              key={item.id}
              className="p-5 bg-dark-card border border-dark-border rounded-2xl flex items-center justify-between group hover:border-slate-700 transition-colors"
            >
              <div className="flex items-center gap-3.5">
                <div className="h-11 w-11 bg-primary/10 text-primary border border-primary/20 flex items-center justify-center font-bold text-sm rounded-2xl">
                  {item.name.substring(0, 2).toUpperCase()}
                </div>
                <div>
                  <h4 className="font-bold text-white text-sm leading-snug">{item.name}</h4>
                  <div className="flex items-center gap-3 text-[10px] text-slate-500 mt-1">
                    <span className="font-semibold text-primary bg-primary/10 px-2 py-0.5 rounded border border-primary/10">
                      {item.image_count} Samples
                    </span>
                    <span className="flex items-center gap-0.5">
                      <Calendar size={10} />
                      {new Date(item.created_at).toLocaleDateString([], { month: 'short', day: 'numeric' })}
                    </span>
                  </div>
                </div>
              </div>
              
              {isUserAdmin && (
                <button
                  onClick={() => handleDelete(item.name)}
                  disabled={actionLoading}
                  className="p-2 text-slate-500 hover:text-accent-danger hover:bg-accent-danger/10 rounded-xl border border-transparent hover:border-accent-danger/25 opacity-0 group-hover:opacity-100 focus:opacity-100 transition-all duration-200"
                  title="Remove user profile"
                >
                  <Trash2 size={16} />
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Face Enrollment Wizard Modal */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-md bg-dark-card border border-dark-border rounded-3xl p-6 shadow-2xl relative">
            <h3 className="text-base font-bold text-white mb-1">Biometric Enrollment Wizard</h3>
            <p className="text-xs text-slate-500 mb-6">Create a secure facial map template for database checks.</p>

            {/* Wizard Screen States */}
            {enrollStatus === 'idle' && (
              <form onSubmit={handleEnrollSubmit} className="space-y-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-slate-400">Full Name</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. John Doe"
                    value={enrollName}
                    onChange={(e) => setEnrollName(e.target.value)}
                    className="w-full px-4 py-3 bg-dark-bg/60 border border-dark-border rounded-xl text-sm text-white placeholder-slate-600 focus:outline-none focus:border-primary/50 transition-colors"
                  />
                </div>
                <button
                  type="submit"
                  className="w-full py-3.5 bg-primary hover:bg-primary/95 text-white font-bold rounded-xl text-xs flex items-center justify-center gap-2 shadow-lg shadow-primary/10 transition-colors"
                >
                  <Camera size={14} />
                  Initiate Camera Captures
                </button>
              </form>
            )}

            {(enrollStatus === 'submitting' || enrollStatus === 'capturing') && (
              <div className="flex flex-col items-center py-6 text-center">
                <Loader2 className="animate-spin text-primary mb-4" size={32} />
                <h4 className="font-bold text-white text-sm">Surveillance Capture Active</h4>
                <p className="text-xs text-slate-500 max-w-[280px] mt-1.5 leading-relaxed">
                  Stand in front of the Raspberry Pi camera. Move your head slowly to record multiple angles.
                </p>

                {/* Progress bar */}
                <div className="w-full bg-dark-bg border border-dark-border rounded-full h-3.5 mt-6 overflow-hidden relative">
                  <div 
                    className="bg-gradient-to-r from-primary to-cyan-500 h-full transition-all duration-300 rounded-full" 
                    style={{ width: `${enrollProgress}%` }}
                  />
                </div>
                <span className="text-[10px] font-bold text-primary tracking-wider uppercase mt-2.5">
                  Frame Capture: {enrollProgress}%
                </span>
              </div>
            )}

            {enrollStatus === 'success' && (
              <div className="flex flex-col items-center py-6 text-center">
                <CheckCircle2 className="text-accent-success mb-3" size={44} />
                <h4 className="font-bold text-white text-sm">Enrollment Complete!</h4>
                <p className="text-xs text-slate-500 max-w-[280px] mt-1.5 leading-relaxed">
                  Face templates for '{enrollName}' have been compiled and integrated into the authorized profiles.
                </p>
                <button
                  onClick={() => setModalOpen(false)}
                  className="w-full mt-6 py-2.5 bg-accent-success/15 hover:bg-accent-success/20 text-accent-success font-bold rounded-xl text-xs border border-accent-success/10 transition-colors"
                >
                  Dismiss Wizard
                </button>
              </div>
            )}

            {enrollStatus === 'failed' && (
              <div className="flex flex-col items-center py-6 text-center">
                <XCircle className="text-accent-danger mb-3" size={44} />
                <h4 className="font-bold text-white text-sm">Enrollment Failed</h4>
                <p className="text-xs text-slate-500 max-w-[280px] mt-1.5 leading-relaxed">
                  {error || 'The system could not compile enough facial frames. Please try again.'}
                </p>
                <div className="flex gap-3 w-full mt-6">
                  <button
                    onClick={() => setEnrollStatus('idle')}
                    className="flex-1 py-2.5 bg-primary/10 hover:bg-primary/20 text-primary border border-primary/10 font-bold rounded-xl text-xs transition-colors"
                  >
                    Retry Setup
                  </button>
                  <button
                    onClick={() => setModalOpen(false)}
                    className="flex-1 py-2.5 bg-dark-hover hover:bg-slate-800 text-white border border-dark-border font-bold rounded-xl text-xs transition-colors"
                  >
                    Close
                  </button>
                </div>
              </div>
            )}

            {/* Cancel Button */}
            {enrollStatus === 'idle' && (
              <button 
                onClick={() => setModalOpen(false)}
                className="absolute top-4 right-4 text-slate-500 hover:text-white transition-colors"
              >
                ✕
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
