# VYOM — Bhagavad Gita Multimodal Intelligence

> **Ancient Wisdom. Infinite Understanding.**  
> A royal, source-grounded multimodal Bhagavad Gita intelligence platform powered by dense retrieval, conversational neighbor expansion, and a 3D Kurukshetra cinematic diorama.

---

## 🏛️ System Architecture

- **Backend (`/backend`)**:
  - FastAPI serving layer exposing `/api/ask` and `/api/health`.
  - Dense semantic search using BGE-M3 and Qdrant.
  - Conversational neighbor expansion (+1, +2 verses) preserving the dialogic flow between Lord Krishna and Arjuna.
  - Classical Sanskrit verse store covering all 701 verses with word-by-word meanings (*Pada-Artha*) and venerable commentaries (Adi Shankaracharya, Sri Ramanuja, Swami Chinmayananda).

- **Frontend (`/frontend`)**:
  - **Vite + React 18+ (TypeScript)** with Tailwind CSS and typography plugins.
  - **3D Kurukshetra Cinematic Diorama (`KurukshetraScene.tsx`)**: Built in Three.js and `@react-three/fiber`, featuring *Rathachakra-dhari Krishna* clutching aloft the glowing golden chariot wheel, surrendering Arjuna, the royal Kapi Dhwaja rath, cinematic orbiting controls, and golden sparks.
  - **Exact VYOM Serif Emblem (`VyomLogo.tsx`)**: High-contrast serif typography with the sacred calligraphic Om/divine feather motif soaring seamlessly from the letter 'V'.
  - **Sanskrit Audio Chanting Engine (`audioChant.ts`)**: Real-time Web Audio API synthesizer producing Indian classical Tanpura drone (Sa-Pa harmonic cycle) and Vedic Anushtup meter recitation.
  - **Royal Quote Card Studio (`QuoteCardModal.tsx`)**: High-resolution 1200x1200 canvas card generator with Devanagari calligraphy, Surya yantras, and 1-click PNG export.
  - **Graceful Error Masking**: Sanitized 502 error masking with a serene golden banner and offline grounded Gita wisdom fallback.

---

## ⚡ Quick Start & Concurrent Run

### 1. Environment Setup
Copy the environment template and insert your API credentials (e.g. Gemini, Groq, or Ollama):
```bash
cp .env.example backend/.env
```

### 2. Concurrent Dev Server (Frontend + Backend)
From the repository root:
```bash
# Standard / Unix / Activated Virtualenv
npm run dev

# Windows PowerShell / CMD with local venv:
npm run dev:win
```
This runs both:
- **Backend API**: `uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload`
- **Frontend Portal**: `vite` on `http://localhost:5173` (with `/api` proxied to port 8000)

### 3. Run Independently

**Frontend only:**
```bash
cd frontend
npm run dev
```

**Backend only:**
```bash
# Unix / Activated venv:
uvicorn backend.api.main:app --reload --port 8000

# Windows:
.\venv\Scripts\python.exe -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Production Build
```bash
npm run build
# or
npm run build:frontend
```

---

## 🎨 Royal Mahabharata Aesthetic Palette
- **Deep Cosmic Charcoal / Dark Obsidian**: `#0D0F12`, `#141820`
- **Royal Golden Cream**: `#F5E6C8`, `#E2C889`, `#C5A059`
- **Spiritual Surya Gold**: `#FFB703`, `#F59E0B`
- **Warm Ivory Typography**: `#FAF6ED`, `#E5DCC5`
- **Filigree Borders**: Fine 1px shimmer `rgba(226, 200, 137, 0.2)`
