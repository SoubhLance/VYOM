export const MARK_SRC = '/vyom-mark.webp';
export const MARK_RATIO = 528 / 900; // height / width of vyom-mark.webp

/** Opaque points of the VYOM mark, mapped into an on-screen box (CSS pixels), shuffled. */
export async function sampleMark(box: DOMRect, count: number): Promise<Array<[number, number]>> {
  const img = new Image();
  img.src = MARK_SRC;
  await img.decode();
  const w = Math.max(90, Math.round(box.width / 1.5));
  const h = Math.max(36, Math.round(w * MARK_RATIO));
  const off = document.createElement('canvas');
  off.width = w;
  off.height = h;
  const ctx = off.getContext('2d', { willReadFrequently: true });
  if (!ctx) return [];
  ctx.drawImage(img, 0, 0, w, h);
  const data = ctx.getImageData(0, 0, w, h).data;
  const points: Array<[number, number]> = [];
  for (let y = 0; y < h; y += 1) {
    for (let x = 0; x < w; x += 1) {
      if (data[(y * w + x) * 4 + 3] > 140) points.push([box.left + (x / w) * box.width, box.top + (y / h) * box.height]);
    }
  }
  for (let i = points.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [points[i], points[j]] = [points[j], points[i]];
  }
  return points.slice(0, count);
}
