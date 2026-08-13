'use client';

import React, { useEffect, useState } from 'react';
import {
  Activity,
  ArrowRight,
  BarChart3,
  CheckCircle,
  Clock,
  HelpCircle,
  Phone,
  RotateCw,
  Search,
  TrendingUp,
  XCircle,
} from 'lucide-react';
import Link from 'next/link';

interface CallRecord {
  call_id: string;
  user_id: string;
  name: string;
  duration_seconds: number;
  outcome: string;
  failure_reason: string | null;
  timestamp: string;
  channel: string;
}

interface CallStats {
  total_calls: number;
  successful_calls: number;
  failed_calls: number;
  success_rate: number;
  failure_reasons: Record<string, number>;
}

export default function DashboardPage() {
  const [stats, setStats] = useState<CallStats | null>(null);
  const [calls, setCalls] = useState<CallRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [autoRefresh, setAutoRefresh] = useState(true);

  const fetchData = async () => {
    try {
      setError(null);
      
      // Fetch stats
      const statsRes = await fetch('http://localhost:8383/stats');
      if (!statsRes.ok) throw new Error('Failed to fetch stats');
      const statsData = await statsRes.json();
      setStats(statsData);

      // Fetch calls
      const callsRes = await fetch('http://localhost:8383/calls');
      if (!callsRes.ok) throw new Error('Failed to fetch call log');
      const callsData = await callsRes.json();
      setCalls(callsData);
    } catch (err: any) {
      console.error(err);
      setError(err.message || 'Failed to connect to the backend server.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(fetchData, 3000);
    return () => clearInterval(interval);
  }, [autoRefresh]);

  const handleManualRefresh = () => {
    setLoading(true);
    fetchData();
  };

  const filteredCalls = calls.filter((call) =>
    call.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    call.call_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (call.failure_reason && call.failure_reason.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  const formatDuration = (seconds: number) => {
    if (seconds === 0) return '0s';
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return m > 0 ? `${m}m ${s}s` : `${s}s`;
  };

  const formatTimestamp = (isoString: string) => {
    try {
      const date = new Date(isoString);
      return date.toLocaleString('en-IN', {
        day: '2-digit',
        month: 'short',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: true,
      });
    } catch {
      return isoString;
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 md:p-12 font-sans selection:bg-purple-600 selection:text-white">
      {/* Background radial gradients for ambient glow */}
      <div className="absolute top-0 left-1/4 w-96 h-96 bg-purple-900/15 rounded-full blur-3xl -z-10 pointer-events-none" />
      <div className="absolute bottom-10 right-1/4 w-96 h-96 bg-indigo-900/15 rounded-full blur-3xl -z-10 pointer-events-none" />

      <div className="max-w-7xl mx-auto space-y-8">
        {/* Header section */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-800 pb-6">
          <div>
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-1 text-xs font-semibold bg-purple-500/10 text-purple-400 border border-purple-500/20 rounded-full flex items-center gap-1.5 animate-pulse">
                <span className="w-2 h-2 rounded-full bg-purple-400" /> Day 8 Analytics
              </span>
            </div>
            <h1 className="text-4xl font-extrabold tracking-tight bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent mt-2">
              Call Performance Dashboard
            </h1>
            <p className="text-slate-400 mt-1">
              Real-time session quality tracking and performance stats for Saathi.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Link
              href="/escalations"
              className="px-4 py-2 text-sm bg-slate-900 hover:bg-slate-800 border border-slate-800 rounded-xl transition duration-200 flex items-center gap-2 text-purple-400 font-medium"
            >
              Go to Escalations <ArrowRight className="w-4 h-4" />
            </Link>

            <button
              onClick={handleManualRefresh}
              disabled={loading}
              className="p-2.5 bg-slate-900 hover:bg-slate-800 border border-slate-800 rounded-xl transition duration-200 text-slate-300 disabled:opacity-50"
              title="Manual Refresh"
            >
              <RotateCw className={`w-5 h-5 ${loading ? 'animate-spin text-purple-400' : ''}`} />
            </button>

            <label className="flex items-center gap-2 bg-slate-900 border border-slate-800 px-4 py-2 rounded-xl text-sm font-medium text-slate-300 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                className="rounded border-slate-800 bg-slate-950 text-purple-600 focus:ring-purple-500/30 w-4 h-4 cursor-pointer"
              />
              Auto-refresh (3s)
            </label>
          </div>
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-4 rounded-2xl flex items-center gap-3">
            <XCircle className="w-6 h-6 flex-shrink-0" />
            <div>
              <p className="font-semibold">Connection Error</p>
              <p className="text-sm opacity-90">{error} Please verify that the Python backend agent is running.</p>
            </div>
          </div>
        )}

        {/* Call Stats Summary Cards */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {/* Total Calls */}
            <div className="relative group bg-slate-900/40 backdrop-blur-xl border border-slate-850 p-6 rounded-2xl transition duration-300 hover:border-slate-800">
              <div className="absolute top-4 right-4 bg-slate-800/60 p-2 rounded-xl">
                <Phone className="w-5 h-5 text-slate-400" />
              </div>
              <p className="text-sm font-semibold text-slate-400 uppercase tracking-wider">Total Calls</p>
              <p className="text-4xl font-extrabold text-white mt-4">{stats.total_calls}</p>
              <p className="text-xs text-slate-500 mt-2">Active & completed sessions</p>
            </div>

            {/* Success Calls */}
            <div className="relative group bg-slate-900/40 backdrop-blur-xl border border-slate-850 p-6 rounded-2xl transition duration-300 hover:border-slate-800">
              <div className="absolute top-4 right-4 bg-emerald-500/10 p-2 rounded-xl border border-emerald-500/20">
                <CheckCircle className="w-5 h-5 text-emerald-400" />
              </div>
              <p className="text-sm font-semibold text-slate-400 uppercase tracking-wider">Successful Calls</p>
              <p className="text-4xl font-extrabold text-emerald-400 mt-4">{stats.successful_calls}</p>
              <p className="text-xs text-slate-500 mt-2">Completed quiz or lookup</p>
            </div>

            {/* Failed Calls */}
            <div className="relative group bg-slate-900/40 backdrop-blur-xl border border-slate-850 p-6 rounded-2xl transition duration-300 hover:border-slate-800">
              <div className="absolute top-4 right-4 bg-rose-500/10 p-2 rounded-xl border border-rose-500/20">
                <XCircle className="w-5 h-5 text-rose-400" />
              </div>
              <p className="text-sm font-semibold text-slate-400 uppercase tracking-wider">Failed/Incomplete</p>
              <p className="text-4xl font-extrabold text-rose-400 mt-4">{stats.failed_calls}</p>
              <p className="text-xs text-slate-500 mt-2">Early hangup or handoff</p>
            </div>

            {/* Success Rate */}
            <div className="relative group bg-slate-900/40 backdrop-blur-xl border border-slate-850 p-6 rounded-2xl transition duration-300 hover:border-emerald-500/20">
              <div className="absolute top-4 right-4 bg-purple-500/10 p-2 rounded-xl border border-purple-500/20">
                <TrendingUp className="w-5 h-5 text-purple-400" />
              </div>
              <p className="text-sm font-semibold text-slate-400 uppercase tracking-wider">Success Rate</p>
              <div className="flex items-baseline gap-2 mt-4">
                <p className="text-4xl font-extrabold text-purple-300">{stats.success_rate}%</p>
              </div>
              
              {/* Simple inline progress bar */}
              <div className="w-full bg-slate-800 rounded-full h-1.5 mt-4 overflow-hidden">
                <div 
                  className="bg-gradient-to-r from-purple-500 to-emerald-400 h-1.5 rounded-full transition-all duration-500" 
                  style={{ width: `${stats.success_rate}%` }}
                />
              </div>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Recent Calls Log Table */}
          <div className="lg:col-span-2 bg-slate-900/30 border border-slate-900 rounded-3xl p-6 backdrop-blur-md space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <h2 className="text-xl font-bold flex items-center gap-2 text-slate-200">
                <Activity className="w-5 h-5 text-purple-400" /> Recent Sessions
              </h2>

              <div className="relative max-w-xs">
                <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                  <Search className="w-4 h-4" />
                </span>
                <input
                  type="text"
                  placeholder="Search by student name..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full bg-slate-950/80 border border-slate-800 rounded-xl py-2 pl-10 pr-4 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/20 transition duration-200"
                />
              </div>
            </div>

            <div className="overflow-x-auto rounded-xl border border-slate-900">
              <table className="w-full border-collapse text-left text-sm text-slate-300">
                <thead className="bg-slate-950/80 text-xs font-semibold uppercase tracking-wider text-slate-400 border-b border-slate-850">
                  <tr>
                    <th className="py-4 px-4">Caller / Room ID</th>
                    <th className="py-4 px-4">Channel</th>
                    <th className="py-4 px-4">Duration</th>
                    <th className="py-4 px-4">Outcome</th>
                    <th className="py-4 px-4">Timestamp</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-850">
                  {filteredCalls.length > 0 ? (
                    filteredCalls.map((call) => (
                      <tr 
                        key={call.call_id} 
                        className="hover:bg-slate-900/20 transition duration-150"
                      >
                        <td className="py-4 px-4 font-medium text-white">
                          <p>{call.name}</p>
                          <p className="text-xs text-slate-500 mt-0.5">Room ID: {call.call_id.substring(0, 12)}...</p>
                        </td>
                        <td className="py-4 px-4">
                          <span className={`px-2 py-0.5 rounded-full text-xs font-medium border ${
                            call.channel === 'SIP' 
                              ? 'bg-sky-500/10 text-sky-400 border-sky-500/20' 
                              : 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20'
                          }`}>
                            {call.channel}
                          </span>
                        </td>
                        <td className="py-4 px-4 font-mono flex items-center gap-1.5 mt-2.5">
                          <Clock className="w-3.5 h-3.5 text-slate-500" />
                          {formatDuration(call.duration_seconds)}
                        </td>
                        <td className="py-4 px-4">
                          <div className="flex flex-col gap-1">
                            <span className={`w-fit px-2.5 py-0.5 rounded-full text-xs font-semibold flex items-center gap-1 border ${
                              call.outcome === 'Success'
                                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/25'
                                : 'bg-rose-500/10 text-rose-400 border-rose-500/25'
                            }`}>
                              {call.outcome === 'Success' ? 'Success' : 'Failed'}
                            </span>
                            {call.outcome === 'Failure' && call.failure_reason && (
                              <span className="text-[11px] text-slate-500 italic">
                                Reason: {call.failure_reason}
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="py-4 px-4 text-xs text-slate-400">
                          {formatTimestamp(call.timestamp)}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={5} className="py-8 text-center text-slate-500">
                        {loading ? 'Fetching call records...' : 'No call logs match your query.'}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Failure Reasons Breakdown & Metrics Guidance */}
          <div className="space-y-6">
            {/* Failure Breakdown Card */}
            <div className="bg-slate-900/30 border border-slate-900 rounded-3xl p-6 backdrop-blur-md space-y-6">
              <h2 className="text-xl font-bold flex items-center gap-2 text-slate-200">
                <BarChart3 className="w-5 h-5 text-rose-400" /> Failure Breakdown
              </h2>

              <div className="space-y-4">
                {stats && Object.keys(stats.failure_reasons).length > 0 ? (
                  Object.entries(stats.failure_reasons).map(([reason, count]) => {
                    const percentage = stats.failed_calls > 0 
                      ? Math.round((count / stats.failed_calls) * 105 / 100) // normalized percentage estimation
                      : 0;

                    const displayPercentage = stats.failed_calls > 0
                      ? Math.round((count / stats.failed_calls) * 100)
                      : 0;

                    return (
                      <div key={reason} className="space-y-1.5">
                        <div className="flex justify-between text-sm">
                          <span className="font-medium text-slate-300 capitalize">
                            {reason === 'Incomplete' ? 'Incomplete / Left early' : reason}
                          </span>
                          <span className="text-slate-400 font-mono">
                            {count} ({displayPercentage}%)
                          </span>
                        </div>
                        <div className="w-full bg-slate-800/80 rounded-full h-2">
                          <div 
                            className={`h-2 rounded-full transition-all duration-300 ${
                              reason === 'Incomplete' ? 'bg-amber-500/80' : 'bg-rose-500/80'
                            }`}
                            style={{ width: `${displayPercentage}%` }}
                          />
                        </div>
                      </div>
                    );
                  })
                ) : (
                  <div className="py-4 text-center text-slate-500 text-sm">
                    No failures recorded. 100% success rate! 🌟
                  </div>
                )}
              </div>
            </div>

            {/* What is a Successful Call Guide */}
            <div className="bg-slate-900/30 border border-slate-900 rounded-3xl p-6 backdrop-blur-md space-y-4">
              <h2 className="text-lg font-bold flex items-center gap-2 text-slate-200">
                <HelpCircle className="w-5 h-5 text-purple-400" /> Success Definition
              </h2>
              <div className="text-sm text-slate-400 space-y-3 leading-relaxed">
                <p>
                  For <strong>Saathi (Learning & Literacy)</strong>, a call is tracked as <strong>Successful</strong> if:
                </p>
                <ul className="list-disc pl-5 space-y-1.5 text-xs text-slate-300">
                  <li>The learner launches and plays the trivia quiz game.</li>
                  <li>The learner performs a dictionary word lookup query.</li>
                </ul>
                <p className="text-xs">
                  If a session closes before any learning activities take place, it is automatically marked as <strong>Incomplete (Failed)</strong>. If the learner struggles repeatedly and triggers human escalation, the call is recorded as <strong>Upset/Struggled (Failed)</strong>.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
