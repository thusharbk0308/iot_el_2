import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useWebSocket } from '../context/WebSocketContext';
import { History, CheckCircle, XCircle, Search, Filter } from 'lucide-react';

export default function Logs() {
  const { token } = useAuth();
  const { latestAccess } = useWebSocket();
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('All'); // 'All', 'Granted', 'Denied'
  const [search, setSearch] = useState('');

  const fetchLogs = async () => {
    setLoading(true);
    try {
      let url = '/api/logs?limit=100';
      if (filter !== 'All') {
        url = `/api/logs?limit=100&status=${filter}`;
      }
      const response = await fetch(url, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setLogs(data);
      }
    } catch (err) {
      console.error('Failed to fetch logs:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, [token, filter]);

  // Sync real-time updates while on the page
  useEffect(() => {
    if (latestAccess) {
      // Prepend to array if it matches the current filter
      if (filter === 'All' || latestAccess.status === filter) {
        setLogs((prev) => [
          {
            id: Date.now(),
            timestamp: latestAccess.timestamp || new Date().toISOString(),
            name: latestAccess.name,
            status: latestAccess.status,
            confidence: latestAccess.confidence,
            signal_sent: latestAccess.signal_sent
          },
          ...prev
        ]);
      }
    }
  }, [latestAccess]);

  const filteredLogs = logs.filter(log => 
    log.name.toLowerCase().includes(search.toLowerCase()) ||
    log.status.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="flex flex-col gap-6 p-6 h-full overflow-y-auto">
      <div>
        <h2 className="text-xl font-bold text-white">Access History Logs</h2>
        <p className="text-xs text-slate-500 font-medium">Audit records of facial recognition match results.</p>
      </div>

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 bg-dark-card border border-dark-border rounded-2xl">
        {/* Search */}
        <div className="relative flex-1 max-w-sm">
          <span className="absolute inset-y-0 left-0 pl-3 flex items-center text-slate-500">
            <Search size={16} />
          </span>
          <input
            type="text"
            placeholder="Search by name..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 bg-dark-bg/60 border border-dark-border rounded-xl text-xs text-white placeholder-slate-600 focus:outline-none focus:border-primary/50 transition-colors"
          />
        </div>

        {/* Filter buttons */}
        <div className="flex items-center gap-2">
          <Filter size={16} className="text-slate-500" />
          {['All', 'Granted', 'Denied'].map((type) => (
            <button
              key={type}
              onClick={() => setFilter(type)}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold border transition-all duration-200 ${
                filter === type
                  ? 'bg-primary text-white border-primary shadow-lg shadow-primary/10'
                  : 'bg-dark-bg/40 text-slate-400 border-dark-border hover:bg-dark-hover hover:text-white'
              }`}
            >
              {type}
            </button>
          ))}
        </div>
      </div>

      {/* Logs Table */}
      <div className="bg-dark-card border border-dark-border rounded-2xl overflow-hidden flex-1">
        <div className="overflow-x-auto h-full">
          {loading ? (
            <div className="text-center py-20 text-slate-500 text-xs">Loading logs data...</div>
          ) : filteredLogs.length === 0 ? (
            <div className="text-center py-20 text-slate-500 text-xs">No matching logs found.</div>
          ) : (
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-dark-border bg-dark-bg/30 text-[10px] text-slate-500 uppercase tracking-wider font-bold">
                  <th className="p-4">Timestamp</th>
                  <th className="p-4">Attempt Classification</th>
                  <th className="p-4">Access Status</th>
                  <th className="p-4">Cosine Confidence</th>
                  <th className="p-4">Pi Lock Trigger</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-dark-border text-xs text-slate-300">
                {filteredLogs.map((log) => {
                  const isGranted = log.status === 'Granted';
                  return (
                    <tr key={log.id} className="hover:bg-dark-hover/30 transition-colors">
                      <td className="p-4 font-mono text-slate-400">
                        {new Date(log.timestamp).toLocaleString()}
                      </td>
                      <td className="p-4 font-bold text-white">
                        {log.name}
                      </td>
                      <td className="p-4">
                        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold ${
                          isGranted 
                            ? 'bg-accent-success/15 text-accent-success border border-accent-success/10' 
                            : 'bg-accent-danger/15 text-accent-danger border border-accent-danger/10'
                        }`}>
                          {isGranted ? <CheckCircle size={10} /> : <XCircle size={10} />}
                          {log.status}
                        </span>
                      </td>
                      <td className="p-4 font-semibold">
                        {log.name === 'Unknown' ? 'N/A' : `${(log.confidence * 100).toFixed(1)}%`}
                      </td>
                      <td className="p-4 font-mono">
                        <span className={`px-2 py-0.5 rounded text-[10px] ${
                          log.signal_sent === 'Yes' 
                            ? 'bg-primary/10 text-primary' 
                            : log.signal_sent === 'Failed' 
                              ? 'bg-accent-danger/10 text-accent-danger' 
                              : 'bg-dark-hover text-slate-500'
                        }`}>
                          {log.signal_sent}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
