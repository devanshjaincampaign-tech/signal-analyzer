import React from 'react';
import { History, X, Play, Clock, CheckCircle2, AlertCircle, FileAudio, RotateCw } from 'lucide-react';
import { Job } from '../types/signal';

interface JobHistoryDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  jobs: Job[];
  activeJobId: string | null;
  onSelectJob: (job: Job) => void;
  onRefreshJobs: () => void;
  isLoading: boolean;
}

export const JobHistoryDrawer: React.FC<JobHistoryDrawerProps> = ({
  isOpen,
  onClose,
  jobs,
  activeJobId,
  onSelectJob,
  onRefreshJobs,
  isLoading,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-xs animate-fade-in">
      <div className="w-full max-w-md bg-[#101522] border-l border-white/10 h-full p-6 flex flex-col shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-white/10">
          <div className="flex items-center gap-2.5">
            <History className="w-5 h-5 text-cyan-400" />
            <h2 className="text-base font-mono font-bold text-white uppercase tracking-wider">
              Signal Ingestion History
            </h2>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={onRefreshJobs}
              disabled={isLoading}
              className="p-1.5 text-slate-400 hover:text-white rounded bg-slate-900 border border-white/5"
              title="Refresh Jobs"
            >
              <RotateCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={onClose}
              className="p-1.5 text-slate-400 hover:text-white rounded bg-slate-900 border border-white/5"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Jobs List */}
        <div className="flex-1 overflow-y-auto py-4 space-y-2.5 scrollbar-thin">
          {jobs.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-48 text-slate-500 font-mono text-xs text-center">
              <FileAudio className="w-8 h-8 mb-2 opacity-50" />
              <p>No Ingested Jobs Recorded</p>
              <p className="text-[11px] text-slate-600 mt-1">Upload a capture to start analyzing</p>
            </div>
          ) : (
            jobs.map((job) => {
              const isActive = job.job_id === activeJobId;
              return (
                <div
                  key={job.job_id}
                  onClick={() => onSelectJob(job)}
                  className={`cursor-pointer p-3.5 rounded-xl border transition-all ${
                    isActive
                      ? 'bg-slate-900 border-cyan-400/60 shadow-[0_0_15px_rgba(0,240,255,0.15)]'
                      : 'bg-slate-900/50 border-white/5 hover:border-white/20 hover:bg-slate-900/80'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-xs font-mono font-bold text-slate-200 truncate max-w-[220px]" title={job.filename}>
                      {job.filename}
                    </span>
                    <span
                      className={`px-2 py-0.5 text-[10px] font-mono font-bold rounded uppercase ${
                        job.status === 'completed'
                          ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                          : job.status === 'validated'
                          ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                          : job.status === 'error'
                          ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                          : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                      }`}
                    >
                      {job.status}
                    </span>
                  </div>

                  <div className="flex items-center justify-between text-[11px] font-mono text-slate-400">
                    <span>Format: {job.file_type.toUpperCase()}</span>
                    {job.metadata?.sample_rate && (
                      <span>{(job.metadata.sample_rate / 1e6).toFixed(2)} MS/s</span>
                    )}
                  </div>

                  {job.error_message && (
                    <div className="mt-2 text-[10px] font-mono text-rose-400 flex items-center gap-1 truncate">
                      <AlertCircle className="w-3 h-3 shrink-0" />
                      <span>{job.error_message}</span>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>

        {/* Footer */}
        <div className="pt-4 border-t border-white/10 text-center text-[11px] font-mono text-slate-500">
          Showing {jobs.length} recorded capture sessions
        </div>
      </div>
    </div>
  );
};
