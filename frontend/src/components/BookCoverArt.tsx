/**
 * Ornamental Gita cover art drawn in SVG from the theme tokens (maroon #8C2D19 / #4B3825 / #24060B,
 * golds #D4AF37 #C5A059 #A27427, cream #F5E6C8, surya #E28743): sun rays, a double lotus mandala
 * and ॐ at the centre. Replaces the old raster cover whose source and licence were unknown.
 */
const PETAL = 'M0,0 C13,-18 13,-40 0,-54 C-13,-40 -13,-18 0,0Z';

export function BookCoverArt() {
  return (
    <svg viewBox="0 0 300 360" preserveAspectRatio="xMidYMid slice" role="img" aria-label="Ornamental cover: a lotus mandala around Om" className="block h-full w-full">
      <defs>
        <radialGradient id="vyomcover-field" cx="50%" cy="50%" r="75%">
          <stop offset="0%" stopColor="#8C2D19" />
          <stop offset="55%" stopColor="#4B3825" />
          <stop offset="100%" stopColor="#24060B" />
        </radialGradient>
        <linearGradient id="vyomcover-gold" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#F5E6C8" />
          <stop offset="45%" stopColor="#D4AF37" />
          <stop offset="100%" stopColor="#A27427" />
        </linearGradient>
      </defs>

      <rect width="300" height="360" fill="url(#vyomcover-field)" />

      <g transform="translate(150 180)">
        {/* sun rays */}
        <g stroke="#E28743" strokeOpacity="0.28" strokeWidth="1">
          {Array.from({ length: 36 }, (_, i) => (
            <line key={i} x1="0" y1="-114" x2="0" y2={i % 2 ? -138 : -156} transform={`rotate(${i * 10})`} />
          ))}
        </g>
        <circle r="110" fill="none" stroke="#C5A059" strokeOpacity="0.55" strokeWidth="0.8" strokeDasharray="2 4" />
        <circle r="104" fill="none" stroke="#D4AF37" strokeOpacity="0.8" strokeWidth="1.2" />

        {/* outer and inner lotus petals */}
        <g fill="#D4AF37" fillOpacity="0.1" stroke="#C5A059" strokeWidth="1">
          {Array.from({ length: 12 }, (_, i) => (
            <path key={i} d={PETAL} transform={`rotate(${i * 30}) translate(0 -46)`} />
          ))}
        </g>
        <g fill="#8C2D19" fillOpacity="0.55" stroke="#D4AF37" strokeWidth="0.9">
          {Array.from({ length: 12 }, (_, i) => (
            <path key={i} d={PETAL} transform={`rotate(${i * 30 + 15}) translate(0 -40) scale(0.78)`} />
          ))}
        </g>

        <circle r="44" fill="#24060B" stroke="url(#vyomcover-gold)" strokeWidth="2" />
        <circle r="38" fill="none" stroke="#C5A059" strokeOpacity="0.5" strokeWidth="0.8" />
        <text
          className="font-sanskrit"
          lang="sa"
          y="20"
          textAnchor="middle"
          fontSize="58"
          fill="url(#vyomcover-gold)"
        >
          ॐ
        </text>
      </g>

      {/* corner flourishes */}
      <g fill="none" stroke="#C5A059" strokeOpacity="0.6" strokeWidth="1">
        {[[14, 14, 0], [286, 14, 90], [286, 346, 180], [14, 346, 270]].map(([x, y, r]) => (
          <g key={`${x}-${y}`} transform={`translate(${x} ${y}) rotate(${r})`}>
            <path d="M0,34 Q0,0 34,0" />
            <path d="M6,26 Q6,6 26,6" strokeOpacity="0.45" />
            <circle cx="10" cy="10" r="2" fill="#D4AF37" stroke="none" />
          </g>
        ))}
      </g>
    </svg>
  );
}
