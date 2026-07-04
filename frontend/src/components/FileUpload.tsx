'use client';

import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, File, X, Loader2 } from 'lucide-react';
import { cn, formatBytes } from '@/lib/utils';
import { api } from '@/lib/api';
import toast from 'react-hot-toast';

interface FileUploadProps {
  onUploadComplete?: () => void;
  autoProcess?: boolean;
}

export default function FileUpload({ onUploadComplete, autoProcess = false }: FileUploadProps) {
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [tags, setTags] = useState('');
  const [notes, setNotes] = useState('');

  const onDrop = useCallback((acceptedFiles: File[]) => {
    setFiles((prev) => [...prev, ...acceptedFiles]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'text/csv': ['.csv'],
      'image/*': ['.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.webp'],
      'text/html': ['.html'],
    },
    maxSize: 100 * 1024 * 1024,
  });

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleUpload = async () => {
    if (files.length === 0) return;
    setUploading(true);

    let successCount = 0;
    for (const file of files) {
      try {
        await api.uploadDocument(file, {
          tags: tags || undefined,
          notes: notes || undefined,
          autoProcess,
        });
        successCount++;
      } catch (error: any) {
        toast.error(`Failed to upload ${file.name}: ${error.response?.data?.detail || 'Unknown error'}`);
      }
    }

    if (successCount > 0) {
      toast.success(`${successCount} document(s) uploaded successfully`);
      setFiles([]);
      setTags('');
      setNotes('');
      onUploadComplete?.();
    }
    setUploading(false);
  };

  return (
    <div className="space-y-4">
      {/* Dropzone */}
      <div
        {...getRootProps()}
        className={cn(
          'border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all',
          isDragActive
            ? 'border-primary-500 bg-primary-500/5'
            : 'border-dark-600 hover:border-dark-500 hover:bg-dark-800/50'
        )}
      >
        <input {...getInputProps()} />
        <Upload className="w-10 h-10 text-dark-400 mx-auto mb-3" />
        <p className="text-dark-300 font-medium">
          {isDragActive ? 'Drop files here...' : 'Drag & drop files here, or click to browse'}
        </p>
        <p className="text-dark-500 text-sm mt-1">
          PDF, DOCX, XLSX, CSV, Images (max 100MB)
        </p>
      </div>

      {/* File list */}
      {files.length > 0 && (
        <div className="space-y-2">
          {files.map((file, index) => (
            <div key={index} className="flex items-center justify-between bg-dark-800 rounded-lg px-4 py-3">
              <div className="flex items-center gap-3">
                <File className="w-5 h-5 text-primary-400" />
                <div>
                  <p className="text-sm text-dark-200 font-medium">{file.name}</p>
                  <p className="text-xs text-dark-500">{formatBytes(file.size)}</p>
                </div>
              </div>
              <button onClick={() => removeFile(index)} className="p-1 hover:bg-dark-700 rounded">
                <X className="w-4 h-4 text-dark-400" />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Options */}
      {files.length > 0 && (
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm text-dark-400 mb-1">Tags (comma-separated)</label>
            <input
              type="text"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              className="input-field"
              placeholder="invoice, 2024, vendor"
            />
          </div>
          <div>
            <label className="block text-sm text-dark-400 mb-1">Notes</label>
            <input
              type="text"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="input-field"
              placeholder="Optional notes..."
            />
          </div>
        </div>
      )}

      {/* Upload button */}
      {files.length > 0 && (
        <button
          onClick={handleUpload}
          disabled={uploading}
          className="btn-primary w-full flex items-center justify-center gap-2 py-3"
        >
          {uploading ? (
            <><Loader2 className="w-5 h-5 animate-spin" /> Uploading...</>
          ) : (
            <><Upload className="w-5 h-5" /> Upload {files.length} file(s)</>
          )}
        </button>
      )}
    </div>
  );
}
