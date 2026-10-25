import React, { useRef, useState, useEffect, useCallback } from 'react';
import { Download, X, Sparkles, Copy, Check, Palette } from 'lucide-react';
import type { GitaVerse } from '../data/gitaVerses';
import confetti from 'canvas-confetti';

interface QuoteCardModalProps {
  verse: GitaVerse | null;
  isOpen: boolean;
  onClose: () => void;
}

type ThemeMode = 'royalGold' | 'cosmicObsidian' | 'dharmaCrimson';

export const QuoteCardModal: React.FC<QuoteCardModalProps> = ({
  verse,
  isOpen,
  onClose,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [theme, setTheme] = useState<ThemeMode>('royalGold');
  const [copied, setCopied] = useState(false);

  const renderCanvas = useCallback(() => {
    if (!verse || !canvasRef.current) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // High Resolution: 1200 x 1200
    const w = 1200;
    const h = 1200;
    canvas.width = w;
    canvas.height = h;

    // Palette configurations
    const palettes = {
      royalGold: {
        bgStart: '#FFFDF8',
        bgEnd: '#F4ECE1',
        border: '#C5A059',
        borderMuted: 'rgba(226, 200, 137, 0.25)',
        goldText: '#8C2D19',
        bodyText: '#2C261F',
        accentGlow: 'rgba(255, 183, 3, 0.15)',
      },
      cosmicObsidian: {
        bgStart: '#0B0D14',
        bgEnd: '#05070A',
        border: '#C5A059',
        borderMuted: 'rgba(197, 160, 89, 0.2)',
        goldText: '#F5E6C8',
        bodyText: '#6A5A48',
        accentGlow: 'rgba(226, 200, 137, 0.1)',
      },
      dharmaCrimson: {
        bgStart: '#260D12',
        bgEnd: '#0D0608',
        border: '#C5A059',
        borderMuted: 'rgba(226, 200, 137, 0.3)',
        goldText: '#E28743',
        bodyText: '#2C261F',
        accentGlow: 'rgba(245, 158, 11, 0.18)',
      },
    }[theme];

    // 1. Background Gradient
    const bgGrad = ctx.createRadialGradient(w / 2, h / 2, 80, w / 2, h / 2, w / 1.3);
    bgGrad.addColorStop(0, palettes.bgStart);
    bgGrad.addColorStop(1, palettes.bgEnd);
    ctx.fillStyle = bgGrad;
    ctx.fillRect(0, 0, w, h);

    // 2. Sacred Sun Yantra Background Ring
    ctx.save();
    ctx.strokeStyle = palettes.borderMuted;
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.arc(w / 2, h / 2 - 40, 340, 0, Math.PI * 2);
    ctx.stroke();

    ctx.beginPath();
    ctx.arc(w / 2, h / 2 - 40, 420, 0, Math.PI * 2);
    ctx.stroke();

    // Radial Rays
    for (let i = 0; i < 24; i++) {
      const angle = (i * Math.PI * 2) / 24;
      const x1 = w / 2 + Math.cos(angle) * 340;
      const y1 = h / 2 - 40 + Math.sin(angle) * 340;
      const x2 = w / 2 + Math.cos(angle) * 420;
      const y2 = h / 2 - 40 + Math.sin(angle) * 420;
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.stroke();
    }
    ctx.restore();

    // 3. Ornate Filigree Corner Borders
    const pad = 60;
    ctx.strokeStyle = palettes.border;
    ctx.lineWidth = 2;
    ctx.strokeRect(pad, pad, w - pad * 2, h - pad * 2);

    ctx.strokeStyle = palettes.borderMuted;
    ctx.lineWidth = 1;
    ctx.strokeRect(pad + 12, pad + 12, w - (pad + 12) * 2, h - (pad + 12) * 2);

    // Corner Ornaments
    const drawCorner = (x: number, y: number, angle: number) => {
      ctx.save();
      ctx.translate(x, y);
      ctx.rotate(angle);
      ctx.strokeStyle = palettes.border;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(0, 0);
      ctx.lineTo(40, 0);
      ctx.moveTo(0, 0);
      ctx.lineTo(0, 40);
      ctx.stroke();

      ctx.fillStyle = palettes.goldText;
      ctx.fillRect(-4, -4, 8, 8);
      ctx.restore();
    };

    drawCorner(pad, pad, 0);
    drawCorner(w - pad, pad, Math.PI / 2);
    drawCorner(w - pad, h - pad, Math.PI);
    drawCorner(pad, h - pad, -Math.PI / 2);

    // 4. Header: Srimad Bhagavad Gita Badge
    ctx.textAlign = 'center';
    ctx.fillStyle = palettes.goldText;
    ctx.font = 'bold 24px "Cinzel", serif';
    ctx.fillText('SRIMAD BHAGAVAD GITA', w / 2, pad + 70);

    ctx.fillStyle = palettes.border;
    ctx.font = '600 18px "Cinzel", serif';
    ctx.fillText(
      `CHAPTER ${verse.chapter} • VERSE ${verse.verse}`,
      w / 2,
      pad + 105
    );

    // Header Divider Line with Center Diamond
    ctx.strokeStyle = palettes.borderMuted;
    ctx.beginPath();
    ctx.moveTo(w / 2 - 160, pad + 125);
    ctx.lineTo(w / 2 + 160, pad + 125);
    ctx.stroke();

    ctx.fillStyle = palettes.goldText;
    ctx.beginPath();
    ctx.arc(w / 2, pad + 125, 4, 0, Math.PI * 2);
    ctx.fill();

    // 5. Sanskrit Shloka in Devanagari
    ctx.fillStyle = '#FFFFFF';
    ctx.font = 'bold 36px "Tiro Devanagari Sanskrit", "Yatra One", serif';
    const sanskritLines = verse.sanskrit.split('\n');
    let sanskritY = 410;
    sanskritLines.forEach((line) => {
      ctx.fillText(line.trim(), w / 2, sanskritY);
      sanskritY += 56;
    });

    // 6. Romanized Transliteration
    ctx.fillStyle = palettes.goldText;
    ctx.font = 'italic 20px "Cinzel", serif';
    const transLines = verse.transliteration.split('\n');
    let transY = sanskritY + 35;
    transLines.forEach((line) => {
      ctx.fillText(line.trim(), w / 2, transY);
      transY += 34;
    });

    // Decorative Center Divider
    ctx.strokeStyle = palettes.borderMuted;
    ctx.beginPath();
    ctx.moveTo(w / 2 - 120, transY + 25);
    ctx.lineTo(w / 2 + 120, transY + 25);
    ctx.stroke();

    // 7. English Translation Block
    ctx.fillStyle = palettes.bodyText;
    ctx.font = '500 24px "Plus Jakarta Sans", sans-serif';

    // Word wrap function
    const wrapText = (text: string, maxWidth: number): string[] => {
      const words = text.split(' ');
      const lines: string[] = [];
      let currentLine = '';

      words.forEach((word) => {
        const testLine = currentLine ? `${currentLine} ${word}` : word;
        const metrics = ctx.measureText(testLine);
        if (metrics.width > maxWidth && currentLine) {
          lines.push(currentLine);
          currentLine = word;
        } else {
          currentLine = testLine;
        }
      });
      if (currentLine) lines.push(currentLine);
      return lines;
    };

    const translationLines = wrapText(`“${verse.translation}”`, 900);
    let transBlockY = transY + 80;
    translationLines.forEach((line) => {
      ctx.fillText(line, w / 2, transBlockY);
      transBlockY += 38;
    });

    // Translation Author Attribution
    ctx.fillStyle = palettes.goldText;
    ctx.font = 'italic 16px "Cinzel", serif';
    ctx.fillText(`— ${verse.author}`, w / 2, transBlockY + 25);

    // 8. Footer: Official VYOM Emblem & Watermark
    ctx.fillStyle = palettes.goldText;
    ctx.font = 'bold 22px "Cinzel", serif';
    ctx.fillText('V Y O M', w / 2, h - pad - 60);

    ctx.fillStyle = palettes.borderMuted;
    ctx.font = '600 13px "Cinzel", serif';
    ctx.fillText(
      'ANCIENT WISDOM • INFINITE UNDERSTANDING',
      w / 2,
      h - pad - 35
    );
  }, [verse, theme]);

  useEffect(() => {
    if (isOpen && verse) {
      setTimeout(renderCanvas, 100);
    }
  }, [isOpen, verse, theme, renderCanvas]);

  if (!isOpen || !verse) return null;

  const handleDownload = () => {
    if (!canvasRef.current) return;
    const link = document.createElement('a');
    link.download = `VYOM_Gita_BG_${verse.verse_id}.png`;
    link.href = canvasRef.current.toDataURL('image/png');
    link.click();

    // Celebration sparks
    confetti({
      particleCount: 40,
      spread: 60,
      origin: { y: 0.7 },
      colors: ['#E28743', '#C5A059', '#2C261F'],
    });
  };

  const handleCopy = async () => {
    if (!canvasRef.current) return;
    try {
      canvasRef.current.toBlob(async (blob) => {
        if (!blob) return;
        await navigator.clipboard.write([
          new ClipboardItem({ 'image/png': blob }),
        ]);
        setCopied(true);
        setTimeout(() => setCopied(false), 2500);
      });
    } catch {
      // Fallback text copy
      navigator.clipboard.writeText(
        `BG ${verse.verse_id}:\n${verse.sanskrit}\n\n"${verse.translation}"\n— Shared via VYOM Multimodal Intelligence`
      );
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#4B3825]/40 backdrop-blur-md animate-fade-in">
      <div className="relative w-full max-w-2xl filigree-card rounded-2xl overflow-hidden p-6 flex flex-col items-center shadow-2xl">
        {/* Header */}
        <div className="w-full flex items-center justify-between pb-4 border-b border-[#C5A059]/20 mb-4">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-[#E28743]" />
            <h3 className="font-cinzel text-base font-bold text-[#2C261F]">
              Divine Gita Quote Card (BG {verse.verse_id})
            </h3>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-[#6A5A48]/70 hover:text-[#2C261F] hover:bg-[#FFFDF8] transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Canvas Preview Container */}
        <div className="relative w-full max-w-md aspect-square rounded-xl overflow-hidden shadow-2xl border border-[#C5A059]/30 bg-[#F4ECE1]">
          <canvas ref={canvasRef} className="w-full h-full object-contain" />
        </div>

        {/* Theme Selectors */}
        <div className="mt-4 flex items-center gap-3">
          <span className="font-cinzel text-xs text-[#6A5A48]/70 flex items-center gap-1">
            <Palette className="w-3.5 h-3.5 text-[#C5A059]" /> Theme:
          </span>
          <button
            onClick={() => setTheme('royalGold')}
            className={`px-3 py-1 rounded-full text-xs font-cinzel transition-all ${
              theme === 'royalGold'
                ? 'bg-[#C5A059] text-[#F4ECE1] font-bold shadow-md'
                : 'bg-[#FFFDF8] text-[#6A5A48] border border-[#C5A059]/30'
            }`}
          >
            Royal Gold
          </button>
          <button
            onClick={() => setTheme('cosmicObsidian')}
            className={`px-3 py-1 rounded-full text-xs font-cinzel transition-all ${
              theme === 'cosmicObsidian'
                ? 'bg-[#C5A059] text-[#F4ECE1] font-bold shadow-md'
                : 'bg-[#FFFDF8] text-[#6A5A48] border border-[#C5A059]/30'
            }`}
          >
            Cosmic Obsidian
          </button>
          <button
            onClick={() => setTheme('dharmaCrimson')}
            className={`px-3 py-1 rounded-full text-xs font-cinzel transition-all ${
              theme === 'dharmaCrimson'
                ? 'bg-rose-900 text-[#2C261F] font-bold shadow-md'
                : 'bg-[#FFFDF8] text-[#6A5A48] border border-[#C5A059]/30'
            }`}
          >
            Dharma Crimson
          </button>
        </div>

        {/* Actions (Download & Copy) */}
        <div className="mt-6 flex items-center gap-3 w-full max-w-md">
          <button
            onClick={handleDownload}
            className="flex-1 py-3 px-4 rounded-xl bg-gradient-to-r from-[#E28743] via-[#C5A059] to-[#C5A059] text-[#F4ECE1] font-cinzel font-bold text-xs tracking-wider flex items-center justify-center gap-2 shadow-[0_0_20px_rgba(255,183,3,0.3)] hover:brightness-110 active:scale-[0.98] transition-all"
          >
            <Download className="w-4 h-4" />
            Download High-Res PNG
          </button>

          <button
            onClick={handleCopy}
            className="py-3 px-4 rounded-xl bg-[#FFFDF8] border border-[#C5A059]/30 text-[#2C261F] font-cinzel text-xs flex items-center gap-2 hover:bg-[#F4ECE1] hover:border-[#C5A059]/60 transition-all"
          >
            {copied ? (
              <>
                <Check className="w-4 h-4 text-emerald-400" />
                <span className="text-emerald-300">Copied!</span>
              </>
            ) : (
              <>
                <Copy className="w-4 h-4 text-[#C5A059]" />
                <span>Copy</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
