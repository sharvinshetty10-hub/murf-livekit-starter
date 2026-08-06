import { Button } from '@/components/ui/button';

function SparklesIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      strokeWidth={1.5}
      stroke="currentColor"
      className="size-5 text-teal-500 animate-pulse"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M9.813 15.904 9 21l-.813-5.096L3 15.187l5.096-.813L9 9.25l.813 5.121L15 15.188l-5.187.716ZM19.071 3.386a.25.25 0 0 1 .458 0l.334.804c.053.128.15.226.279.279l.804.334a.25.25 0 0 1 0 .458l-.804.334a.279.279 0 0 0-.279.279l-.334.804a.25.25 0 0 1-.458 0l-.334-.804a.279.279 0 0 0-.279-.279l-.804-.334a.25.25 0 0 1 0-.458l.804-.334c.128-.053.226-.15.279-.279l.334-.804ZM18.75 16.75a.25.25 0 0 1 .458 0l.19.458c.03.072.088.13.16.16l.458.19a.25.25 0 0 1 0 .458l-.458.19a.18.18 0 0 0-.16.16l-.19.458a.25.25 0 0 1-.458 0l-.19-.458a.18.18 0 0 0-.16-.16l-.458-.19a.25.25 0 0 1 0-.458l.458-.19c.072-.03.13-.088.16-.16l.19-.458Z"
      />
    </svg>
  );
}

interface WelcomeViewProps {
  startButtonText: string;
  onStartCall: () => void;
}

