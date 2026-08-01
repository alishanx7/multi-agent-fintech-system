import React, { useMemo, useState } from 'react';
import {
  BarChart3,
  Building2,
  CircleDollarSign,
  FileDown,
  RefreshCw,
  Scale,
  Sparkles,
  TrendingUp,
} from 'lucide-react';

interface PostAnalysisOptionsProps {
  sessionId: string;
  onReset: () => void;
}

interface FinancialTelemetry {
  company_name?: string;
  gross_revenue?: number;
  total_debt_service?: number;
  net_operating_income?: number;
  calculated_dscr?: number;
}

interface BenchmarkPayload {
  dscr?: number;
  monthly_revenue?: number;
  benchmark?: {
    average_dscr?: number;
    average_monthly_revenue?: number;
  };
}

const API_BASE_URL = 'http://127.0.0.1:8000';

const formatCurrency = (value: number | undefined) =>
  new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(value ?? 0);

const formatNumber = (value: number | undefined, fractionDigits = 2) =>
  new Intl.NumberFormat('en-IN', { maximumFractionDigits: fractionDigits }).format(value ?? 0);

const trendLabel = (value: number, baseline: number) => {
  if (value > baseline) return { label: 'Above benchmark', tone: 'text-emerald-400 bg-emerald-500/15 border-emerald-500/30' };
  if (value < baseline) return { label: 'Below benchmark', tone: 'text-amber-300 bg-amber-500/15 border-amber-500/30' };
  return { label: 'At benchmark', tone: 'text-cyan-300 bg-cyan-500/15 border-cyan-500/30' };
};

