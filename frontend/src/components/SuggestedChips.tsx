import React from 'react';
import { Sparkles, BookOpen, Compass, Shield, Flame } from 'lucide-react';

interface ChipItem {
  label: string;
  query: string;
  badge: string;
  icon: React.ReactNode;
}

const SUGGESTIONS: ChipItem[] = [
  {
    label: 'Whom should I surrender to?',
    query: 'Whom should I surrender to? Explain BG 18.66 and Sharanagati',
    badge: 'BG 18.66',
    icon: <Shield className="w-3.5 h-3.5 text-[#E28743]" />,
  },
  {
    label: 'Explain BG 2.47 Nishkama Karma',
    query: 'Explain Nishkama Karma and duty from BG 2.47',
    badge: 'BG 2.47',
    icon: <BookOpen className="w-3.5 h-3.5 text-[#A27427]" />,
  },
  {
    label: 'Overcoming fear of failure',
    query: 'How to overcome fear of failure and anxiety through the eternal Atman? BG 2.20',
    badge: 'BG 2.20',
    icon: <Compass className="w-3.5 h-3.5 text-[#E28743]" />,
  },
  {
    label: 'How to master an agitated mind?',
    query: 'How does Sri Krishna advise mastering a turbulent mind in BG 6.35?',
    badge: 'BG 6.35',
    icon: <Flame className="w-3.5 h-3.5 text-[#8C2D19]" />,
  },
  {
    label: 'The Cosmic Vision of Time',
    query: 'What is the revelation of Kala (Time) in the Viswarupa BG 11.32?',
    badge: 'BG 11.32',
    icon: <Sparkles className="w-3.5 h-3.5 text-[#A27427]" />,
  },
  {
    label: 'Restoring Dharma in chaotic times',
    query: 'When does the Divine incarnate to protect righteousness? BG 4.7 and BG 4.8',
    badge: 'BG 4.7-8',
    icon: <Shield className="w-3.5 h-3.5 text-[#E28743]" />,
  },
];

const THEMES: Array<{ label: string; query: string }> = [
  { label: 'Surrender & Anxiety', query: 'How can the Bhagavad Gita help me meet anxiety through surrender? Explain BG 18.66.' },
  { label: 'Nishkama Karma in Modern Life', query: 'How can I practice Nishkama Karma in modern life? Explain BG 2.47.' },
  { label: 'Conquering Self-Doubt', query: 'How can Krishna’s teachings help me overcome self-doubt?' },
  { label: 'Decision Making in Dilemma', query: 'How should I make a difficult decision when I feel torn between duties?' },
];

interface InspirationPanelProps {
  onSelectQuery: (query: string) => void;
  disabled?: boolean;
}

/** Themes and sacred inquiries: a side rail on wide screens, a bottom sheet in the chat elsewhere. */
export const InspirationPanel: React.FC<InspirationPanelProps> = ({ onSelectQuery, disabled = false }) => (
  <div className="space-y-5">
    <div className="flex items-center gap-2">
      <Sparkles className="h-4 w-4 text-[#E28743]" />
      <h2 className="font-cinzel text-sm font-bold tracking-[0.12em] text-[#8C2D19]">Inspiration</h2>
    </div>

    <section aria-label="Themes">
      <p className="mb-2 font-cinzel text-[10px] font-bold uppercase tracking-[0.18em] text-[#6A5A48]">Themes</p>
      <div className="flex flex-wrap gap-2">
        {THEMES.map((theme) => (
          <button
            key={theme.label}
            disabled={disabled}
            onClick={() => onSelectQuery(theme.query)}
            className="rounded-full border border-[#C5A059]/35 bg-[#FFFDF8]/85 px-3 py-1.5 text-xs font-semibold text-[#704B20] transition hover:-translate-y-0.5 hover:border-[#A27427] hover:bg-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#C5A059]/50 disabled:opacity-50 motion-reduce:hover:translate-y-0"
          >
            {theme.label}
          </button>
        ))}
      </div>
    </section>

    <section aria-label="Sacred inquiries">
      <p className="mb-2 font-cinzel text-[10px] font-bold uppercase tracking-[0.18em] text-[#6A5A48]">Sacred inquiries</p>
      <div className="space-y-1.5">
        {SUGGESTIONS.map((item) => (
          <button
            key={item.label}
            disabled={disabled}
            onClick={() => onSelectQuery(item.query)}
            className="group flex w-full items-center gap-2.5 rounded-xl border border-transparent px-2.5 py-2 text-left transition hover:border-[#C5A059]/40 hover:bg-[#FFFDF8] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#C5A059]/50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <span className="shrink-0 rounded-lg border border-[#C5A059]/20 bg-[#F4ECE1] p-1.5 transition-colors group-hover:border-[#E28743]/40">{item.icon}</span>
            <span className="min-w-0 flex-1 text-[13px] font-medium leading-snug text-[#2C261F]">{item.label}</span>
            <span className="shrink-0 font-cinzel text-[10px] font-bold text-[#A27427]">{item.badge}</span>
          </button>
        ))}
      </div>
    </section>
  </div>
);
