'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { AuditLog } from '@/lib/types';
import DataTable from '@/components/DataTable';
import { formatDate } from '@/lib/utils';
import toast from 'react-hot-toast';
import { RefreshCw, Filter } from 'lucide-react';

export default function AuditLogsPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [actionFilter, setActionFilter] = useState('');
  const [resourceFilter, setResourceFilter] = useState('');

  useEffect(() => { loadLogs(); }, [page, actionFilter, resourceFilter]);

  const loadLogs = async () => {
    setLoading(true);
    try {
      const params: Record<string, any> = { page, per_page: 50 };
      if (actionFilter) params.action = actionFilter;
      if (resourceFilter) params.resource_type = resourceFilter;
      const { data } = await api.getAuditLogs(params);
      setLogs(data.logs);
      setTotal(data.total);
    } catch { toast.error('Failed to load audit logs'); }
    finally { setLoading(false); }
  };

  const columns = [
    { key: 'created_at', header: 'Time', render: (l: AuditLog) => <span className="text-sm text-dark-400">{formatDate(l.created_at)}</span> },
    { key: 'action', header: 'Action', render: (l: AuditLog) => <span className="badge bg-dark-700 text-dark-300 font-mono text-xs">{l.action}</span> },
    { key: 'resource_type', header: 'Resource', render: (l: AuditLog) => <span className="text-sm">{l.resource_type}</span> },
    { key: 'resource_id', header: 'Resource ID', render: (l: AuditLog) => <span className="text-xs text-dark-500 font-mono">{l.resource_id ? l.resource_id.slice(0, 8) + '...' : '-'}</span> },
    { key: 'ip_address', header: 'IP', render: (l: AuditLog) => <span className="text-sm text-dark-400">{l.ip_address || '-'}</span> },
    { key: 'details', header: 'Details', render: (l: AuditLog) => (
      <span className="text-xs text-dark-500 truncate max-w-[200px] block">
        {l.details ? JSON.stringify(l.details).slice(0, 50) : '-'}
      </span>
    )},
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Audit Logs</h1>
          <p className="text-dark-400 mt-1">{total} log entries</p>
        </div>
        <button onClick={loadLogs} className="btn-secondary flex items-center gap-2">
          <RefreshCw className="w-4 h-4" /> Refresh
        </button>
      </div>

      <div className="flex items-center gap-3">
        <select value={actionFilter} onChange={e => { setActionFilter(e.target.value); setPage(1); }} className="input-field w-48">
          <option value="">All Actions</option>
          <option value="user.login">Login</option>
          <option value="document.upload">Upload</option>
          <option value="document.process">Process</option>
          <option value="document.delete">Delete</option>
          <option value="extraction.validate">Validate</option>
          <option value="template.create">Template Create</option>
          <option value="webhook.create">Webhook Create</option>
        </select>
        <select value={resourceFilter} onChange={e => { setResourceFilter(e.target.value); setPage(1); }} className="input-field w-40">
          <option value="">All Resources</option>
          <option value="document">Document</option>
          <option value="user">User</option>
          <option value="template">Template</option>
          <option value="webhook">Webhook</option>
          <option value="extraction">Extraction</option>
        </select>
      </div>

      <DataTable columns={columns} data={logs} loading={loading} emptyMessage="No audit logs found" />

      {total > 50 && (
        <div className="flex items-center justify-center gap-2">
          <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="btn-secondary">Previous</button>
          <span className="text-dark-400 text-sm">Page {page} of {Math.ceil(total / 50)}</span>
          <button onClick={() => setPage(p => p + 1)} disabled={page >= Math.ceil(total / 50)} className="btn-secondary">Next</button>
        </div>
      )}
    </div>
  );
}
