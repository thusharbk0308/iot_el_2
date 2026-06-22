import React from 'react';
import { Cpu, Video, Server, Database } from 'lucide-react';
import { useWebSocket } from '../context/WebSocketContext';

export default function HealthPanel() {
  const { healthState } = useWebSocket();

  const statuses = [
    {
      name: 'Raspberry Pi',
      status: healthState.pi,
      icon: Cpu,
    },
    {
      name: 'Camera Feed',
      status: healthState.camera,
      icon: Video,
    },
    {
      name: 'AI Inference Server',
      status: healthState.ai_server,
      icon: Server,
    },
    {
      name: 'Database Unit',
      status: healthState.database,
      icon: Database,
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
      {statuses.map((item) => {
        const Icon = item.icon;
        const isOnline = item.status === 'Online';
        return (
          <div 
            key={item.name} 
            className="p-4 bg-dark-card border border-dark-border rounded-xl flex items-center justify-between"
          >
            <div className="flex items-center gap-3">
              <div className={`p-2 rounded-lg ${isOnline ? 'bg-primary/10 text-primary' : 'bg-accent-danger/10 text-accent-danger'}`}>
                <Icon size={20} />
              </div>
              <div>
                <p className="text-xs text-slate-500 font-medium">{item.name}</p>
                <p className="text-sm font-semibold text-white">{isOnline ? 'Active' : 'Offline'}</p>
              </div>
            </div>
            <div className="flex items-center gap-1.5">
              <span className={`h-2 w-2 rounded-full ${isOnline ? 'bg-accent-success animate-pulse' : 'bg-accent-danger'}`} />
              <span className={`text-xs font-semibold ${isOnline ? 'text-accent-success' : 'text-accent-danger'}`}>
                {item.status}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
