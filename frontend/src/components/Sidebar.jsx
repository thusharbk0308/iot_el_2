import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  History, 
  ShieldAlert, 
  UserCheck, 
  LogOut, 
  Shield, 
  Lock, 
  Unlock 
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useWebSocket } from '../context/WebSocketContext';

export default function Sidebar() {
  const { user, logout } = useAuth();
  const { lockState } = useWebSocket();

  const links = [
    { name: 'Dashboard', path: '/', icon: LayoutDashboard },
    { name: 'Logs', path: '/logs', icon: History },
    { name: 'Intruder Gallery', path: '/gallery', icon: ShieldAlert },
    { name: 'Authorized Users', path: '/users', icon: UserCheck },
  ];

  return (
    <div className="w-64 bg-dark-card border-r border-dark-border flex flex-col h-full text-slate-300">
      {/* Brand Header */}
      <div className="p-6 border-b border-dark-border flex items-center gap-3">
        <div className="p-2 bg-primary/10 rounded-lg text-primary">
          <Shield size={24} />
        </div>
        <div>
          <h1 className="font-bold text-lg text-white leading-tight">SMART SENTINEL</h1>
          <span className="text-xs text-slate-500">Security Control Unit</span>
        </div>
      </div>

      {/* Nav Links */}
      <nav className="flex-1 p-4 space-y-1">
        {links.map((link) => {
          const Icon = link.icon;
          return (
            <NavLink
              key={link.path}
              to={link.path}
              className={({ isActive }) => 
                `flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-all duration-200 ${
                  isActive 
                    ? 'bg-primary text-white shadow-lg shadow-primary/20' 
                    : 'hover:bg-dark-hover text-slate-400 hover:text-white'
                }`
              }
            >
              <Icon size={18} />
              {link.name}
            </NavLink>
          );
        })}
      </nav>

      {/* Real-time Lock Status Widget */}
      <div className="p-4 mx-4 mb-4 rounded-xl bg-dark-bg/50 border border-dark-border flex flex-col items-center gap-2">
        <span className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Door Status</span>
        <div className="flex items-center gap-2">
          {lockState === 'LOCKED' ? (
            <>
              <div className="p-2 bg-accent-danger/10 rounded-full text-accent-danger">
                <Lock size={18} />
              </div>
              <span className="text-sm font-bold text-accent-danger">LOCKED</span>
            </>
          ) : (
            <>
              <div className="p-2 bg-accent-success/10 rounded-full text-accent-success animate-pulse">
                <Unlock size={18} />
              </div>
              <span className="text-sm font-bold text-accent-success">UNLOCKED</span>
            </>
          )}
        </div>
      </div>

      {/* User profile & logout footer */}
      <div className="p-4 border-t border-dark-border flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 bg-primary/20 text-primary border border-primary/30 flex items-center justify-center font-bold text-sm rounded-full">
            {user?.username?.substring(0, 2).toUpperCase() || 'US'}
          </div>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-white truncate">{user?.username}</p>
            <p className="text-xs text-slate-500 capitalize">{user?.role}</p>
          </div>
        </div>
        <button 
          onClick={logout}
          className="p-2 text-slate-500 hover:text-white hover:bg-dark-hover rounded-lg transition-colors"
          title="Sign Out"
        >
          <LogOut size={18} />
        </button>
      </div>
    </div>
  );
}
