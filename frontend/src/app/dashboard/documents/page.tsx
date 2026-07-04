'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { Document, DocumentListResponse } from '@/lib/types';
import DataTable from '@/components/DataTable';
import Modal from '@/components/Modal';
import FileUpload from '@/components/FileUpload';
import { formatBytes, formatDate, getStatusColor, cn } from '@/lib/utils';
import toast from 'react-hot-toast';
import {
  Plus,
  Search,
  Filter,
  Play,
  Trash2,
  Download,
  RefreshCw,
  Eye,
  Archive,
  Loader2,
} from 'lucide-react';

export default function DocumentsPage() {
  const router = useRouter();
  const [documents, setDocuments] = useState<Document[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [showUpload, setShowUpload] = useState(false);
  const [processing, setProcessing] = useState<string | null>(null);

  useEffect(() => {
    loadDocuments();
  }, [page, statusFilter]);

  const loadDocuments = async () => {
    setLoading(true);
    try {
      const params: Record<string, any> = { page, per_page: 20 };
      if (statusFilter) params.status = statusFilter;
      if (search) params.search = search;
      const { data } = await api.listDocuments(params);
      setDocuments(data.documents);
      setTotal(data.total);
    } catch (error) {
      toast.error('Failed to load documents');
    } finally {
      setLoading(false);
    }
  };

  const handleProcess = async (id: string) => {
    setProcessing(id);
    try {
      await api.processDocumentSync(id, { extraction_method: 'auto' });
      toast.success('Document processed successfully');
      loadDocuments();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Processing failed');
    } finally {
      setProcessing(null);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this document?')) return;
    try {
      await api.deleteDocument(id);
      toast.success('Document deleted');
      loadDocuments();
    } catch (error) {
      toast.error('Failed to delete document');
    }
  };

  const columns = [
    {
      key: 'original_filename',
      header: 'Document',
      render: (doc: Document) => (
        <div>
          <p className="font-medium text-dark-100 truncate max-w-[200px]">{doc.original_filename}</p>
          <p className="text-xs text-dark-500">{formatBytes(doc.file_size)}</p>
        </div>
      ),
    },
    {
      key: 'document_type',
      header: 'Type',
      render: (doc: Document) => (
        <span className="badge bg-dark-700 text-dark-300">
          {doc.document_type || 'Unclassified'}
        </span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (doc: Document) => (
        <span className={cn('badge', getStatusColor(doc.status))}>
          {doc.status}
        </span>
      ),
    },
    {
      key: 'confidence',
      header: 'Confidence',
      render: (doc: Document) => (
        doc.classification_confidence
          ? <span className="text-sm">{(doc.classification_confidence * 100).toFixed(0)}%</span>
          : <span className="text-dark-500">-</span>
      ),
    },
    {
      key: 'created_at',
      header: 'Uploaded',
      render: (doc: Document) => (
        <span className="text-sm text-dark-400">{formatDate(doc.created_at)}</span>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (doc: Document) => (
        <div className="flex items-center gap-1">
          <button
            onClick={(e) => { e.stopPropagation(); router.push(`/dashboard/documents/${doc.id}`); }}
            className="p-1.5 rounded hover:bg-dark-700 text-dark-400 hover:text-primary-400"
            title="View"
          >
            <Eye className="w-4 h-4" />
          </button>
          {(doc.status === 'uploaded' || doc.status === 'failed') && (
            <button
              onClick={(e) => { e.stopPropagation(); handleProcess(doc.id); }}
              className="p-1.5 rounded hover:bg-dark-700 text-dark-400 hover:text-green-400"
              title="Process"
              disabled={processing === doc.id}
            >
              {processing === doc.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            </button>
          )}
          <button
            onClick={(e) => { e.stopPropagation(); handleDelete(doc.id); }}
            className="p-1.5 rounded hover:bg-dark-700 text-dark-400 hover:text-red-400"
            title="Delete"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Documents</h1>
          <p className="text-dark-400 mt-1">{total} documents total</p>
        </div>
        <button onClick={() => setShowUpload(true)} className="btn-primary flex items-center gap-2">
          <Plus className="w-4 h-4" /> Upload Documents
        </button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-dark-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && loadDocuments()}
            className="input-field pl-10"
            placeholder="Search documents..."
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="input-field w-40"
        >
          <option value="">All Status</option>
          <option value="uploaded">Uploaded</option>
          <option value="processing">Processing</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
        </select>
        <button onClick={loadDocuments} className="btn-secondary flex items-center gap-2">
          <RefreshCw className="w-4 h-4" /> Refresh
        </button>
      </div>

      {/* Table */}
      <DataTable
        columns={columns}
        data={documents}
        loading={loading}
        onRowClick={(doc) => router.push(`/dashboard/documents/${doc.id}`)}
        emptyMessage="No documents found. Upload your first document!"
      />

      {/* Pagination */}
      {total > 20 && (
        <div className="flex items-center justify-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="btn-secondary"
          >
            Previous
          </button>
          <span className="text-dark-400 text-sm">Page {page} of {Math.ceil(total / 20)}</span>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={page >= Math.ceil(total / 20)}
            className="btn-secondary"
          >
            Next
          </button>
        </div>
      )}

      {/* Upload Modal */}
      <Modal isOpen={showUpload} onClose={() => setShowUpload(false)} title="Upload Documents" size="lg">
        <FileUpload
          autoProcess={false}
          onUploadComplete={() => {
            setShowUpload(false);
            loadDocuments();
          }}
        />
      </Modal>
    </div>
  );
}
