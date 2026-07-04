'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { Template } from '@/lib/types';
import DataTable from '@/components/DataTable';
import Modal from '@/components/Modal';
import { formatDate, cn } from '@/lib/utils';
import toast from 'react-hot-toast';
import { Plus, Trash2, Edit3, FileSearch, Loader2 } from 'lucide-react';

export default function TemplatesPage() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [formData, setFormData] = useState({
    name: '', description: '', document_type: 'invoice',
    fields: [{ field_name: '', field_label: '', field_type: 'text', is_required: false, extraction_hint: '', order: 0 }],
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => { loadTemplates(); }, []);

  const loadTemplates = async () => {
    setLoading(true);
    try {
      const { data } = await api.listTemplates();
      setTemplates(data.templates);
    } catch { toast.error('Failed to load templates'); }
    finally { setLoading(false); }
  };

  const handleCreate = async () => {
    setSaving(true);
    try {
      await api.createTemplate(formData);
      toast.success('Template created');
      setShowCreate(false);
      setFormData({ name: '', description: '', document_type: 'invoice', fields: [{ field_name: '', field_label: '', field_type: 'text', is_required: false, extraction_hint: '', order: 0 }] });
      loadTemplates();
    } catch (e: any) { toast.error(e.response?.data?.detail || 'Failed to create template'); }
    finally { setSaving(false); }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this template?')) return;
    try { await api.deleteTemplate(id); toast.success('Deleted'); loadTemplates(); }
    catch { toast.error('Failed to delete'); }
  };

  const addField = () => {
    setFormData(prev => ({
      ...prev,
      fields: [...prev.fields, { field_name: '', field_label: '', field_type: 'text', is_required: false, extraction_hint: '', order: prev.fields.length }],
    }));
  };

  const updateField = (index: number, key: string, value: any) => {
    setFormData(prev => {
      const fields = [...prev.fields];
      (fields[index] as any)[key] = value;
      return { ...prev, fields };
    });
  };

  const removeField = (index: number) => {
    setFormData(prev => ({ ...prev, fields: prev.fields.filter((_, i) => i !== index) }));
  };

  const columns = [
    { key: 'name', header: 'Name', render: (t: Template) => <span className="font-medium text-dark-100">{t.name}</span> },
    { key: 'document_type', header: 'Doc Type', render: (t: Template) => <span className="badge bg-dark-700 text-dark-300">{t.document_type}</span> },
    { key: 'fields', header: 'Fields', render: (t: Template) => <span>{t.fields.length}</span> },
    { key: 'is_active', header: 'Status', render: (t: Template) => <span className={cn('badge', t.is_active ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400')}>{t.is_active ? 'Active' : 'Inactive'}</span> },
    { key: 'version', header: 'Version', render: (t: Template) => <span>v{t.version}</span> },
    { key: 'created_at', header: 'Created', render: (t: Template) => <span className="text-sm text-dark-400">{formatDate(t.created_at)}</span> },
    { key: 'actions', header: '', render: (t: Template) => (
      <button onClick={(e) => { e.stopPropagation(); handleDelete(t.id); }} className="p-1.5 rounded hover:bg-dark-700 text-dark-400 hover:text-red-400">
        <Trash2 className="w-4 h-4" />
      </button>
    )},
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Extraction Templates</h1>
          <p className="text-dark-400 mt-1">Define extraction rules for document types</p>
        </div>
        <button onClick={() => setShowCreate(true)} className="btn-primary flex items-center gap-2">
          <Plus className="w-4 h-4" /> New Template
        </button>
      </div>

      <DataTable columns={columns} data={templates} loading={loading} emptyMessage="No templates yet. Create your first template!" />

      <Modal isOpen={showCreate} onClose={() => setShowCreate(false)} title="Create Template" size="xl">
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-dark-400 mb-1">Template Name</label>
              <input type="text" value={formData.name} onChange={e => setFormData(p => ({ ...p, name: e.target.value }))} className="input-field" placeholder="Invoice Template" />
            </div>
            <div>
              <label className="block text-sm text-dark-400 mb-1">Document Type</label>
              <select value={formData.document_type} onChange={e => setFormData(p => ({ ...p, document_type: e.target.value }))} className="input-field">
                {['invoice', 'receipt', 'contract', 'resume', 'form', 'report', 'letter', 'id_document', 'other'].map(t => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>
          </div>
          <div>
            <label className="block text-sm text-dark-400 mb-1">Description</label>
            <textarea value={formData.description} onChange={e => setFormData(p => ({ ...p, description: e.target.value }))} className="input-field" rows={2} placeholder="Template description..." />
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm text-dark-400 font-medium">Fields</label>
              <button onClick={addField} className="text-sm text-primary-400 hover:text-primary-300">+ Add Field</button>
            </div>
            <div className="space-y-3">
              {formData.fields.map((field, i) => (
                <div key={i} className="grid grid-cols-12 gap-2 items-end bg-dark-800 p-3 rounded-lg">
                  <div className="col-span-3">
                    <label className="block text-xs text-dark-500 mb-1">Name</label>
                    <input type="text" value={field.field_name} onChange={e => updateField(i, 'field_name', e.target.value)} className="input-field py-1.5 text-sm" placeholder="invoice_number" />
                  </div>
                  <div className="col-span-3">
                    <label className="block text-xs text-dark-500 mb-1">Label</label>
                    <input type="text" value={field.field_label} onChange={e => updateField(i, 'field_label', e.target.value)} className="input-field py-1.5 text-sm" placeholder="Invoice Number" />
                  </div>
                  <div className="col-span-2">
                    <label className="block text-xs text-dark-500 mb-1">Type</label>
                    <select value={field.field_type} onChange={e => updateField(i, 'field_type', e.target.value)} className="input-field py-1.5 text-sm">
                      {['text', 'number', 'date', 'currency', 'email', 'phone', 'address', 'boolean'].map(t => <option key={t} value={t}>{t}</option>)}
                    </select>
                  </div>
                  <div className="col-span-3">
                    <label className="block text-xs text-dark-500 mb-1">Extraction Hint</label>
                    <input type="text" value={field.extraction_hint} onChange={e => updateField(i, 'extraction_hint', e.target.value)} className="input-field py-1.5 text-sm" placeholder="Regex or hint" />
                  </div>
                  <div className="col-span-1 flex items-center gap-1">
                    <label className="flex items-center gap-1 text-xs text-dark-500">
                      <input type="checkbox" checked={field.is_required} onChange={e => updateField(i, 'is_required', e.target.checked)} className="rounded" />
                      Req
                    </label>
                    <button onClick={() => removeField(i)} className="p-1 text-dark-400 hover:text-red-400"><Trash2 className="w-3.5 h-3.5" /></button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <button onClick={handleCreate} disabled={saving || !formData.name} className="btn-primary w-full flex items-center justify-center gap-2">
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileSearch className="w-4 h-4" />}
            Create Template
          </button>
        </div>
      </Modal>
    </div>
  );
}
