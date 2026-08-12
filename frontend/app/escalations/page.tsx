'use client';

import React, { useEffect, useState } from 'react';
import {
  AlertTriangle,
  BookOpen,
  CheckCircle,
  Clock,
  FileText,
  Phone,
  RefreshCw,
  Search,
  User,
} from 'lucide-react';

interface Ticket {
  ticket_id: string;
  user_id: string;
  name: string;
  reason: string;
  topics_covered: string;
  urgency: string;
  follow_up_method: string;
  status: string;
  timestamp: string;
}

export default function EscalationsPage() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [error, setError] = useState<string | null>(null);

  const fetchTickets = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetch('http://localhost:8383/escalations');
      if (!res.ok) {
        throw new Error(`Server returned code ${res.status}`);
      }
      const data = await res.json();
      setTickets(data);
    } catch (err: any) {
      console.error(err);
      setError(
        'Unable to connect to the Saathi Agent Escalation server on port 8383. Make sure the backend agent is running.'
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTickets();
    const interval = setInterval(fetchTickets, 10000); // Auto-refresh every 10 seconds
    return () => clearInterval(interval);
  }, []);

  const filteredTickets = tickets.filter(
    (ticket) =>
      ticket.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      ticket.reason.toLowerCase().includes(searchQuery.toLowerCase()) ||
      ticket.ticket_id.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const getUrgencyStyles = (urgency: string) => {
    switch (urgency.toLowerCase()) {
      case 'high':
        return 'bg-rose-500/10 text-rose-400 border border-rose-500/20 shadow-[0_0_12px_rgba(244,63,94,0.15)]';
      case 'medium':
        return 'bg-amber-500/10 text-amber-400 border border-amber-500/20 shadow-[0_0_12px_rgba(245,158,11,0.15)]';
      default:
        return 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 shadow-[0_0_12px_rgba(16,185,129,0.15)]';
    }
  };

  return (
    <div className="relative min-h-screen overflow-hidden bg-slate-950 p-6 font-sans text-slate-100 md:p-12">
      {/* Background Decorative Gradients */}
      <div className="pointer-events-none absolute top-[-20%] left-[-10%] h-[500px] w-[500px] rounded-full bg-violet-600/10 blur-[120px]" />
      <div className="pointer-events-none absolute right-[-10%] bottom-[-20%] h-[500px] w-[500px] rounded-full bg-rose-600/10 blur-[120px]" />

      <main className="relative z-10 mx-auto max-w-6xl space-y-8">
        {/* Header Section */}
        <div className="flex flex-col gap-4 border-b border-slate-800 pb-6 md:flex-row md:items-center md:justify-between">
          <div className="space-y-1">
            <h1 className="bg-gradient-to-r from-violet-400 via-purple-300 to-rose-400 bg-clip-text text-3xl font-extrabold tracking-tight text-transparent md:text-4xl">
              Saathi Escalation Center
            </h1>
            <p className="text-sm text-slate-400 md:text-base">
              Human-in-the-loop dashboard for students needing teacher assistance.
            </p>
          </div>

          <button
            onClick={fetchTickets}
            className="group flex items-center gap-2 self-start rounded-xl border border-slate-800 bg-slate-900 px-4 py-2.5 shadow-lg transition-all duration-300 hover:border-slate-700 hover:bg-slate-800/80 active:scale-95 md:self-auto"
          >
            <RefreshCw
              className={`h-4 w-4 text-violet-400 transition-transform duration-500 group-hover:rotate-180 ${loading ? 'animate-spin' : ''}`}
            />
            <span className="text-sm font-medium">Refresh Data</span>
          </button>
        </div>

        {/* Info Box if Server is offline */}
        {error && (
          <div className="flex items-start gap-3 rounded-2xl border border-amber-900/30 bg-amber-950/20 p-4 text-amber-300 shadow-md">
            <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" />
            <div className="space-y-1">
              <p className="text-sm font-semibold">Server Offline / Connection Issue</p>
              <p className="text-xs leading-relaxed text-amber-400/80">{error}</p>
            </div>
          </div>
        )}

        {/* Stats & Filters Row */}
        <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
          <div className="flex gap-4">
            <div className="rounded-xl border border-slate-800 bg-slate-900 px-4 py-2">
              <span className="text-xs font-semibold tracking-wider text-slate-500 uppercase">
                Total Tickets
              </span>
              <p className="text-2xl font-bold text-slate-100">{tickets.length}</p>
            </div>
            <div className="rounded-xl border border-slate-800 bg-slate-900 px-4 py-2">
              <span className="text-xs font-semibold tracking-wider text-slate-500 uppercase">
                Open Status
              </span>
              <p className="text-2xl font-bold text-violet-400">
                {tickets.filter((t) => t.status.toLowerCase() === 'open').length}
              </p>
            </div>
          </div>

          {/* Search bar */}
          <div className="relative w-full max-w-md">
            <Search className="absolute top-1/2 left-3.5 h-4 w-4 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              placeholder="Search by student name, topic, or ticket ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full rounded-xl border border-slate-800 bg-slate-900/60 py-2.5 pr-4 pl-10 text-sm text-slate-100 placeholder-slate-500 backdrop-blur-sm transition-all duration-300 outline-none focus:border-violet-500 focus:ring-1 focus:ring-violet-500"
            />
          </div>
        </div>

        {/* Tickets Grid */}
        {loading && tickets.length === 0 ? (
          <div className="flex flex-col items-center justify-center gap-4 py-20">
            <RefreshCw className="h-8 w-8 animate-spin text-violet-500" />
            <p className="text-sm text-slate-400">Fetching escalation tickets...</p>
          </div>
        ) : filteredTickets.length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-3xl border border-dashed border-slate-800 bg-slate-900/10 py-20 text-center">
            <FileText className="mb-3 h-12 w-12 text-slate-600" />
            <h3 className="text-lg font-semibold text-slate-300">No tickets found</h3>
            <p className="mt-1 max-w-xs text-sm leading-relaxed text-slate-500">
              No matching human help request tickets are currently open. Let's keep teaching!
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
            {filteredTickets.map((ticket) => (
              <div
                key={ticket.ticket_id}
                className="group relative flex flex-col justify-between overflow-hidden rounded-2xl border border-slate-800/80 bg-slate-900/40 p-5 shadow-xl backdrop-blur-sm transition-all duration-300 hover:border-slate-700/80 hover:bg-slate-900/60 hover:shadow-[0_8px_30px_rgb(0,0,0,0.12)]"
              >
                {/* Visual Accent Glow on Hover */}
                <div className="pointer-events-none absolute top-0 right-0 h-32 w-32 rounded-full bg-violet-600/5 blur-2xl transition-all duration-500 group-hover:bg-violet-600/10" />

                <div className="relative z-10 space-y-4">
                  {/* Card Header */}
                  <div className="flex items-center justify-between">
                    <span className="rounded border border-slate-700/60 bg-slate-800 px-2 py-1 font-mono text-xs font-bold text-slate-300">
                      {ticket.ticket_id}
                    </span>
                    <span
                      className={`rounded-full px-2 py-0.5 text-[10px] font-bold tracking-wider uppercase ${getUrgencyStyles(ticket.urgency)}`}
                    >
                      {ticket.urgency}
                    </span>
                  </div>

                  {/* Student Info */}
                  <div className="flex items-start gap-3">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-violet-500/20 bg-violet-500/10 text-violet-400">
                      <User className="h-5 w-5" />
                    </div>
                    <div>
                      <h4 className="font-bold text-slate-100 transition-colors duration-300 group-hover:text-violet-300">
                        {ticket.name}
                      </h4>
                      <p className="font-mono text-xs text-slate-500">User: {ticket.user_id}</p>
                    </div>
                  </div>

                  <hr className="border-slate-800/60" />

                  {/* Details */}
                  <div className="space-y-2.5 text-sm">
                    <div className="space-y-1">
                      <span className="block text-xs font-semibold tracking-wide text-slate-500">
                        Reason for Escalation
                      </span>
                      <p className="text-xs leading-relaxed text-slate-300">{ticket.reason}</p>
                    </div>
                    {ticket.topics_covered && (
                      <div className="flex items-center gap-2 text-xs text-slate-400">
                        <BookOpen className="h-3.5 w-3.5 text-violet-400" />
                        <span>
                          Covered:{' '}
                          <strong className="text-slate-300">{ticket.topics_covered}</strong>
                        </span>
                      </div>
                    )}
                    <div className="flex items-center gap-2 text-xs text-slate-400">
                      <Phone className="h-3.5 w-3.5 text-rose-400" />
                      <span>
                        Contact:{' '}
                        <strong className="text-slate-300">{ticket.follow_up_method}</strong>
                      </span>
                    </div>
                  </div>
                </div>

                {/* Card Footer */}
                <div className="relative z-10 mt-5 flex items-center justify-between border-t border-slate-800/60 pt-3 text-xs text-slate-500">
                  <div className="flex items-center gap-1.5">
                    <Clock className="h-3.5 w-3.5" />
                    <span>
                      {new Date(ticket.timestamp).toLocaleString('en-IN', {
                        day: '2-digit',
                        month: 'short',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </span>
                  </div>
                  <div className="flex items-center gap-1 font-medium text-emerald-400/90">
                    <CheckCircle className="h-3.5 w-3.5" />
                    <span>{ticket.status}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