export const WelcomeView = ({
  startButtonText,
  onStartCall,
  ref,
}: React.ComponentProps<'div'> & WelcomeViewProps) => {
  return (
    <div ref={ref} className="relative w-full max-w-4xl px-4 py-8 mx-auto">
      {/* Background soft glowing blur elements */}
      <div className="absolute top-1/4 left-1/4 -translate-x-1/2 -translate-y-1/2 w-64 h-64 bg-teal-500/10 dark:bg-teal-500/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 translate-x-1/2 translate-y-1/2 w-80 h-80 bg-orange-500/5 dark:bg-orange-500/10 rounded-full blur-3xl pointer-events-none" />

      {/* Main Glassmorphic Card Container */}
      <section className="relative overflow-hidden backdrop-blur-xl bg-white/40 dark:bg-black/35 border border-white/20 dark:border-white/5 rounded-3xl p-8 md:p-12 shadow-2xl flex flex-col items-center justify-center text-center max-w-2xl mx-auto">
        
        {/* Voice for Bharat Indian Flag Gradient Badge */}
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-linear-to-r from-orange-500/10 via-white/10 to-emerald-500/10 border border-orange-500/20 dark:border-emerald-500/20 text-xs font-semibold tracking-wide text-orange-600 dark:text-emerald-400 mb-6 uppercase shadow-xs">
          <span className="flex h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
          🇮🇳 Voice for Bharat Edition
        </div>

        {/* Pulsing Glowing AI Orb Avatar Representation */}
        <div className="relative mb-6 flex items-center justify-center">
          <div className="absolute inset-0 rounded-full bg-teal-500/20 dark:bg-teal-400/20 blur-xl animate-pulse scale-125" />
          <div className="relative w-20 h-20 rounded-full bg-linear-to-tr from-teal-600 to-teal-400 dark:from-teal-500 dark:to-teal-300 flex items-center justify-center shadow-lg shadow-teal-500/20">
            <svg
              width="36"
              height="36"
              viewBox="0 0 64 64"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              className="text-white"
            >
              <path
                d="M15 24V40C15 40.7957 14.6839 41.5587 14.1213 42.1213C13.5587 42.6839 12.7956 43 12 43C11.2044 43 10.4413 42.6839 9.87868 42.1213C9.31607 41.5587 9 40.7957 9 40V24C9 23.2044 9.31607 22.4413 9.87868 21.8787C10.4413 21.3161 11.2044 21 12 21C12.7956 21 13.5587 21.3161 14.1213 21.8787C14.6839 22.4413 15 23.2044 15 24ZM22 5C21.2044 5 20.4413 5.31607 19.8787 5.87868C19.3161 6.44129 19 7.20435 19 8V56C19 56.7957 19.3161 57.5587 19.8787 58.1213C20.4413 58.6839 21.2044 59 22 59C22.7956 59 23.5587 58.6839 24.1213 58.1213C24.6839 57.5587 25 56.7957 25 56V8C25 7.20435 24.6839 6.44129 24.1213 5.87868C23.5587 5.31607 22.7956 5 22 5ZM32 13C31.2044 13 30.4413 13.3161 29.8787 13.8787C29.3161 14.4413 29 15.2044 29 16V48C29 48.7957 29.3161 49.5587 29.8787 50.1213C30.4413 50.6839 31.2044 51 32 51C32.7956 51 33.5587 50.6839 34.1213 50.1213C34.6839 49.5587 35 48.7957 35 48V16C35 15.2044 34.6839 14.4413 34.1213 13.8787C33.5587 13.3161 32.7956 13 32 13ZM42 21C41.2043 21 40.4413 21.3161 39.8787 21.8787C39.3161 22.4413 39 23.2044 39 24V40C39 40.7957 39.3161 41.5587 39.8787 42.1213C40.4413 42.6839 41.2043 43 42 43C42.7957 43 43.5587 42.6839 44.1213 42.1213C44.6839 41.5587 45 40.7957 45 40V24C45 23.2044 44.6839 22.4413 44.1213 21.8787C43.5587 21.3161 42.7957 21 42 21ZM52 17C51.2043 17 50.4413 17.3161 49.8787 17.8787C49.3161 18.4413 49 19.2044 49 20V44C49 44.7957 49.3161 45.5587 49.8787 46.1213C50.4413 46.6839 51.2043 47 52 47C52.7957 47 53.5587 46.6839 54.1213 46.1213C54.6839 45.5587 55 44.7957 55 44V20C55 19.2044 54.6839 18.4413 54.1213 17.8787C53.5587 17.3161 52.7957 17 52 17Z"
                fill="currentColor"
              />
            </svg>
          </div>
        </div>

        {/* Title */}
        <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight text-foreground bg-linear-to-b from-foreground to-foreground/80 bg-clip-text">
          Meet <span className="text-teal-600 dark:text-teal-400 font-black">Saathi</span>
        </h1>

        {/* Description */}
        <p className="text-muted-foreground max-w-md mt-3 text-sm md:text-base leading-relaxed">
          A patient, encouraging voice tutor designed for grassroots students in India. Speak naturally and get instant answers for your studies.
        </p>

        {/* Suggested Topics Card Grid */}
        <div className="grid grid-cols-2 gap-3 w-full max-w-md mt-8 text-left">
          <div className="flex items-center gap-2 p-3 rounded-xl bg-white/20 dark:bg-white/5 border border-white/10 text-xs text-foreground/95 hover:bg-white/30 dark:hover:bg-white/10 transition-colors cursor-pointer">
            <span className="p-1 rounded-md bg-teal-500/10 text-teal-600 dark:text-teal-400">📝</span>
            <div>
              <p className="font-semibold">Grammar</p>
              <p className="text-[10px] text-muted-foreground">A vs An / Sentence structure</p>
            </div>
          </div>
          <div className="flex items-center gap-2 p-3 rounded-xl bg-white/20 dark:bg-white/5 border border-white/10 text-xs text-foreground/95 hover:bg-white/30 dark:hover:bg-white/10 transition-colors cursor-pointer">
            <span className="p-1 rounded-md bg-orange-500/10 text-orange-600 dark:text-orange-400">🔬</span>
            <div>
              <p className="font-semibold">Science</p>
              <p className="text-[10px] text-muted-foreground">Why is the sky blue?</p>
            </div>
          </div>
        </div>

        {/* Action Button */}
        <div className="relative group w-full max-w-xs mt-8">
          <div className="absolute inset-0 bg-teal-500/25 rounded-full blur-md opacity-75 group-hover:opacity-100 transition-opacity animate-pulse pointer-events-none" />
          <Button
            size="lg"
            onClick={onStartCall}
            className="relative w-full h-12 rounded-full bg-teal-600 hover:bg-teal-700 dark:bg-teal-500 dark:hover:bg-teal-600 text-white font-bold tracking-wide transition-all shadow-lg hover:shadow-teal-500/20 active:scale-98 flex items-center justify-center gap-2 text-sm"
          >
            <SparklesIcon />
            {startButtonText}
          </Button>
        </div>

      </section>

      {/* Footer Info */}
      <div className="mt-8 flex flex-col items-center justify-center text-center gap-1">
        <p className="text-muted-foreground text-[11px] md:text-xs">
          Powered by <strong className="text-foreground/90">Murf Falcon</strong> (TTS) &amp; <strong className="text-foreground/90">Gemini 3.5</strong> (LLM) over <strong className="text-foreground/90">LiveKit</strong>
        </p>
        <p className="text-[10px] text-muted-foreground/60 max-w-xs">
          Built for the Day 1 challenge of 10 Days of AI Voice Agents.
        </p>
      </div>
    </div>
  );
};
