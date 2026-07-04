'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { SystemStats } from '@/lib/types';
import StatsCard from '@/components/StatsCard';
import {
  FileText,
  FileCheck,
  Clock,
  HardDrive,
  Users,
  FileSearch,
  Webhook,
  TrendingUp,
  Activity,
  Layers,
  CheckCircle,
  AlertTriangle,
} from 'lucide-react';

export default function DashboardPage() {
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      const { data } = await api.getSystemStats();
      setStats(data);
    } catch (error) {
      console.error('Failed to load stats:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="card animate-pulse">
              <div className="h-20 bg-dark-800 rounded" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className="text-dark-400 mt-1">System overview and processing metrics</p>
        </div>
        <button onClick={loadStats} className="btn-secondary flex items-center gap-2">
          <Activity className="w-4 h-4" /> Refresh
        </button>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatsCard
          title="Total Documents"
          value={stats?.total_documents || 0}
          icon={FileText}
          color="blue"
          subtitle={`${stats?.documents_today || 0} today`}
        />
        <StatsCard
          title="Pages Processed"
          value={stats?.total_pages_processed || 0}
          icon={Layers}
          color="purple"
        />
        <StatsCard
          title="Extractions"
          value={stats?.total_extractions || 0}
          icon={FileCheck}
          color="green"
        />
        <StatsCard
          title="Success Rate"
          value={`${((stats?.success_rate || 0) * 100).toFixed(1)}%`}
          icon={TrendingUp}
          color="green"
        />
        <StatsCard
          title="Avg Processing Time"
          value={`${(stats?.avg_processing_time_seconds || 0).toFixed(1)}s`}
          icon={Clock}
          color="orange"
        />
        <StatsCard
          title="Queue Size"
          value={stats?.processing_queue_size || 0}
          icon={AlertTriangle}
          color={stats?.processing_queue_size ? 'orange' : 'green'}
        />
        <StatsCard
          title="Storage Used"
          value={`${(stats?.storage_used_mb || 0).toFixed(1)} MB`}
          icon={HardDrive}
          color="purple"
        />
        <StatsCard
          title="Active Users"
          value={stats?.active_users || 0}
          icon={Users}
          color="blue"
          subtitle={`${stats?.active_templates || 0} templates, ${stats?.active_webhooks || 0} webhooks`}
        />
      </div>

      {/* Quick Actions */}
      <div className="card">
        <h2 className="text-lg font-semibold text-white mb-4">Quick Actions</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <a href="/dashboard/documents" className="flex flex-col items-center gap-2 p-4 rounded-xl bg-dark-800 hover:bg-dark-700 transition-colors">
            <FileText className="w-8 h-8 text-primary-400" />
            <span className="text-sm text-dark-300">Upload Documents</span>
          </a>
          <a href="/dashboard/templates" className="flex flex-col items-center gap-2 p-4 rounded-xl bg-dark-800 hover:bg-dark-700 transition-colors">
            <FileSearch className="w-8 h-8 text-green-400" />
            <span className="text-sm text-dark-300">Manage Templates</span>
          </a>
          <a href="/dashboard/webhooks" className="flex flex-col items-center gap-2 p-4 rounded-xl bg-dark-800 hover:bg-dark-700 transition-colors">
            <Webhook className="w-8 h-8 text-orange-400" />
            <span className="text-sm text-dark-300">Configure Webhooks</span>
          </a>
          <a href="/dashboard/audit-logs" className="flex flex-col items-center gap-2 p-4 rounded-xl bg-dark-800 hover:bg-dark-700 transition-colors">
            <CheckCircle className="w-8 h-8 text-purple-400" />
            <span className="text-sm text-dark-300">View Audit Logs</span>
          </a>
        </div>
      </div>
    </div>
  );
}
