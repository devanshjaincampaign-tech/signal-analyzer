import {
  Job,
  AnalysisResponse,
  StoredAnalysisStageRow,
  SpectralFeatures,
  SpectrogramData,
  SymbolRateResult,
  ClassificationResult,
  DemodResult,
  InterleavingResult,
} from '../types/signal';

const API_BASE = 'http://127.0.0.1:8000';

export async function checkBackendHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/health`, { method: 'GET' });
    if (!res.ok) return false;
    const data = await res.json();
    return data.status === 'ok';
  } catch (err) {
    return false;
  }
}

export async function listJobs(): Promise<Job[]> {
  const res = await fetch(`${API_BASE}/jobs`);
  if (!res.ok) {
    throw new Error(`Failed to fetch jobs: ${res.statusText}`);
  }
  return res.json();
}

export async function getJob(jobId: string): Promise<Job> {
  const res = await fetch(`${API_BASE}/jobs/${jobId}`);
  if (!res.ok) {
    throw new Error(`Failed to get job ${jobId}: ${res.statusText}`);
  }
  return res.json();
}

export async function uploadSignalFile(
  file: File,
  sidecarFile?: File | null,
  onProgress?: (percent: number) => void
): Promise<{ job_id: string; status: string }> {
  const formData = new FormData();
  formData.append('file', file);
  if (sidecarFile) {
    formData.append('sidecar', sidecarFile);
  }

  // Use XMLHttpRequest to get upload progress tracking
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${API_BASE}/jobs`);

    if (xhr.upload && onProgress) {
      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable) {
          const percent = Math.round((event.loaded / event.total) * 100);
          onProgress(percent);
        }
      };
    }

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const response = JSON.parse(xhr.responseText);
          resolve(response);
        } catch (e) {
          reject(new Error('Invalid JSON response from server'));
        }
      } else {
        try {
          const errData = JSON.parse(xhr.responseText);
          reject(new Error(errData.detail || `Upload failed with status ${xhr.status}`));
        } catch (e) {
          reject(new Error(`Upload failed with status ${xhr.status}`));
        }
      }
    };

    xhr.onerror = () => {
      reject(new Error('Network error during signal file upload'));
    };

    xhr.send(formData);
  });
}

