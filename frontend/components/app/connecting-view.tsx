'use client';

import React from 'react';

interface ConnectingViewProps {
  onCancel?: () => void;
}

export function ConnectingView({ onCancel }: ConnectingViewProps) {
  return (
    <div className="relative w-full max-w-4xl px-4 py-8 mx-auto flex items-center justify-center min-h-[50vh]">
      {/* Background glowing blobs */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-64 h-64 bg-teal-500/10 dark:bg-teal-500/15 rounded-full blur-3xl pointer-events-none" />

      {/* Glassmorphic card */}
      <section className="relative overflow-hidden backdrop-blur-xl bg-white/40 dark:bg-black/35 border border-white/20 dark:border-white/5 rounded-3xl p-8 md:p-12 shadow-2xl flex flex-col items-center justify-center text-center max-w-md mx-auto w-full">
        
        {/* Loading Spinner with glowing core */}
        <div className="relative mb-8 w-24 h-24 flex items-center justify-center">
          {/* Glowing core */}
          <div className="absolute w-12 h-12 rounded-full bg-teal-500/30 dark:bg-teal-400/40 blur-md animate-pulse" />
          
          {/* Animated loading border */}
          <div className="absolute inset-0 rounded-full border-4 border-teal-500/20 border-t-teal-600 dark:border-teal-400/20 dark:border-t-teal-400 animate-spin" />
        </div>

        {/* Text and Info */}
        <h2 className="text-2xl font-bold text-foreground">
          Connecting to Saathi
        </h2>
        
        <p className="text-muted-foreground mt-3 text-sm leading-relaxed max-w-xs">
          Setting up your study room. Please make sure your microphone is allowed and wait a moment...
        </p>

        {/* Cancel Button */}
        {onCancel && (
          <button
            onClick={onCancel}
            className="mt-8 px-5 py-2 text-xs font-semibold text-muted-foreground hover:text-foreground bg-white/10 dark:bg-white/5 border border-white/10 hover:bg-white/20 rounded-full transition-all cursor-pointer"
          >
            Cancel
          </button>
        )}
      </section>
    </div>
  );
}
