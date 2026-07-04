'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { Document, ExtractionResult } from '@/lib/types';
import { formatBytes, formatDate, getStatusColor, getConfidenceColor, cn } from '@/lib/utils';
import toast from 'react-hot-toast';
import {
  ArrowLeft,
  Play,
  Download,
  Trash2,
  CheckCircle,
  FileText,
  Loader2,
  Edit3,
  Save,
  X,
  Table,
  Copy,
} from 'lucide-react';

export default function DocumentDetailPage() {
  const params = useParams();
  const router = useRouter();
  const [doc, setDoc] = useState<Document | null>(null);
  const [extractions, setExtractions] = useState<ExtractionResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [editingField, setEditingField] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');

  const docId = params.id as string;

  useEffect(() => {
    loadDocument();
  }, [docId]);

  const loadDocument = async () => {
    setLoading(true);
    try {
      const { data } = await api.getDocument(docId);
      setDoc(data);
      if (data.status === 'completed') {
        const { data: extData } = await api.getDocumentExtractions(docId);
        setExtractions(extData);
      }
    } catch (error) {
      toast.error('Failed to load document');
    } finally {
      setLoading(false);
    }
  };

  const handleProcess = async () => {
    setProcessing(true);
    try {
      await api.processDocumentSync(docId, { extraction_method: 'auto' });
      toast.success('Document processed!');
      loadDocument();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Processing failed');
    } finally {
      setProcessing(false);
    }
  };

  const handleCorrectField = async (fieldId: string, value: string) => {
    try {
      await api.correctFields([{ field_id: fieldId, corrected_value: value }]);
      toast.success('Field corrected');
      setEditingField(null);
      loadDocument();
    } catch (error) {
      toast.error('Failed to correct field');
    }
  };

  const handleValidate = async (extractionId: string) => {
    try {
      await api.validateExtraction(extractionId);
      toast.success('Extraction validated!');
      loadDocument();
    } catch (error) {
      toast.error('Failed to validate');
    }
  };

  const handleExport = async (extractionId: string, format: string) => {
    try {
      const { data } = await api.exportExtraction(extractionId, format);
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `extraction_${extractionId}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      toast.error('Export failed');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
      </div>
    );
  }

  if (!doc) return <p className="text-dark-400">Document not found</p>;

  const latestExtraction = extractions[0];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <button onClick={() => router.back()} className="p-2 rounded-lg hover:bg-dark-800 text-dark-400">
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div className="flex-1">
          <h1 className="text-xl font-bold text-white flex items-center gap-3">
            <FileText className="w-6 h-6 text-primary-400" />
            {doc.original_filename}
          </h1>
          <div className="flex items-center gap-3 mt-1">
            <span className={cn('badge', getStatusColor(doc.status))}>{doc.status}</span>
            {doc.document_type && (
              <span className="badge bg-dark-700 text-dark-300">{doc.document_type}</span>
            )}
            <span className="text-sm text-dark-500">{formatBytes(doc.file_size)}</span>
            <span className="text-sm text-dark-500">{formatDate(doc.created_at)}</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {(doc.status === 'uploaded' || doc.status === 'failed') && (
            <button onClick={handleProcess} disabled={processing} className="btn-primary flex items-center gap-2">
              {processing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
              Process
            </button>
          )}
          <button
            onClick={() => router.push(`/dashboard/documents`)}
            className="btn-secondary"
          >
            Back to List
          </button>
        </div>
      </div>

      {/* Document Info */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="card">
          <h3 className="text-sm font-medium text-dark-400 mb-3">Document Info</h3>
          <dl className="space-y-2">
            <div className="flex justify-between">
              <dt className="text-dark-500 text-sm">Type</dt>
              <dd className="text-dark-200 text-sm">{doc.mime_type}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-dark-500 text-sm">Pages</dt>
              <dd className="text-dark-200 text-sm">{doc.page_count || '-'}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-dark-500 text-sm">Classification</dt>
              <dd className="text-dark-200 text-sm">{doc.document_type || 'Pending'}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-dark-500 text-sm">Confidence</dt>
              <dd className={cn('text-sm', doc.classification_confidence ? getConfidenceColor(doc.classification_confidence) : 'text-dark-500')}>
                {doc.classification_confidence ? `${(doc.classification_confidence * 100).toFixed(0)}%` : '-'}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-dark-500 text-sm">Duplicate</dt>
              <dd className="text-dark-200 text-sm">{doc.is_duplicate ? 'Yes' : 'No'}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-dark-500 text-sm">Review Required</dt>
              <dd className="text-dark-200 text-sm">{doc.requires_review ? 'Yes' : 'No'}</dd>
            </div>
          </dl>
          {doc.tags && doc.tags.length > 0 && (
            <div className="mt-4">
              <p className="text-dark-500 text-sm mb-2">Tags</p>
              <div className="flex flex-wrap gap-1">
                {doc.tags.map((tag, i) => (
                  <span key={i} className="badge bg-dark-700 text-dark-300">{tag}</span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Extracted Fields */}
        <div className="lg:col-span-2">
          {latestExtraction ? (
            <div className="card">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-medium text-dark-400">
                  Extracted Data (v{latestExtraction.version})
                  {latestExtraction.validated && (
                    <span className="ml-2 badge bg-green-500/10 text-green-400">Validated</span>
                  )}
                </h3>
                <div className="flex items-center gap-2">
                  {!latestExtraction.validated && (
                    <button
                      onClick={() => handleValidate(latestExtraction.id)}
                      className="btn-primary text-sm py-1.5 px-3 flex items-center gap-1"
                    >
                      <CheckCircle className="w-3.5 h-3.5" /> Validate
                    </button>
                  )}
                  <button
                    onClick={() => handleExport(latestExtraction.id, 'json')}
                    className="btn-secondary text-sm py-1.5 px-3 flex items-center gap-1"
                  >
                    <Download className="w-3.5 h-3.5" /> Export
                  </button>
                </div>
              </div>

              {/* Fields */}
              <div className="space-y-2">
                {latestExtraction.fields.map((field) => (
                  <div key={field.id} className="flex items-center justify-between bg-dark-800 rounded-lg px-4 py-3">
                    <div className="flex-1">
                      <p className="text-xs text-dark-500 uppercase">{field.field_name}</p>
                      {editingField === field.id ? (
                        <div className="flex items-center gap-2 mt-1">
                          <input
                            type="text"
                            value={editValue}
                            onChange={(e) => setEditValue(e.target.value)}
                            className="input-field py-1 text-sm"
                            autoFocus
                          />
                          <button
                            onClick={() => handleCorrectField(field.id, editValue)}
                            className="p-1 text-green-400 hover:bg-dark-700 rounded"
                          >
                            <Save className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => setEditingField(null)}
                            className="p-1 text-dark-400 hover:bg-dark-700 rounded"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        </div>
                      ) : (
                        <p className="text-sm text-dark-200 mt-0.5">
                          {field.field_value || <span className="text-dark-500 italic">Empty</span>}
                          {field.is_corrected && (
                            <span className="ml-2 text-xs text-yellow-500">(corrected)</span>
                          )}
                        </p>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      {field.confidence !== null && field.confidence !== undefined && (
                        <span className={cn('text-xs', getConfidenceColor(field.confidence))}>
                          {(field.confidence * 100).toFixed(0)}%
                        </span>
                      )}
                      <span className="badge bg-dark-700 text-dark-400 text-xs">{field.field_type}</span>
                      <button
                        onClick={() => {
                          setEditingField(field.id);
                          setEditValue(field.field_value || '');
                        }}
                        className="p-1 rounded hover:bg-dark-700 text-dark-400 hover:text-primary-400"
                      >
                        <Edit3 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>

              {/* Tables */}
              {latestExtraction.tables.length > 0 && (
                <div className="mt-6">
                  <h4 className="text-sm font-medium text-dark-400 mb-3 flex items-center gap-2">
                    <Table className="w-4 h-4" /> Extracted Tables
                  </h4>
                  {latestExtraction.tables.map((table) => (
                    <div key={table.id} className="bg-dark-800 rounded-lg overflow-hidden mb-4">
                      {table.table_name && (
                        <p className="text-sm font-medium text-dark-300 px-4 py-2 bg-dark-750">{table.table_name}</p>
                      )}
                      <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                          {table.headers && (
                            <thead>
                              <tr className="border-b border-dark-700">
                                {table.headers.map((h, i) => (
                                  <th key={i} className="text-left px-3 py-2 text-dark-400 font-medium">{h}</th>
                                ))}
                              </tr>
                            </thead>
                          )}
                          <tbody>
                            {table.rows?.map((row, i) => (
                              <tr key={i} className="border-b border-dark-700/50">
                                {row.map((cell: any, j: number) => (
                                  <td key={j} className="px-3 py-2 text-dark-300">{cell}</td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="card flex flex-col items-center justify-center py-12">
              <FileText className="w-12 h-12 text-dark-600 mb-3" />
              <p className="text-dark-400">No extraction results yet</p>
              {(doc.status === 'uploaded' || doc.status === 'failed') && (
                <button onClick={handleProcess} disabled={processing} className="btn-primary mt-4 flex items-center gap-2">
                  {processing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                  Process Document
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
