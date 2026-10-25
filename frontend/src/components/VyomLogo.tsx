import React from 'react';

interface VyomLogoProps {
  className?: string;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  showSubtitle?: boolean;
}

export const VyomLogo: React.FC<VyomLogoProps> = ({ className = '', size = 'md', showSubtitle = true }) => (
  <div className={`inline-flex flex-col items-center select-none ${className}`}>
    <img src="/Vyom.png" alt="VYOM" className={`${size === 'sm' ? 'h-10 sm:h-12' : size === 'md' ? 'h-14' : size === 'lg' ? 'h-20' : 'h-28'} w-auto object-contain drop-shadow-[0_0_12px_rgba(226,200,137,0.35)]`} />
    {showSubtitle && <span className="mt-1 font-cinzel text-center text-[10px] sm:text-xs text-[#FAF6ED]">Bhagavad Gita Multimodal Intelligence</span>}
  </div>
);
