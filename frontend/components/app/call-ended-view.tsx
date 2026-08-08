'use client';

import React from 'react';
import { Button } from '@/components/ui/button';

interface CallEndedViewProps {
  onRestart: () => void;
}

export function CallEndedView({ onRestart }: CallEndedViewProps) {
  return (
    <div className="relative w-full max-w-4xl px-4 py-8 mx-auto flex items-center justify-center min-h-[50vh]">
      {/* Background soft glowing blur elements */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-64 h-64 bg-teal-500/10 dark:bg-teal-500/15 rounded-full blur-3xl pointer-events-none" />

      {/* Main Glassmorphic Card Container */}
      <section className="relative overflow-hidden backdrop-blur-xl bg-white/40 dark:bg-black/35 border border-white/20 dark:border-white/5 rounded-3xl p-8 md:p-12 shadow-2xl flex flex-col items-center justify-center text-center max-w-md mx-auto w-full">
        
        {/* Sparkles / Celebration icon representation */}
        <div className="relative mb-6 flex items-center justify-center">
          <div className="absolute inset-0 rounded-full bg-emerald-500/10 dark:bg-emerald-400/20 blur-xl scale-125 animate-pulse" />
          <div className="relative w-16 h-16 rounded-full bg-emerald-100 dark:bg-emerald-950 flex items-center justify-center shadow-md">
            <span className="text-3xl">🎓</span>
          </div>
        </div>

        {/* Title */}
        <h2 className="text-2xl font-bold text-foreground">
          Session Completed!
        </h2>

        {/* Reassuring message */}
        <p className="text-muted-foreground mt-3 text-sm leading-relaxed max-w-xs">
          Great job studying with Saathi today! Every small step of learning brings you closer to your goals. Keep up the amazing work!
        </p>

        {/* Action Button */}
        <div className="relative group w-full max-w-xs mt-8">
          <div className="absolute inset-0 bg-teal-500/25 rounded-full blur-md opacity-75 group-hover:opacity-100 transition-opacity animate-pulse pointer-events-none" />
          <Button
            size="lg"
            onClick={onRestart}
            className="relative w-full h-12 rounded-full bg-teal-600 hover:bg-teal-700 dark:bg-teal-500 dark:hover:bg-teal-600 text-white font-bold tracking-wide transition-all shadow-lg hover:shadow-teal-500/20 active:scale-98 flex items-center justify-center gap-2 text-sm"
          >
            Start a New Session 🔄
          </Button>
        </div>

      </section>
    </div>
  );
}
