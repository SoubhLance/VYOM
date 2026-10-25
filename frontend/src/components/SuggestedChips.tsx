import React from 'react';
import { Sparkles, BookOpen, Compass, Shield, Flame } from 'lucide-react';

interface SuggestedChipsProps {
  onSelectQuery: (query: string) => void;
  disabled?: boolean;
}

interface ChipItem {
  label: string;
  query: string;
  badge: string;
  icon: React.ReactNode;
}

export const SUGGESTIONS: ChipItem[] = [
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
    icon: <BookOpen className="w-3.5 h-3.5 text-[#C5A059]" />,
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
    icon: <Sparkles className="w-3.5 h-3.5 text-[#C5A059]" />,
  },
  {
    label: 'Restoring Dharma in chaotic times',
    query: 'When does the Divine incarnate to protect righteousness? BG 4.7 and BG 4.8',
    badge: 'BG 4.7-8',
    icon: <Shield className="w-3.5 h-3.5 text-[#E28743]" />,
  },
];

export const SuggestedChips: React.FC<SuggestedChipsProps> = ({
  onSelectQuery,
  disabled = false,
}) => {
  return (
    <div className="w-full">
      <div className="flex items-center gap-2 mb-3">
        <Sparkles className="w-3.5 h-3.5 text-[#E28743]" />
        <span className="font-cinzel text-xs font-semibold uppercase tracking-wider text-[#6A5A48]">
          Sacred Inquiries for Contemplation
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
        {SUGGESTIONS.map((item, idx) => (
          <button
            key={idx}
            disabled={disabled}
            onClick={() => onSelectQuery(item.query)}
            className="group relative flex items-center justify-between p-3 rounded-xl border border-[#C5A059]/20 bg-[#FFFDF8]/75 hover:bg-[#F4ECE1]/90 hover:border-[#C5A059]/50 transition-all text-left disabled:opacity-50 disabled:cursor-not-allowed shadow-sm hover:shadow-[0_0_16px_rgba(226,200,137,0.15)]"
          >
            <div className="flex items-center gap-2.5 pr-2">
              <span className="p-1.5 rounded-lg bg-[#F4ECE1] border border-[#C5A059]/15 group-hover:border-[#E28743]/40 transition-colors">
                {item.icon}
              </span>
              <span className="font-sans-body text-xs font-medium text-[#2C261F] group-hover:text-[#2C261F] transition-colors line-clamp-1">
                {item.label}
              </span>
            </div>

            <span className="font-cinzel text-[10px] font-bold px-2 py-0.5 rounded-md bg-[#F4ECE1]/80 border border-[#C5A059]/30 text-[#C5A059] whitespace-nowrap group-hover:border-[#E28743]/60 group-hover:text-[#E28743] transition-colors">
              {item.badge}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
};
