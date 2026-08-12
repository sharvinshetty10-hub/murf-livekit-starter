'use client';

import React from 'react';
import { Button } from '@/components/ui/button';

interface CallEndedViewProps {
  onRestart: () => void;
}

export function CallEndedView({ onRestart }: CallEndedViewProps) {
  return (
    <div className="relative mx-auto flex min-h-[50vh] w-full max-w-4xl items-center justify-center px-4 py-8">
      {/* Background soft glowing blur elements */}
      <div className="pointer-events-none absolute top-1/2 left-1/2 h-64 w-64 -translate-x-1/2 -translate-y-1/2 rounded-full bg-teal-500/10 blur-3xl dark:bg-teal-500/15" />

      {/* Main Glassmorphic Card Container */}
      <section className="relative mx-auto flex w-full max-w-md flex-col items-center justify-center overflow-hidden rounded-3xl border border-white/20 bg-white/40 p-8 text-center shadow-2xl backdrop-blur-xl md:p-12 dark:border-white/5 dark:bg-black/35">
        {/* Sparkles / Celebration icon representation */}
        <div className="relative mb-6 flex items-center justify-center">
          <div className="absolute inset-0 scale-125 animate-pulse rounded-full bg-emerald-500/10 blur-xl dark:bg-emerald-400/20" />
          <div className="relative flex h-16 w-16 items-center justify-center rounded-full bg-emerald-100 shadow-md dark:bg-emerald-950">
            <span className="text-3xl">🎓</span>
          </div>
        </div>

        {/* Title */}
        <h2 className="text-foreground text-2xl font-bold">Session Completed!</h2>

        {/* Reassuring message */}
        <p className="text-muted-foreground mt-3 max-w-xs text-sm leading-relaxed">
          Great job studying with Saathi today! Every small step of learning brings you closer to
          your goals. Keep up the amazing work!
        </p>

        {/* Action Button */}
        <div className="group relative mt-8 w-full max-w-xs">
          <div className="pointer-events-none absolute inset-0 animate-pulse rounded-full bg-teal-500/25 opacity-75 blur-md transition-opacity group-hover:opacity-100" />
          <Button
            size="lg"
            onClick={onRestart}
            className="relative flex h-12 w-full items-center justify-center gap-2 rounded-full bg-teal-600 text-sm font-bold tracking-wide text-white shadow-lg transition-all hover:bg-teal-700 hover:shadow-teal-500/20 active:scale-98 dark:bg-teal-500 dark:hover:bg-teal-600"
          >
            Start a New Session 🔄
          </Button>
        </div>
      </section>
    </div>
  );
}
