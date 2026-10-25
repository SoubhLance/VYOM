import React from 'react';
import { VyomLogo } from './VyomLogo';
import { Volume2, VolumeX, Activity, Info, Music2 } from 'lucide-react';

interface NavbarProps {
  isBackendOnline: boolean;
  isCheckingHealth: boolean;
  onRefreshHealth: () => void;
  isAudioPlaying: boolean;
  onToggleAudio: () => void;
  onOpenAbout: () => void;
  onToggleChant: () => void;
  isChanting: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({ isBackendOnline, isCheckingHealth, onRefreshHealth, isAudioPlaying, onToggleAudio, onOpenAbout, onToggleChant, isChanting }) => (
  <header className="sticky top-0 z-40 w-full border-b border-[#C5A059]/30 bg-[#FAF6EB]/85 shadow-sm backdrop-blur-xl">
    <div className="mx-auto flex min-h-[76px] max-w-7xl items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
      <div className="flex min-w-0 items-center gap-3"><VyomLogo size="sm" showSubtitle={false} /><span className="hidden text-sm text-[#4B3825] sm:block">Bhagavad Gita Multimodal Intelligence</span></div>
      <div className="flex items-center gap-2 sm:gap-3">
        <button onClick={onRefreshHealth} title="Refresh API status" className="flex items-center gap-2 rounded-full border border-[#C5A059]/30 bg-white/70 px-3 py-2 text-xs text-[#4B3825]"><span className="relative flex h-2 w-2"><span className={`absolute inline-flex h-full w-full animate-ping rounded-full opacity-75 ${isBackendOnline ? 'bg-emerald-400' : 'bg-amber-400'}`} /><span className={`relative inline-flex h-2 w-2 rounded-full ${isBackendOnline ? 'bg-emerald-500' : 'bg-amber-500'}`} /></span><span className="hidden sm:inline">{isCheckingHealth ? 'Connecting…' : isBackendOnline ? 'Connected' : 'Offline'}</span><Activity className="h-3.5 w-3.5 text-[#A27427]" /></button>
        <button onClick={onToggleAudio} aria-pressed={isAudioPlaying} title={isAudioPlaying ? 'Mute ambient music' : 'Play ambient music'} className={`flex items-center gap-2 rounded-xl border px-3 py-2 transition-colors ${isAudioPlaying ? 'border-[#A27427]/60 bg-[#F1E0BB] text-[#8C2D19]' : 'border-[#C5A059]/30 bg-white/70 text-[#704B20] hover:border-[#A27427]'}`}>
          {isAudioPlaying ? <span className="flex h-4 items-end gap-0.5" aria-label="Music playing"><i className="h-2 w-0.5 animate-pulse bg-[#A27427]" /><i className="h-4 w-0.5 animate-pulse bg-[#A27427] [animation-delay:120ms]" /><i className="h-2.5 w-0.5 animate-pulse bg-[#A27427] [animation-delay:240ms]" /></span> : <VolumeX className="h-4 w-4" />}
          {isAudioPlaying && <Volume2 className="h-4 w-4" />}<span className="hidden text-xs md:inline">Music</span>
        </button>
        <button onClick={onToggleChant} aria-pressed={isChanting} title={isChanting ? 'Stop Sanskrit chant' : 'Play Sanskrit chant'} className={`rounded-xl border p-2.5 ${isChanting ? 'border-[#A27427] bg-[#F1E0BB] text-[#8C2D19]' : 'border-[#C5A059]/30 bg-white/70 text-[#704B20]'}`}><Music2 className="h-4 w-4" /></button>
        <button onClick={onOpenAbout} title="About VYOM" className="rounded-xl border border-[#C5A059]/30 bg-white/70 p-2.5 text-[#704B20] hover:border-[#A27427]"><Info className="h-4 w-4" /></button>
      </div>
    </div>
  </header>
);