export async function analyzeJob(jobId: string): Promise<AnalysisResponse> {
  const res = await fetch(`${API_BASE}/jobs/${jobId}/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorBody.detail || `Analysis failed with code ${res.status}`);
  }

  return res.json();
}

export async function getJobResults(jobId: string): Promise<StoredAnalysisStageRow[]> {
  const res = await fetch(`${API_BASE}/jobs/${jobId}/results`);
  if (!res.ok) {
    throw new Error(`Failed to fetch results: ${res.statusText}`);
  }
  return res.json();
}

// -------------------------------------------------------------
// Realistic Synthetic Signal Generator for Offline/Demo Studio
// -------------------------------------------------------------
export function generateSyntheticDemoSignal(
  type: 'BPSK' | 'FSK' | '16-QAM',
  options: {
    snrDb?: number;
    sampleRate?: number;
    samplesPerSymbol?: number;
    numSymbols?: number;
  } = {}
): {
  job: Job;
  analysis: AnalysisResponse;
  samples: { i: number[]; q: number[] };
} {
  const sampleRate = options.sampleRate || 1_000_000;
  const sps = options.samplesPerSymbol || 16;
  const numSymbols = options.numSymbols || 256;
  const numSamples = numSymbols * sps;
  const snr = options.snrDb ?? 25;
  const noiseSigma = Math.pow(10, -snr / 20) / Math.sqrt(2);

  const iArr: number[] = new Array(numSamples);
  const qArr: number[] = new Array(numSamples);
  const generatedBits: number[] = [];

  // Random bit generator
  for (let s = 0; s < numSymbols; s++) {
    const bit = Math.random() > 0.5 ? 1 : 0;
    generatedBits.push(bit);
  }

  let centerFreq = 120_000;
  let bandwidth = 62_500;
  let modClass: 'PSK' | 'FSK' | 'QAM' = 'PSK';
  let conf = 0.94;
  let demodResult: DemodResult;
  let iLevels: number[] = [];
  let qLevels: number[] = [];

  if (type === 'BPSK') {
    modClass = 'PSK';
    centerFreq = 150_000;
    bandwidth = Math.round(sampleRate / sps * 1.2);
    conf = 0.92;
    for (let s = 0; s < numSymbols; s++) {
      const bitVal = generatedBits[s];
      const symbolVal = bitVal === 1 ? 1.0 : -1.0;
      for (let k = 0; k < sps; k++) {
        const idx = s * sps + k;
        const nI = (Math.random() - 0.5) * 2 * noiseSigma;
        const nQ = (Math.random() - 0.5) * 2 * noiseSigma;
        iArr[idx] = symbolVal + nI;
        qArr[idx] = nQ;
      }
    }
    demodResult = {
      success: true,
      type: 'bits',
      bits: generatedBits,
      num_bits: generatedBits.length,
    };
  } else if (type === 'FSK') {
    modClass = 'FSK';
    centerFreq = 200_000;
    bandwidth = 110_000;
    conf = 0.88;
    const fDev = 40_000;
    let phase = 0;
    for (let s = 0; s < numSymbols; s++) {
      const bitVal = generatedBits[s];
      const freq = bitVal === 1 ? fDev : -fDev;
      const dPhi = (2 * Math.PI * freq) / sampleRate;
      for (let k = 0; k < sps; k++) {
        const idx = s * sps + k;
        phase += dPhi;
        const nI = (Math.random() - 0.5) * 2 * noiseSigma;
        const nQ = (Math.random() - 0.5) * 2 * noiseSigma;
        iArr[idx] = Math.cos(phase) + nI;
        qArr[idx] = Math.sin(phase) + nQ;
      }
    }
    demodResult = {
      success: true,
      type: 'bits',
      bits: generatedBits,
      num_bits: generatedBits.length,
    };
  } else {
    // 16-QAM
    modClass = 'QAM';
    centerFreq = 0;
    bandwidth = 85_000;
    conf = 0.95;
    const levels = [-1.0, -0.333, 0.333, 1.0];
    for (let s = 0; s < numSymbols; s++) {
      const iVal = levels[Math.floor(Math.random() * 4)];
      const qVal = levels[Math.floor(Math.random() * 4)];
      iLevels.push(iVal);
      qLevels.push(qVal);
      for (let k = 0; k < sps; k++) {
        const idx = s * sps + k;
        const nI = (Math.random() - 0.5) * 2 * noiseSigma;
        const nQ = (Math.random() - 0.5) * 2 * noiseSigma;
        iArr[idx] = iVal + nI;
        qArr[idx] = qVal + nQ;
      }
    }
    demodResult = {
      success: true,
      type: 'symbol_levels',
      i_levels: iLevels,
      q_levels: qLevels,
    };
  }

  // Generate Spectrogram 64x64 grid
  const nFreqs = 64;
  const nTimes = 64;
  const freqBins: number[] = [];
  const timeBins: number[] = [];
  const powerDbMatrix: number[][] = [];

  for (let f = 0; f < nFreqs; f++) {
    freqBins.push(-sampleRate / 2 + (f / nFreqs) * sampleRate);
  }
  for (let t = 0; t < nTimes; t++) {
    timeBins.push((t / nTimes) * (numSamples / sampleRate));
  }

  const centerIdx = Math.floor(nFreqs / 2 + (centerFreq / sampleRate) * nFreqs);
  const bwBins = Math.max(2, Math.floor((bandwidth / sampleRate) * nFreqs));

  for (let f = 0; f < nFreqs; f++) {
    const row: number[] = [];
    const dist = Math.abs(f - centerIdx);
    for (let t = 0; t < nTimes; t++) {
      let baseDb = -65 + (Math.random() - 0.5) * 4; // noise floor ~ -65 dB
      if (dist <= bwBins / 2) {
        // Active signal band
        baseDb = -18 + (Math.random() - 0.5) * 6; // ~ -18 dB
      } else if (dist <= bwBins) {
        baseDb = -35 + (Math.random() - 0.5) * 5;
      }
      row.push(Number(baseDb.toFixed(2)));
    }
    powerDbMatrix.push(row);
  }

  const mockJobId = `synth-${type.toLowerCase()}-${Date.now().toString(36)}`;

  const job: Job = {
    job_id: mockJobId,
    filename: `synthetic_${type.toLowerCase()}_capture.iq`,
    file_type: 'iq',
    status: 'completed',
    metadata: {
      sample_rate: sampleRate,
      num_samples: numSamples,
      duration_s: Number((numSamples / sampleRate).toFixed(4)),
      format: 'IQ Complex Float32',
      is_complex: true,
      channels: 2,
    },
    created_at: new Date().toISOString(),
  };

  const spectral: SpectralFeatures = {
    center_frequency_hz: centerFreq,
    bandwidth_hz: bandwidth,
    noise_floor_db: -64.2,
    peak_power_db: -14.8,
    sample_rate_used: sampleRate,
    sample_rate_was_assumed: false,
    spectrogram: {
      freq_bins: freqBins,
      time_bins: timeBins,
      power_db_matrix: powerDbMatrix,
    },
  };

  const symbolRate: SymbolRateResult = {
    samples_per_symbol: sps,
    symbol_rate_baud: sampleRate / sps,
    confidence: 0.96,
    method: 'spectral_peak_cyclostationary',
  };

  const candidateScores = [
    { label: modClass, score: conf },
    { label: modClass === 'PSK' ? 'FSK' : 'PSK', score: Number(((1 - conf) * 0.7).toFixed(3)) },
    { label: modClass === 'QAM' ? 'FSK' : 'QAM', score: Number(((1 - conf) * 0.3).toFixed(3)) },
  ];

  const classification: ClassificationResult = {
    modulation: modClass,
    confidence: conf,
    candidates: candidateScores,
    features_used: {
      applicable: true,
      envelope_variance: type === 'BPSK' ? 0.012 : type === 'FSK' ? 0.008 : 0.185,
      inst_freq_variance: type === 'FSK' ? 0.045 : 0.892,
      c42_cumulant: type === '16-QAM' ? 0.042 : 0.812,
    },
  };

  const interleaving: InterleavingResult = {
    success: type === 'BPSK',
    stride: type === 'BPSK' ? 8 : undefined,
    depth: type === 'BPSK' ? 16 : undefined,
    confidence: type === 'BPSK' ? 0.88 : undefined,
    reason: type === 'BPSK' ? undefined : 'No bitstream or periodic autocorrelation detected',
  };

  return {
    job,
    analysis: {
      job_id: mockJobId,
      features: spectral,
      symbol_rate: symbolRate,
      classification,
      demod: demodResult,
      interleaving,
    },
    samples: { i: iArr, q: qArr },
  };
}
