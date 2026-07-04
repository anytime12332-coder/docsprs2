'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { User } from '@/lib/types';
import DataTable from '@/components/DataTable';
import Modal from '@/components/Modal';
import { formatDate, cn } from '@/lib/utils';
import toast from 'react-hot-toast';
import { Plus, Trash2, Shield, Loader2, UserPlus } from 'lucide-react';

export default function UsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [formData, setFormData] = useState({ email: '', password: '', full_name: '', is_admin: false });
  const [saving, setSaving] = useState(false);

  useEffect(() => { loadUsers(); }, []);

  const loadUsers = async () => {
    setLoading(true);
    try { const { data } = await api.listUsers(); setUsers(data.users); }
    catch { toast.error('Failed to load users'); }
    finally { setLoading(false); }
  };

  const handleCreate = async () => {
    setSaving(true);
    try {
      await api.createUser(formData);
      toast.success('User created');
      setShowCreate(false);
      setFormData({ email: '', password: '', full_name: '', is_admin: false });
      loadUsers();
    } catch (e: any) { toast.error(e.response?.data?.detail || 'Failed'); }
    finally { setSaving(false); }
  };

  const handleToggleActive = async (user: User) => {
    try {
      await api.updateUser(user.id, { is_active: !user.is_active });
      toast.success(`User ${user.is_active ? 'deactivated' : 'activated'}`);
      loadUsers();
    } catch { toast.error('Failed'); }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this user?')) return;
    try { await api.deleteUser(id); toast.success('Deleted'); loadUsers(); }
    catch { toast.error('Failed'); }
  };

  const columns = [
    { key: 'full_name', header: 'Name', render: (u: User) => (
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 bg-primary-700 rounded-full flex items-center justify-center text-white text-sm font-medium">
          {u.full_name.charAt(0).toUpperCase()}
        </div>
        <div>
          <p className="font-medium text-dark-100">{u.full_name}</p>
          <p className="text-xs text-dark-500">{u.email}</p>
        </div>
      </div>
    )},
    { key: 'is_admin', header: 'Role', render: (u: User) => (
      <span className={cn('badge', u.is_admin ? 'bg-purple-500/10 text-purple-400' : 'bg-dark-700 text-dark-300')}>
        {u.is_admin ? 'Admin' : 'User'}
      </span>
    )},
    { key: 'is_active', header: 'Status', render: (u: User) => (
      <button onClick={(e) => { e.stopPropagation(); handleToggleActive(u); }} className={cn('badge cursor-pointer', u.is_active ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400')}>
        {u.is_active ? 'Active' : 'Inactive'}
      </button>
    )},
    { key: 'last_login', header: 'Last Login', render: (u: User) => <span className="text-sm text-dark-400">{u.last_login ? formatDate(u.last_login) : 'Never'}</span> },
    { key: 'created_at', header: 'Created', render: (u: User) => <span className="text-sm text-dark-400">{formatDate(u.created_at)}</span> },
    { key: 'actions', header: '', render: (u: User) => (
      <button onClick={(e) => { e.stopPropagation(); handleDelete(u.id); }} className="p-1.5 rounded hover:bg-dark-700 text-dark-400 hover:text-red-400">
        <Trash2 className="w-4 h-4" />
      </button>
    )},
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Users</h1>
          <p className="text-dark-400 mt-1">Manage system users</p>
        </div>
        <button onClick={() => setShowCreate(true)} className="btn-primary flex items-center gap-2">
          <Plus className="w-4 h-4" /> Add User
        </button>
      </div>

      <DataTable columns={columns} data={users} loading={loading} emptyMessage="No users found" />

      <Modal isOpen={showCreate} onClose={() => setShowCreate(false)} title="Create User" size="md">
        <div className="space-y-4">
          <div>
            <label className="block text-sm text-dark-400 mb-1">Full Name</label>
            <input type="text" value={formData.full_name} onChange={e => setFormData(p => ({ ...p, full_name: e.target.value }))} className="input-field" placeholder="John Doe" />
          </div>
          <div>
            <label className="block text-sm text-dark-400 mb-1">Email</label>
            <input type="email" value={formData.email} onChange={e => setFormData(p => ({ ...p, email: e.target.value }))} className="input-field" placeholder="john@example.com" />
          </div>
          <div>
            <label className="block text-sm text-dark-400 mb-1">Password</label>
            <input type="password" value={formData.password} onChange={e => setFormData(p => ({ ...p, password: e.target.value }))} className="input-field" placeholder="Strong password" />
          </div>
          <label className="flex items-center gap-2 text-sm text-dark-300 cursor-pointer">
            <input type="checkbox" checked={formData.is_admin} onChange={e => setFormData(p => ({ ...p, is_admin: e.target.checked }))} className="rounded" />
            <Shield className="w-4 h-4" /> Admin privileges
          </label>
          <button onClick={handleCreate} disabled={saving || !formData.email || !formData.password || !formData.full_name} className="btn-primary w-full flex items-center justify-center gap-2">
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <UserPlus className="w-4 h-4" />}
            Create User
          </button>
        </div>
      </Modal>
    </div>
  );
}
