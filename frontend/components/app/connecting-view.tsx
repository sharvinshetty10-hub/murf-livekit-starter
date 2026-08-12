'use client';

import React from 'react';

interface ConnectingViewProps {
  onCancel?: () => void;
}

export function ConnectingView({ onCancel }: ConnectingViewProps) {
  return (
    <div className="relative mx-auto flex min-h-[50vh] w-full max-w-4xl items-center justify-center px-4 py-8">
      {/* Background glowing blobs */}
      <div className="pointer-events-none absolute top-1/2 left-1/2 h-64 w-64 -translate-x-1/2 -translate-y-1/2 rounded-full bg-teal-500/10 blur-3xl dark:bg-teal-500/15" />

      {/* Glassmorphic card */}
      <section className="relative mx-auto flex w-full max-w-md flex-col items-center justify-center overflow-hidden rounded-3xl border border-white/20 bg-white/40 p-8 text-center shadow-2xl backdrop-blur-xl md:p-12 dark:border-white/5 dark:bg-black/35">
        {/* Loading Spinner with glowing core */}
        <div className="relative mb-8 flex h-24 w-24 items-center justify-center">
          {/* Glowing core */}
          <div className="absolute h-12 w-12 animate-pulse rounded-full bg-teal-500/30 blur-md dark:bg-teal-400/40" />

          {/* Animated loading border */}
          <div className="absolute inset-0 animate-spin rounded-full border-4 border-teal-500/20 border-t-teal-600 dark:border-teal-400/20 dark:border-t-teal-400" />
        </div>

        {/* Text and Info */}
        <h2 className="text-foreground text-2xl font-bold">Connecting to Saathi</h2>

        <p className="text-muted-foreground mt-3 max-w-xs text-sm leading-relaxed">
          Setting up your study room. Please make sure your microphone is allowed and wait a
          moment...
        </p>

        {/* Cancel Button */}
        {onCancel && (
          <button
            onClick={onCancel}
            className="text-muted-foreground hover:text-foreground mt-8 cursor-pointer rounded-full border border-white/10 bg-white/10 px-5 py-2 text-xs font-semibold transition-all hover:bg-white/20 dark:bg-white/5"
          >
            Cancel
          </button>
        )}
      </section>
    </div>
  );
}
