import { useEffect, useRef } from 'react';

/** Lightweight ambient layer: CSS mist plus a capped canvas of soft golden rain. */
export function SacredAtmosphere() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const context = canvas?.getContext('2d');
    if (!canvas || !context) return;
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const particles: Array<{ x: number; y: number; length: number; speed: number; drift: number; alpha: number }> = [];
    let width = 0;
    let height = 0;
    let animation = 0;
    const resize = () => {
      const ratio = Math.min(window.devicePixelRatio || 1, 1.5);
      width = window.innerWidth;
      height = window.innerHeight;
      canvas.width = Math.round(width * ratio);
      canvas.height = Math.round(height * ratio);
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      context.setTransform(ratio, 0, 0, ratio, 0, 0);
    };
    resize();
    window.addEventListener('resize', resize);
    const count = reducedMotion ? 0 : Math.min(52, Math.floor((width * height) / 28000));
    for (let i = 0; i < count; i += 1) particles.push({ x: Math.random() * width, y: Math.random() * height, length: 5 + Math.random() * 12, speed: 0.35 + Math.random() * 0.7, drift: 0.12 + Math.random() * 0.24, alpha: 0.12 + Math.random() * 0.16 });
    const draw = () => {
      context.clearRect(0, 0, width, height);
      for (const particle of particles) {
        context.beginPath();
        context.strokeStyle = `rgba(212, 175, 55, ${particle.alpha})`;
        context.lineWidth = 1;
        context.moveTo(particle.x, particle.y);
        context.lineTo(particle.x + particle.drift * particle.length, particle.y + particle.length);
        context.stroke();
        particle.x += particle.drift;
        particle.y += particle.speed;
        if (particle.y > height) { particle.y = -particle.length; particle.x = Math.random() * width; }
      }
      if (!reducedMotion) animation = window.requestAnimationFrame(draw);
    };
    if (!reducedMotion) animation = window.requestAnimationFrame(draw);
    return () => { window.removeEventListener('resize', resize); window.cancelAnimationFrame(animation); };
  }, []);

  return <div className="sacred-atmosphere" aria-hidden="true"><div className="sacred-cloud sacred-cloud-one" /><div className="sacred-cloud sacred-cloud-two" /><div className="sacred-cloud sacred-cloud-three" /><canvas ref={canvasRef} className="sacred-rain" /></div>;
}