export default function PostAnalysisOptions({ sessionId, onReset }: PostAnalysisOptionsProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [financialBreakdown, setFinancialBreakdown] = useState<FinancialTelemetry | null>(null);
  const [riskExplanation, setRiskExplanation] = useState<string>('');
  const [benchmarkData, setBenchmarkData] = useState<BenchmarkPayload | null>(null);

  const runAction = async (action: 'financial' | 'explain' | 'benchmark') => {
    setIsLoading(true);
    setError(null);

    try {
      const endpoint =
        action === 'financial'
          ? `/api/financial-breakdown/${sessionId}`
          : action === 'explain'
          ? `/api/explain-risk/${sessionId}`
          : `/api/benchmark/${sessionId}`;

      const response = await fetch(`${API_BASE_URL}${endpoint}`);
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail || 'Post-analysis request failed');
      }

      const payload = await response.json();
      if (action === 'financial') {
        setFinancialBreakdown(payload.financial_telemetry || {});
      } else if (action === 'explain') {
        setRiskExplanation(payload.explanation || '');
      } else {
        setBenchmarkData(payload || {});
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Unknown post-analysis error');
    } finally {
      setIsLoading(false);
    }
  };

  const downloadPdf = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/api/download-pdf/${sessionId}`);
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail || 'Failed to generate PDF');
      }

      const blob = await response.blob();
      const objectUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = objectUrl;
      link.download = `underwriting_${sessionId}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(objectUrl);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to generate PDF');
    } finally {
      setIsLoading(false);
    }
  };

  const benchmarkSummary = useMemo(() => {
    if (!benchmarkData?.benchmark) return null;
    const dscr = benchmarkData.dscr ?? 0;
    const avgDscr = benchmarkData.benchmark.average_dscr ?? 0;
    const revenue = benchmarkData.monthly_revenue ?? 0;
    const avgRevenue = benchmarkData.benchmark.average_monthly_revenue ?? 0;
    return {
      dscrTrend: trendLabel(dscr, avgDscr),
      revenueTrend: trendLabel(revenue, avgRevenue),
      dscrGap: dscr - avgDscr,
      revenueGap: revenue - avgRevenue,
    };
  }, [benchmarkData]);

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-950 p-4 space-y-4">
      <div className="flex items-center justify-between gap-3">
        <h4 className="text-xs font-bold uppercase tracking-wider text-cyan-300">Post-analysis intelligence</h4>
        <span className="text-[10px] font-mono text-slate-500">Session: {sessionId.slice(0, 8)}...</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        <button
          onClick={() => runAction('financial')}
          disabled={isLoading}
          className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs font-semibold text-slate-200 hover:border-cyan-500/50 disabled:opacity-60"
        >
          Financial Breakdown
        </button>
        <button
          onClick={() => runAction('explain')}
          disabled={isLoading}
          className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs font-semibold text-slate-200 hover:border-cyan-500/50 disabled:opacity-60"
        >
          Explain Risk
        </button>
        <button
          onClick={() => runAction('benchmark')}
          disabled={isLoading}
          className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs font-semibold text-slate-200 hover:border-cyan-500/50 disabled:opacity-60 flex items-center justify-center gap-1.5"
        >
          <BarChart3 className="h-3.5 w-3.5 text-cyan-400" />
          Benchmark
        </button>
        <button
          onClick={downloadPdf}
          disabled={isLoading}
          className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs font-semibold text-slate-200 hover:border-cyan-500/50 disabled:opacity-60 flex items-center justify-center gap-1.5"
        >
          <FileDown className="h-3.5 w-3.5 text-cyan-400" />
          Download Dossier PDF
        </button>
      </div>

      {isLoading && (
        <p className="text-xs text-cyan-300 flex items-center gap-2">
          <RefreshCw className="h-3.5 w-3.5 animate-spin" />
          Updating post-analysis insights...
        </p>
      )}
      {error && <p className="text-xs text-rose-300">{error}</p>}

      {financialBreakdown && (
        <div className="rounded-lg border border-slate-800 bg-slate-900 p-4 space-y-3">
          <p className="text-[10px] uppercase tracking-wider text-slate-400">Financial telemetry snapshot</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
            <div className="rounded-lg border border-slate-800 bg-slate-950 p-3">
              <p className="text-slate-400 flex items-center gap-1.5"><Building2 className="h-3.5 w-3.5 text-cyan-400" />Company</p>
              <p className="mt-1 text-slate-200 font-semibold">{financialBreakdown.company_name || 'N/A'}</p>
            </div>
            <div className="rounded-lg border border-slate-800 bg-slate-950 p-3">
              <p className="text-slate-400 flex items-center gap-1.5"><Scale className="h-3.5 w-3.5 text-cyan-400" />DSCR</p>
              <p className="mt-1 text-cyan-300 font-bold text-sm">{formatNumber(financialBreakdown.calculated_dscr)}</p>
            </div>
            <div className="rounded-lg border border-slate-800 bg-slate-950 p-3">
              <p className="text-slate-400 flex items-center gap-1.5"><CircleDollarSign className="h-3.5 w-3.5 text-cyan-400" />Gross revenue</p>
              <p className="mt-1 text-slate-200 font-semibold">{formatCurrency(financialBreakdown.gross_revenue)}</p>
            </div>
            <div className="rounded-lg border border-slate-800 bg-slate-950 p-3">
              <p className="text-slate-400 flex items-center gap-1.5"><TrendingUp className="h-3.5 w-3.5 text-cyan-400" />Net operating income</p>
              <p className="mt-1 text-slate-200 font-semibold">{formatCurrency(financialBreakdown.net_operating_income)}</p>
            </div>
          </div>
        </div>
      )}

      {riskExplanation && (
        <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
          <p className="mb-2 text-[10px] uppercase tracking-wider text-slate-400">Risk explanation</p>
          <p className="text-xs text-slate-200 leading-relaxed">{riskExplanation}</p>
        </div>
      )}

      {benchmarkData && benchmarkSummary && (
        <div className="rounded-lg border border-slate-800 bg-slate-900 p-4 space-y-3">
          <p className="text-[10px] uppercase tracking-wider text-slate-400">Benchmark comparison</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
            <div className="rounded-lg border border-slate-800 bg-slate-950 p-3 space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="text-slate-300 font-semibold">DSCR vs Market</span>
                <span className={`text-[10px] px-2 py-0.5 rounded-full border ${benchmarkSummary.dscrTrend.tone}`}>
                  {benchmarkSummary.dscrTrend.label}
                </span>
              </div>
              <p className="text-slate-400">
                Your DSCR: <span className="text-cyan-300 font-semibold">{formatNumber(benchmarkData.dscr)}</span>
              </p>
              <p className="text-slate-400">
                Benchmark: <span className="text-slate-200">{formatNumber(benchmarkData.benchmark?.average_dscr)}</span>
              </p>
              <p className="text-slate-400">
                Gap: <span className="text-slate-200">{formatNumber(benchmarkSummary.dscrGap)}</span>
              </p>
            </div>
            <div className="rounded-lg border border-slate-800 bg-slate-950 p-3 space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="text-slate-300 font-semibold">Revenue vs Market</span>
                <span className={`text-[10px] px-2 py-0.5 rounded-full border ${benchmarkSummary.revenueTrend.tone}`}>
                  {benchmarkSummary.revenueTrend.label}
                </span>
              </div>
              <p className="text-slate-400">
                Your revenue: <span className="text-cyan-300 font-semibold">{formatCurrency(benchmarkData.monthly_revenue)}</span>
              </p>
              <p className="text-slate-400">
                Benchmark: <span className="text-slate-200">{formatCurrency(benchmarkData.benchmark?.average_monthly_revenue)}</span>
              </p>
              <p className="text-slate-400">
                Gap: <span className="text-slate-200">{formatCurrency(benchmarkSummary.revenueGap)}</span>
              </p>
            </div>
          </div>
        </div>
      )}

      <div className="flex justify-end">
        <button
          onClick={onReset}
          className="rounded-full bg-cyan-500 px-4 py-2 text-xs font-bold text-slate-950 hover:bg-cyan-400 flex items-center gap-1.5"
        >
          <Sparkles className="h-3.5 w-3.5" />
          Start New Analysis
        </button>
      </div>
    </div>
  );
}
