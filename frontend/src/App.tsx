import React, { useState, useEffect } from 'react';
import { 
  Activity, 
  Layers, 
  Target, 
  Binary, 
  AlertCircle
} from 'lucide-react';

import { Header } from './components/Header';
import { SpectrogramWaterfall } from './components/SpectrogramWaterfall';
import { SpectrumPSDView } from './components/SpectrumPSDView';
import { ConstellationView } from './components/ConstellationView';
import { ModulationCard } from './components/ModulationCard';
import { SymbolRateCard } from './components/SymbolRateCard';
import { BitstreamInspector } from './components/BitstreamInspector';
import { CaptureDropzone } from './components/CaptureDropzone';
import { SyntheticGeneratorModal } from './components/SyntheticGeneratorModal';
import { JobHistoryDrawer } from './components/JobHistoryDrawer';

import { 
  checkBackendHealth, 
  listJobs, 
  analyzeJob, 
  getJobResults, 
  generateSyntheticDemoSignal 
} from './services/api';
import type { Job, AnalysisResponse } from './types/signal';

const initialBpskPreset = generateSyntheticDemoSignal('BPSK', {
  snrDb: 24,
  sampleRate: 1_000_000,
  samplesPerSymbol: 16,
  numSymbols: 256,
});

export function App() {
  const [backendConnected, setBackendConnected] = useState<boolean>(false);
  const [activeJob, setActiveJob] = useState<Job | null>(initialBpskPreset.job);
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(initialBpskPreset.analysis);
  const [samplePoints, setSamplePoints] = useState<{ i: number[]; q: number[] } | undefined>(initialBpskPreset.samples);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<'dashboard' | 'spectral' | 'demod' | 'constellation'>('dashboard');

  // Modals
  const [isUploadOpen, setIsUploadOpen] = useState<boolean>(false);
  const [isGeneratorOpen, setIsGeneratorOpen] = useState<boolean>(false);
  const [isHistoryOpen, setIsHistoryOpen] = useState<boolean>(false);
  const [isLoadingJobs, setIsLoadingJobs] = useState<boolean>(false);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);

  // Initialize and check health
  useEffect(() => {
    const init = async () => {
      const isAlive = await checkBackendHealth();
      setBackendConnected(isAlive);

      if (isAlive) {
        try {
          const jobList = await listJobs();
          setJobs(jobList);
          if (jobList.length > 0) {
            const latest = jobList[0];
            setActiveJob(latest);
            // Try fetching existing results
            try {
              const res = await getJobResults(latest.job_id);
              if (res && res.length > 0) {
                const featuresRow = res.find((r) => r.stage === 'features');
                const symbolRow = res.find((r) => r.stage === 'symbol_rate');
                const classRow = res.find((r) => r.stage === 'classification');
                const demodRow = res.find((r) => r.stage === 'demod');
                const interRow = res.find((r) => r.stage === 'interleaving');

                setAnalysis({
                  job_id: latest.job_id,
                  features: featuresRow?.result_data,
                  symbol_rate: symbolRow?.result_data,
                  classification: classRow?.result_data,
                  demod: demodRow?.result_data,
                  interleaving: interRow?.result_data,
                });
              }
            } catch (e) {
              // Results not generated yet
            }
          }
        } catch (e) {
          console.error(e);
        }
      }
    };

    init();

    // Periodic health check
    const interval = setInterval(async () => {
      const alive = await checkBackendHealth();
      setBackendConnected(alive);
    }, 10000);

    return () => clearInterval(interval);
  }, []);

  const loadPreset = (type: 'BPSK' | 'FSK' | '16-QAM') => {
    const preset = generateSyntheticDemoSignal(type, {
      snrDb: 24,
      sampleRate: 1_000_000,
      samplesPerSymbol: 16,
      numSymbols: 256,
    });
    setActiveJob(preset.job);
    setAnalysis(preset.analysis);
    setSamplePoints(preset.samples);
    setErrorBanner(null);
  };

  const handleRunAnalysis = async () => {
    if (!activeJob) return;
    setIsAnalyzing(true);
    setErrorBanner(null);

    try {
      if (backendConnected && !activeJob.job_id.startsWith('synth-')) {
        const result = await analyzeJob(activeJob.job_id);
        setAnalysis(result);
        setActiveJob((prev) => (prev ? { ...prev, status: 'completed' } : null));
      } else {
        // Run simulation animation
        setTimeout(() => {
          loadPreset(
            activeJob.filename.includes('fsk') ? 'FSK' :
            activeJob.filename.includes('qam') ? '16-QAM' : 'BPSK'
          );
          setIsAnalyzing(false);
        }, 800);
        return;
      }
    } catch (err: any) {
      setErrorBanner(err.message || 'Analysis pipeline encountered an error');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleUploadSuccess = (newJob: Job) => {
    setActiveJob(newJob);
    setJobs((prev) => [newJob, ...prev]);
    setAnalysis(null);
    setSamplePoints(undefined);
    setErrorBanner(null);
  };

  const handleSelectHistoryJob = async (job: Job) => {
    setActiveJob(job);
    setIsHistoryOpen(false);
    setErrorBanner(null);
    setAnalysis(null);

    try {
      const results = await getJobResults(job.job_id);
      if (results && results.length > 0) {
        const featuresRow = results.find((r) => r.stage === 'features');
        const symbolRow = results.find((r) => r.stage === 'symbol_rate');
        const classRow = results.find((r) => r.stage === 'classification');
        const demodRow = results.find((r) => r.stage === 'demod');
        const interRow = results.find((r) => r.stage === 'interleaving');

        setAnalysis({
          job_id: job.job_id,
          features: featuresRow?.result_data,
          symbol_rate: symbolRow?.result_data,
          classification: classRow?.result_data,
          demod: demodRow?.result_data,
          interleaving: interRow?.result_data,
        });
      }
    } catch (e) {
      // Results not ready yet
    }
  };

  const sampleRate = analysis?.features?.sample_rate_used || activeJob?.metadata?.sample_rate || 1_000_000;

  return (
    <div className="min-h-screen bg-[#0a0d14] text-slate-100 flex flex-col font-sans">
      {/* Header Bar */}
      <Header
        backendConnected={backendConnected}
        activeJob={activeJob}
        onOpenUpload={() => setIsUploadOpen(true)}
        onOpenGenerator={() => setIsGeneratorOpen(true)}
        onOpenHistory={() => setIsHistoryOpen(true)}
        onLoadPreset={loadPreset}
        onRunAnalysis={handleRunAnalysis}
        isAnalyzing={isAnalyzing}
      />

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 lg:px-8 py-6 space-y-6">
        
        {/* Error notification banner */}
        {errorBanner && (
          <div className="p-3.5 rounded-xl bg-rose-950/40 border border-rose-500/50 text-rose-300 text-xs font-mono flex items-center justify-between shadow-lg">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
              <span>{errorBanner}</span>
            </div>
            <button
              onClick={() => setErrorBanner(null)}
              className="px-2 py-0.5 rounded bg-slate-900 border border-white/10 hover:text-white"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* View Navigation Tabs */}
        <div className="flex items-center justify-between border-b border-white/10 pb-2">
          <div className="flex items-center gap-2 bg-slate-900/80 p-1 rounded-xl border border-white/5 font-mono text-xs">
            <button
              onClick={() => setActiveTab('dashboard')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-semibold transition-all ${
                activeTab === 'dashboard'
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-[0_0_12px_rgba(0,240,255,0.2)]'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Activity className="w-3.5 h-3.5" />
              <span>DSP Dashboard</span>
            </button>
            <button
              onClick={() => setActiveTab('spectral')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-semibold transition-all ${
                activeTab === 'spectral'
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-[0_0_12px_rgba(0,240,255,0.2)]'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              <span>Spectrogram & PSD</span>
            </button>
            <button
              onClick={() => setActiveTab('constellation')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-semibold transition-all ${
                activeTab === 'constellation'
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-[0_0_12px_rgba(0,240,255,0.2)]'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Target className="w-3.5 h-3.5" />
              <span>Constellation (IQ)</span>
            </button>
            <button
              onClick={() => setActiveTab('demod')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-semibold transition-all ${
                activeTab === 'demod'
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-[0_0_12px_rgba(0,240,255,0.2)]'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Binary className="w-3.5 h-3.5" />
              <span>Bitstream & Deinterleaving</span>
            </button>
          </div>

          {/* Quick Capture Metadata readout */}
          {activeJob?.metadata && (
            <div className="hidden md:flex items-center gap-3 text-[11px] font-mono text-slate-400">
              <span>Samples: <strong className="text-slate-200">{activeJob.metadata.num_samples?.toLocaleString() ?? 'N/A'}</strong></span>
              <span>•</span>
              <span>Rate: <strong className="text-cyan-300">{(sampleRate / 1e6).toFixed(2)} MS/s</strong></span>
              <span>•</span>
              <span>Duration: <strong className="text-slate-200">{activeJob.metadata.duration_s ? `${(activeJob.metadata.duration_s * 1000).toFixed(1)} ms` : 'N/A'}</strong></span>
            </div>
          )}
        </div>

        {/* TAB 1: ALL-IN-ONE OVERVIEW DASHBOARD */}
        {activeTab === 'dashboard' && (
          <div className="space-y-6">
            {/* Top Row: Classification & Symbol Rate Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <ModulationCard classification={analysis?.classification || null} />
              <SymbolRateCard symbolRate={analysis?.symbol_rate || null} sampleRate={sampleRate} />
            </div>

            {/* Middle Row: Spectrogram Waterfall & Welch PSD */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <SpectrogramWaterfall
                spectrogram={analysis?.features?.spectrogram || null}
                sampleRate={sampleRate}
              />
              <SpectrumPSDView features={analysis?.features || null} />
            </div>

            {/* Bottom Row: Constellation & Bitstream Inspector */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-1">
                <ConstellationView
                  demod={analysis?.demod || null}
                  classification={analysis?.classification || null}
                  samplePoints={samplePoints}
                />
              </div>
              <div className="lg:col-span-2">
                <BitstreamInspector
                  demod={analysis?.demod || null}
                  interleaving={analysis?.interleaving || null}
                />
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: SPECTRAL DEEP DIVE */}
        {activeTab === 'spectral' && (
          <div className="space-y-6">
            <SpectrogramWaterfall
              spectrogram={analysis?.features?.spectrogram || null}
              sampleRate={sampleRate}
            />
            <SpectrumPSDView features={analysis?.features || null} />
          </div>
        )}

        {/* TAB 3: CONSTELLATION (I/Q) */}
        {activeTab === 'constellation' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-1">
              <ConstellationView
                demod={analysis?.demod || null}
                classification={analysis?.classification || null}
                samplePoints={samplePoints}
              />
            </div>
            <div className="lg:col-span-2 space-y-6">
              <ModulationCard classification={analysis?.classification || null} />
              <SymbolRateCard symbolRate={analysis?.symbol_rate || null} sampleRate={sampleRate} />
            </div>
          </div>
        )}

        {/* TAB 4: DEMODULATION & BITSTREAM */}
        {activeTab === 'demod' && (
          <div className="space-y-6">
            <BitstreamInspector
              demod={analysis?.demod || null}
              interleaving={analysis?.interleaving || null}
            />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <ModulationCard classification={analysis?.classification || null} />
              <SymbolRateCard symbolRate={analysis?.symbol_rate || null} sampleRate={sampleRate} />
            </div>
          </div>
        )}

      </main>

      {/* Footer */}
      <footer className="mt-auto border-t border-white/5 bg-[#090c14] py-4 px-4 lg:px-8 text-center text-xs font-mono text-slate-500">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>SIGNAL ANALYZER // RF-IQ-DSP SYSTEM</span>
          <span>FastAPI Backend • React 18 DSP Frontend • SigMF Standard</span>
        </div>
      </footer>

      {/* Modals & Drawers */}
      <CaptureDropzone
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onUploadSuccess={handleUploadSuccess}
      />

      <SyntheticGeneratorModal
        isOpen={isGeneratorOpen}
        onClose={() => setIsGeneratorOpen(false)}
        onLoadSyntheticSignal={(job, analysisRes, samples) => {
          setActiveJob(job);
          setAnalysis(analysisRes);
          setSamplePoints(samples);
          setErrorBanner(null);
        }}
      />

      <JobHistoryDrawer
        isOpen={isHistoryOpen}
        onClose={() => setIsHistoryOpen(false)}
        jobs={jobs}
        activeJobId={activeJob?.job_id || null}
        onSelectJob={handleSelectHistoryJob}
        onRefreshJobs={async () => {
          setIsLoadingJobs(true);
          try {
            const list = await listJobs();
            setJobs(list);
          } finally {
            setIsLoadingJobs(false);
          }
        }}
        isLoading={isLoadingJobs}
      />
    </div>
  );
}

export default App;
