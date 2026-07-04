'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { Webhook } from '@/lib/types';
import DataTable from '@/components/DataTable';
import Modal from '@/components/Modal';
import { formatDate, cn } from '@/lib/utils';
import toast from 'react-hot-toast';
import { Plus, Trash2, Send, Loader2, Webhook as WebhookIcon } from 'lucide-react';

const EVENTS = [
  'document.uploaded', 'document.processed', 'document.failed',
  'extraction.completed', 'extraction.validated',
];

export default function WebhooksPage() {
  const [webhooks, setWebhooks] = useState<Webhook[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [formData, setFormData] = useState({ name: '', url: '', secret: '', events: [] as string[] });
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState<string | null>(null);

  useEffect(() => { loadWebhooks(); }, []);

  const loadWebhooks = async () => {
    setLoading(true);
    try { const { data } = await api.listWebhooks(); setWebhooks(data.webhooks); }
    catch { toast.error('Failed to load webhooks'); }
    finally { setLoading(false); }
  };

  const handleCreate = async () => {
    setSaving(true);
    try {
      await api.createWebhook(formData);
      toast.success('Webhook created');
      setShowCreate(false);
      setFormData({ name: '', url: '', secret: '', events: [] });
      loadWebhooks();
    } catch (e: any) { toast.error(e.response?.data?.detail || 'Failed'); }
    finally { setSaving(false); }
  };

  const handleTest = async (id: string) => {
    setTesting(id);
    try {
      const { data } = await api.testWebhook(id);
      if (data.data?.success) toast.success('Webhook test successful!');
      else toast.error('Webhook test failed');
    } catch { toast.error('Test failed'); }
    finally { setTesting(null); }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this webhook?')) return;
    try { await api.deleteWebhook(id); toast.success('Deleted'); loadWebhooks(); }
    catch { toast.error('Failed'); }
  };

  const toggleEvent = (event: string) => {
    setFormData(prev => ({
      ...prev,
      events: prev.events.includes(event) ? prev.events.filter(e => e !== event) : [...prev.events, event],
    }));
  };

  const columns = [
    { key: 'name', header: 'Name', render: (w: Webhook) => <span className="font-medium text-dark-100">{w.name}</span> },
    { key: 'url', header: 'URL', render: (w: Webhook) => <span className="text-sm text-dark-400 truncate max-w-[200px] block">{w.url}</span> },
    { key: 'events', header: 'Events', render: (w: Webhook) => <span className="text-sm">{w.events.length} events</span> },
    { key: 'is_active', header: 'Status', render: (w: Webhook) => <span className={cn('badge', w.is_active ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400')}>{w.is_active ? 'Active' : 'Inactive'}</span> },
    { key: 'actions', header: '', render: (w: Webhook) => (
      <div className="flex items-center gap-1">
        <button onClick={(e) => { e.stopPropagation(); handleTest(w.id); }} disabled={testing === w.id} className="p-1.5 rounded hover:bg-dark-700 text-dark-400 hover:text-primary-400" title="Test">
          {testing === w.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
        </button>
        <button onClick={(e) => { e.stopPropagation(); handleDelete(w.id); }} className="p-1.5 rounded hover:bg-dark-700 text-dark-400 hover:text-red-400" title="Delete">
          <Trash2 className="w-4 h-4" />
        </button>
      </div>
    )},
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Webhooks</h1>
          <p className="text-dark-400 mt-1">Configure event notifications</p>
        </div>
        <button onClick={() => setShowCreate(true)} className="btn-primary flex items-center gap-2">
          <Plus className="w-4 h-4" /> New Webhook
        </button>
      </div>

      <DataTable columns={columns} data={webhooks} loading={loading} emptyMessage="No webhooks configured" />

      <Modal isOpen={showCreate} onClose={() => setShowCreate(false)} title="Create Webhook" size="md">
        <div className="space-y-4">
          <div>
            <label className="block text-sm text-dark-400 mb-1">Name</label>
            <input type="text" value={formData.name} onChange={e => setFormData(p => ({ ...p, name: e.target.value }))} className="input-field" placeholder="My Webhook" />
          </div>
          <div>
            <label className="block text-sm text-dark-400 mb-1">URL</label>
            <input type="url" value={formData.url} onChange={e => setFormData(p => ({ ...p, url: e.target.value }))} className="input-field" placeholder="https://example.com/webhook" />
          </div>
          <div>
            <label className="block text-sm text-dark-400 mb-1">Secret (optional)</label>
            <input type="text" value={formData.secret} onChange={e => setFormData(p => ({ ...p, secret: e.target.value }))} className="input-field" placeholder="Signing secret" />
          </div>
          <div>
            <label className="block text-sm text-dark-400 mb-2">Events</label>
            <div className="space-y-2">
              {EVENTS.map(event => (
                <label key={event} className="flex items-center gap-2 text-sm text-dark-300 cursor-pointer">
                  <input type="checkbox" checked={formData.events.includes(event)} onChange={() => toggleEvent(event)} className="rounded" />
                  {event}
                </label>
              ))}
            </div>
          </div>
          <button onClick={handleCreate} disabled={saving || !formData.name || !formData.url || formData.events.length === 0} className="btn-primary w-full flex items-center justify-center gap-2">
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <WebhookIcon className="w-4 h-4" />}
            Create Webhook
          </button>
        </div>
      </Modal>
    </div>
  );
}
