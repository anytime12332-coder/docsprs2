'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';
import toast from 'react-hot-toast';
import { Settings, Lock, Loader2, Server } from 'lucide-react';

export default function SettingsPage() {
  const { user } = useAuth();
  const [config, setConfig] = useState<Record<string, any> | null>(null);
  const [loading, setLoading] = useState(true);
  const [passwords, setPasswords] = useState({ current: '', new: '', confirm: '' });
  const [changingPassword, setChangingPassword] = useState(false);

  useEffect(() => { loadConfig(); }, []);

  const loadConfig = async () => {
    try { const { data } = await api.getSystemConfig(); setConfig(data); }
    catch { toast.error('Failed to load config'); }
    finally { setLoading(false); }
  };

  const handleChangePassword = async () => {
    if (passwords.new !== passwords.confirm) { toast.error('Passwords do not match'); return; }
    if (passwords.new.length < 8) { toast.error('Password must be at least 8 characters'); return; }
    setChangingPassword(true);
    try {
      await api.changePassword(passwords.current, passwords.new);
      toast.success('Password changed successfully');
      setPasswords({ current: '', new: '', confirm: '' });
    } catch (e: any) { toast.error(e.response?.data?.detail || 'Failed'); }
    finally { setChangingPassword(false); }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Settings</h1>
        <p className="text-dark-400 mt-1">System configuration and account settings</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Change Password */}
        <div className="card">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Lock className="w-5 h-5 text-primary-400" /> Change Password
          </h3>
          <div className="space-y-3">
            <div>
              <label className="block text-sm text-dark-400 mb-1">Current Password</label>
              <input type="password" value={passwords.current} onChange={e => setPasswords(p => ({ ...p, current: e.target.value }))} className="input-field" />
            </div>
            <div>
              <label className="block text-sm text-dark-400 mb-1">New Password</label>
              <input type="password" value={passwords.new} onChange={e => setPasswords(p => ({ ...p, new: e.target.value }))} className="input-field" />
            </div>
            <div>
              <label className="block text-sm text-dark-400 mb-1">Confirm New Password</label>
              <input type="password" value={passwords.confirm} onChange={e => setPasswords(p => ({ ...p, confirm: e.target.value }))} className="input-field" />
            </div>
            <button onClick={handleChangePassword} disabled={changingPassword || !passwords.current || !passwords.new} className="btn-primary w-full flex items-center justify-center gap-2">
              {changingPassword ? <Loader2 className="w-4 h-4 animate-spin" /> : <Lock className="w-4 h-4" />}
              Update Password
            </button>
          </div>
        </div>

        {/* System Config */}
        <div className="card">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Server className="w-5 h-5 text-green-400" /> System Configuration
          </h3>
          {loading ? (
            <div className="animate-pulse space-y-3">
              {[...Array(8)].map((_, i) => <div key={i} className="h-6 bg-dark-800 rounded" />)}
            </div>
          ) : config ? (
            <dl className="space-y-2">
              {Object.entries(config).map(([key, value]) => (
                <div key={key} className="flex justify-between py-1.5 border-b border-dark-800">
                  <dt className="text-sm text-dark-400">{key.replace(/_/g, ' ')}</dt>
                  <dd className="text-sm text-dark-200 font-mono">
                    {Array.isArray(value) ? value.join(', ') : String(value)}
                  </dd>
                </div>
              ))}
            </dl>
          ) : (
            <p className="text-dark-500">Failed to load configuration</p>
          )}
        </div>
      </div>
    </div>
  );
}
