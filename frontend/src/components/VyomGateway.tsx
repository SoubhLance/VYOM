import { useEffect, useRef } from 'react';
import { sampleMark } from '../utils/sampleMark';
import './VyomGateway.css';

const LAYERS = 7; // extrusion depth of the 3D logo
const CONVERGE_MS = 850; // embers gather into the mark
const RELAX_MS = 1400; // then drift up as slow embers
const EMBER_COLORS = ['245,230,200', '212,175,55', '226,135,67']; // cream #F5E6C8, filigree #D4AF37, surya #E28743

interface Particle {
  x: number;
  y: number;
  sx: number;
  sy: number;
  tx: number;
  ty: number;
  r: number;
  color: string;
  delay: number;
  vy: number;
  vx: number;
  life: number;
  keep: boolean;
}

const prefersReducedMotion = () =>
  typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

/**
 * Full-screen ember field. Embers drift in and gather into the VYOM mark, then relax into a slow
 * upward drift; only a few keep drifting. Not rendered at all under reduced motion.
 */
function EmberField({ targetRef }: { targetRef: React.RefObject<HTMLDivElement | null> }) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const target = targetRef.current;
    if (!canvas || !target) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let frame = 0;
    let stopped = false;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const narrow = window.innerWidth < 768;
    const gatherCount = narrow ? 380 : 700;
    const keepCount = narrow ? 28 : 55;
    let width = 0;
    let height = 0;
    const resize = () => {
      width = window.innerWidth;
      height = window.innerHeight;
      canvas.width = Math.round(width * dpr);
      canvas.height = Math.round(height * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize();
    window.addEventListener('resize', resize);

    let particles: Particle[] = [];
    let start = 0;

    const spawnDrifter = (p: Particle, fromBottom: boolean) => {
      p.x = Math.random() * width;
      p.y = fromBottom ? height + Math.random() * 40 : p.y;
      p.vy = -(0.12 + Math.random() * 0.28);
      p.vx = (Math.random() - 0.5) * 0.12;
      p.life = 1;
    };

    const draw = (now: number) => {
      if (stopped) return;
      if (!start) start = now;
      const t = now - start;
      ctx.clearRect(0, 0, width, height);
      let currentColor = '';
      for (const p of particles) {
        let alpha: number;
        if (t < CONVERGE_MS + p.delay) {
          const k = Math.max(0, Math.min(1, (t - p.delay) / CONVERGE_MS));
          const e = 1 - (1 - k) ** 3; // ease-out cubic
          p.x = p.sx + (p.tx - p.sx) * e;
          p.y = p.sy + (p.ty - p.sy) * e;
          alpha = 0.25 + 0.65 * e;
        } else if (t < RELAX_MS) {
          alpha = 0.9 - ((t - CONVERGE_MS) / (RELAX_MS - CONVERGE_MS)) * (p.keep ? 0.45 : 0.9);
          p.y -= 0.15;
        } else {
          if (!p.keep) continue;
          if (p.vy === 0) spawnDrifter(p, false);
          p.x += p.vx;
          p.y += p.vy;
          p.life -= 0.0016;
          if (p.y < -10 || p.life <= 0) spawnDrifter(p, true);
          alpha = 0.45 * Math.min(1, p.life * 1.5);
        }
        if (p.color !== currentColor) {
          currentColor = p.color;
          ctx.fillStyle = `rgb(${p.color})`;
        }
        ctx.globalAlpha = Math.max(0, Math.min(1, alpha));
        ctx.fillRect(p.x - p.r, p.y - p.r, p.r * 2, p.r * 2);
      }
      ctx.globalAlpha = 1;
      if (t > RELAX_MS) particles = particles.filter((p) => p.keep);
      frame = requestAnimationFrame(draw);
    };

    const onVisibility = () => {
      if (document.hidden) cancelAnimationFrame(frame);
      else if (!stopped) frame = requestAnimationFrame(draw);
    };
    document.addEventListener('visibilitychange', onVisibility);

    void sampleMark(target.getBoundingClientRect(), gatherCount)
      .then((points) => {
        if (stopped) return;
        particles = points.map(([tx, ty], i) => {
          const angle = Math.random() * Math.PI * 2;
          const dist = Math.max(width, height) * (0.45 + Math.random() * 0.4);
          return {
            sx: width / 2 + Math.cos(angle) * dist,
            sy: height / 2 + Math.sin(angle) * dist,
            x: 0,
            y: 0,
            tx,
            ty,
            r: 0.5 + Math.random() * 0.75,
            color: EMBER_COLORS[Math.floor((i / points.length) * EMBER_COLORS.length)],
            delay: Math.random() * 120,
            vx: 0,
            vy: 0,
            life: 1,
            keep: i % Math.max(1, Math.round(points.length / keepCount)) === 0,
          };
        });
        frame = requestAnimationFrame(draw);
      })
      .catch(() => { /* the static logo still shows */ });

    return () => {
      stopped = true;
      cancelAnimationFrame(frame);
      window.removeEventListener('resize', resize);
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, [targetRef]);

  return <canvas ref={canvasRef} className="vyom-gateway-embers" aria-hidden="true" />;
}

interface VyomGatewayProps {
  fading: boolean;
  onSkip: () => void;
}

/** Loading screen: a layered 3D VYOM mark that embers gather into. Click, tap, Enter or Esc skips. */
export function VyomGateway({ fading, onSkip }: VyomGatewayProps) {
  const logoRef = useRef<HTMLDivElement | null>(null);
  const reduced = prefersReducedMotion();

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Enter' || event.key === 'Escape' || event.key === ' ') onSkip();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onSkip]);

  return (
    <div
      className={`vyom-gateway fixed inset-0 z-50 overflow-hidden transition-opacity duration-[800ms] ${fading ? 'opacity-0' : 'opacity-100'}`}
      onClick={onSkip}
      role="presentation"
    >
      {!reduced && <EmberField targetRef={logoRef} />}
      <div className="absolute right-5 top-5 z-10">
        <button
          type="button"
          onClick={(event) => { event.stopPropagation(); onSkip(); }}
          className="rounded-full border border-[#F5E6C8]/50 bg-[#34291ecc] px-4 py-2 text-xs font-medium text-[#FFF9EA] backdrop-blur-md transition hover:bg-[#57462c]"
        >
          Enter <span aria-hidden="true">→</span>
        </button>
      </div>
      <div className="relative z-[1] flex h-full flex-col items-center justify-center gap-6 px-4 text-center">
        <div className="vyom-gateway-stage" ref={logoRef} role="img" aria-label="VYOM">
          <div className="vyom-gateway-glow" />
          <div className="vyom-gateway-stack">
            {Array.from({ length: LAYERS }, (_, i) => (
              <span
                key={i}
                className={`vyom-gateway-layer ${i === LAYERS - 1 ? 'is-face' : ''}`}
                style={{ transform: `translateZ(${(i - (LAYERS - 1)) * 1.6}px)` }}
              />
            ))}
          </div>
        </div>
        <div className="vyom-gateway-caption">
          <p className="font-cinzel text-xs tracking-[0.22em] text-[#F5E6C8]">Bhagavad Gita Multimodal Intelligence</p>
          <p className="mt-2 text-xs text-[#FFF9EA]/70">Entering the sanctuary…</p>
        </div>
      </div>
    </div>
  );
}
