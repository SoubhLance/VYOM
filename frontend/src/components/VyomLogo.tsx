import React from 'react';

interface VyomLogoProps {
  className?: string;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  showSubtitle?: boolean;
  /** 'ink' (#4B3825) for light surfaces, 'gold' (#C5A059) for dark ones */
  tone?: 'ink' | 'gold';
}

const HEIGHTS = { sm: 'h-10 sm:h-12', md: 'h-14', lg: 'h-20', xl: 'h-28' } as const;

/** The VYOM mark: a transparent mask (public/vyom-mark.webp) filled with a theme colour. */
export const VyomLogo: React.FC<VyomLogoProps> = ({ className = '', size = 'md', showSubtitle = true, tone = 'ink' }) => (
  <div className={`inline-flex flex-col items-center select-none ${className}`}>
    <span role="img" aria-label="VYOM" className={`vyom-mark ${HEIGHTS[size]} ${tone === 'gold' ? 'text-[#C5A059]' : 'text-[#4B3825]'}`} />
    {showSubtitle && <span className={`mt-1 font-cinzel text-center text-[10px] sm:text-xs ${tone === 'gold' ? 'text-[#FAF6ED]' : 'text-[#6A5A48]'}`}>Bhagavad Gita Multimodal Intelligence</span>}
  </div>
);
