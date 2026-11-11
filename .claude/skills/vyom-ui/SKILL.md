---
name: vyom-ui
description: Use whenever editing any VYOM frontend component or styling (frontend/src/**/*.tsx, *.css).
---

# VYOM UI tokens (from the code; use these, don't invent new ones)

Colours are Tailwind arbitrary values, e.g. `text-[#2C261F]`. The `:root` vars in `src/index.css` exist but TSX doesn't use them.

- Page #FAF6EB · surface #F4ECE1 · elevated #EDE3D2 · card fill #FFFDF8 (at /65–/90)
- Gold #C5A059 (main accent; borders at /20–/50) · deep gold #A27427 · filigree #D4AF37 · cream #F5E6C8
- Surya #E28743 (icons, section headings; primary button `bg-gradient-to-r from-[#E28743] to-[#C5A059]`)
- Text #2C261F · muted #6A5A48 · maroon headings #8C2D19 · brown #4B3825 (/35 for modal scrims)

Fonts (loaded in `index.html`): `font-cinzel` for headings and labels (often uppercase with `tracking-[0.18em]`); Plus Jakarta Sans for body (the default); `font-sanskrit` = Tiro Devanagari Sanskrit. `GitaBookReader.css` adds a Noto Serif Devanagari fallback and uses Georgia for prose.

Surfaces: `.royal-card` / `.filigree-card` (ivory at 0.94–0.95, gold border at 0.35, no backdrop blur, shadow `0 10px 30px rgba(180,140,75,.08)`), plus `.subtle-gold-glow` and `.gold-glow`. Corners: `rounded-xl` by default, `rounded-2xl` for cards and modals, `rounded-full` for pills.

Mist: `SacredAtmosphere` clouds (blur 55px, opacity .15–.24, 45–66 s drift; off under reduced motion).

Motion: gateway fade 800ms · page turn 300ms ease-out · drawer 220ms · book open 720ms `cubic-bezier(0.2,0.75,0.25,1)` · hovers 180–300ms · ambient loops 3–4s.

Breakpoints: Tailwind `sm`, `md` and `lg`; the reader CSS switches at 768px.

# Rules

1. Reuse the tokens, classes and components above (`VyomLogo`, `ClipPlayer`, `VerseDetailModal`, the cards). Ask before adding any new colour, font, shadow or animation.
2. All audio goes through `src/services/audioCoordinator.ts`: call `onClipPlayStart` and `onClipPlayEndOrPause` (or `stopAllClips`). Never use Web Audio synthesis or `speechSynthesis`.
3. Every Devanagari string gets `font-sanskrit` and `lang="sa"`.
4. Check at 375px and at desktop width. Anything you didn't see yourself is UNVERIFIED.
5. Keep the sanctuary calm: no flashy effects, neon, bouncing or loops faster than 3s. Every new animation must respect `prefers-reduced-motion`.

Known traps: `font-cinzel-dec` points at Cinzel Decorative, which is not loaded; `RecitationSanctuary.tsx` is not mounted (leave it until the owner decides). `animate-fade-in` is defined in `index.css` (200 ms fade). Never put `backdrop-filter` blur on surfaces over the animated background: it re-blurs every frame and caused the lag fixed on 2026-11-12.
