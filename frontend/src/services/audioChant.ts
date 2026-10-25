/**
 * Sacred Sanskrit Chanting & Tanpura Synthesis Engine using Web Audio API
 */

class SanskritAudioEngine {
  private ctx: AudioContext | null = null;
  private isPlaying: boolean = false;
  private droneInterval: number | null = null;
  private chantTimeout: number | null = null;
  private masterGain: GainNode | null = null;
  private analyser: AnalyserNode | null = null;
  private currentShloka: string = '';

  private initContext() {
    if (!this.ctx) {
      const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      this.ctx = new AudioCtx();

      this.masterGain = this.ctx.createGain();
      this.masterGain.gain.setValueAtTime(0.35, this.ctx.currentTime);

      this.analyser = this.ctx.createAnalyser();
      this.analyser.fftSize = 64;

      this.masterGain.connect(this.analyser);
      this.analyser.connect(this.ctx.destination);
    }

    if (this.ctx.state === 'suspended') {
      this.ctx.resume();
    }
  }

  /**
   * Play a resonant sacred temple bell / bronze chime
   */
  public playTempleBell(freq: number = 880) {
    this.initContext();
    if (!this.ctx || !this.masterGain) return;

    const t = this.ctx.currentTime;
    const osc1 = this.ctx.createOscillator();
    const osc2 = this.ctx.createOscillator();
    const gain = this.ctx.createGain();

    osc1.type = 'sine';
    osc1.frequency.setValueAtTime(freq, t);
    osc2.type = 'triangle';
    osc2.frequency.setValueAtTime(freq * 1.503, t); // rich overtone

    gain.gain.setValueAtTime(0.2, t);
    gain.gain.exponentialRampToValueAtTime(0.0001, t + 3.5);

    osc1.connect(gain);
    osc2.connect(gain);
    gain.connect(this.masterGain);

    osc1.start(t);
    osc2.start(t);
    osc1.stop(t + 3.6);
    osc2.stop(t + 3.6);
  }

  /**
   * Synthesize Tanpura Pluck (String 1 to 4)
   * Traditional Pa (207.65 Hz), Sa' (277.18 Hz), Sa' (277.18 Hz), Kharaj Sa (138.59 Hz)
   */
  private pluckTanpuraString(freq: number, panOffset: number = 0) {
    if (!this.ctx || !this.masterGain) return;
    const t = this.ctx.currentTime;

    const osc = this.ctx.createOscillator();
    const subOsc = this.ctx.createOscillator();
    const filter = this.ctx.createBiquadFilter();
    const panner = this.ctx.createStereoPanner ? this.ctx.createStereoPanner() : null;
    const gain = this.ctx.createGain();

    osc.type = 'sawtooth';
    osc.frequency.setValueAtTime(freq, t);

    subOsc.type = 'sine';
    subOsc.frequency.setValueAtTime(freq * 2, t);

    // Warm resonant acoustic cavity filter
    filter.type = 'bandpass';
    filter.frequency.setValueAtTime(freq * 2.8, t);
    filter.Q.setValueAtTime(3.2, t);

    // Jawari / buzz harmonic envelope
    gain.gain.setValueAtTime(0.001, t);
    gain.gain.linearRampToValueAtTime(0.18, t + 0.08);
    gain.gain.exponentialRampToValueAtTime(0.0001, t + 4.2);

    osc.connect(filter);
    subOsc.connect(filter);
    filter.connect(gain);

    if (panner) {
      panner.pan.setValueAtTime(panOffset, t);
      gain.connect(panner);
      panner.connect(this.masterGain);
    } else {
      gain.connect(this.masterGain);
    }

    osc.start(t);
    subOsc.start(t);
    osc.stop(t + 4.5);
    subOsc.stop(t + 4.5);
  }

  /**
   * Start Indian Classical Drone Loop (Sa-Pa cycle)
   */
  private startTanpuraDrone() {
    // Key of C# (Sa = 138.59 Hz, Pa = 207.65 Hz, High Sa = 277.18 Hz)
    const strings = [
      { f: 207.65, pan: -0.4 }, // Pa
      { f: 277.18, pan: -0.1 }, // Sa'
      { f: 277.18, pan: 0.1 },  // Sa'
      { f: 138.59, pan: 0.35 }, // Kharaj Sa
    ];

    let currentString = 0;
    this.pluckTanpuraString(strings[0].f, strings[0].pan);

    this.droneInterval = window.setInterval(() => {
      currentString = (currentString + 1) % strings.length;
      const s = strings[currentString];
      this.pluckTanpuraString(s.f, s.pan);
    }, 1200);
  }

  /**
   * Sing Vedic Chanting Syllable with Classical Svarita / Udatta intonation
   */
  private chantTone(freq: number, duration: number, timeOffset: number) {
    if (!this.ctx || !this.masterGain) return;
    const t = this.ctx.currentTime + timeOffset;

    const osc = this.ctx.createOscillator();
    const vibrato = this.ctx.createOscillator();
    const vibratoGain = this.ctx.createGain();
    const formant = this.ctx.createBiquadFilter();
    const gain = this.ctx.createGain();

    osc.type = 'triangle';
    osc.frequency.setValueAtTime(freq, t);

    // Vocal vibrato
    vibrato.frequency.setValueAtTime(5.2, t);
    vibratoGain.gain.setValueAtTime(1.8, t);
    vibrato.connect(osc.frequency);

    // Vocal vocalic vowel formant (O/A resonance)
    formant.type = 'lowpass';
    formant.frequency.setValueAtTime(750, t);
    formant.Q.setValueAtTime(4.0, t);

    // Smooth vocal chanting attack and release
    gain.gain.setValueAtTime(0.0001, t);
    gain.gain.linearRampToValueAtTime(0.22, t + 0.12);
    gain.gain.setValueAtTime(0.18, t + duration - 0.15);
    gain.gain.exponentialRampToValueAtTime(0.0001, t + duration);

    osc.connect(formant);
    formant.connect(gain);
    gain.connect(this.masterGain);

    osc.start(t);
    vibrato.start(t);
    osc.stop(t + duration);
    vibrato.stop(t + duration);
  }

  /**
   * Play shloka chanting in authentic Vedic meter (Anushtup meter)
   */
  public playShlokaChant(
    sanskritText: string,
    transliteration: string,
    onEnded?: () => void
  ) {
    this.stop();
    this.initContext();
    this.isPlaying = true;
    this.currentShloka = sanskritText;

    // Ring auspicious entry bell
    this.playTempleBell(587.33); // D5

    // Start soothing background Tanpura drone
    this.startTanpuraDrone();

    // Vedic Anushtup meter scale (C# - D# - E - F# - G#)
    const Sa = 138.59;
    const Re = 155.56;
    const Ga = 174.61;
    const Ma = 185.0;
    const Pa = 207.65;
    const Dha = 233.08;

    // Classical chanting pitch contour
    const melody = [
      Sa * 1.5, Sa * 1.5, Ga * 1.5, Ma * 1.5, Pa * 1.5, Pa * 1.5, Ma * 1.5, Ga * 1.5,
      Sa * 1.5, Re * 1.5, Ga * 1.5, Ga * 1.5, Re * 1.5, Sa * 1.5, Sa * 1.5, Sa * 1.5,
      Pa * 1.5, Dha * 1.5, Pa * 1.5, Ma * 1.5, Ga * 1.5, Ma * 1.5, Pa * 1.5, Pa * 1.5,
      Ma * 1.5, Ga * 1.5, Re * 1.5, Ga * 1.5, Re * 1.5, Sa * 1.5, Sa * 1.5, Sa * 1.5
    ];

    let delay = 1.0;
    const noteDuration = 0.48;

    melody.forEach((pitch) => {
      this.chantTone(pitch, noteDuration, delay);
      delay += noteDuration;
    });

    // Also utilize Web Speech API with serene Sanskrit pitch if available in browser
    if ('speechSynthesis' in window) {
      try {
        const utterance = new SpeechSynthesisUtterance(transliteration || sanskritText);
        utterance.rate = 0.78;
        utterance.pitch = 0.9;
        utterance.volume = 0.45;
        // Try to pick Sanskrit / Hindi voice if found
        const voices = window.speechSynthesis.getVoices();
        const indianVoice = voices.find(v => v.lang.includes('hi') || v.lang.includes('sa') || v.name.includes('India'));
        if (indianVoice) {
          utterance.voice = indianVoice;
        }
        setTimeout(() => {
          if (this.isPlaying) {
            window.speechSynthesis.speak(utterance);
          }
        }, 1200);
      } catch {
        // Audio synthesis takes care
      }
    }

    const totalDuration = (delay + 3.0) * 1000;
    this.chantTimeout = window.setTimeout(() => {
      this.playTempleBell(440);
      setTimeout(() => {
        this.stop();
        if (onEnded) onEnded();
      }, 3000);
    }, totalDuration);
  }

  public stop() {
    this.isPlaying = false;
    this.currentShloka = '';

    if (this.droneInterval !== null) {
      clearInterval(this.droneInterval);
      this.droneInterval = null;
    }

    if (this.chantTimeout !== null) {
      clearTimeout(this.chantTimeout);
      this.chantTimeout = null;
    }

    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
  }

  public getIsPlaying(): boolean {
    return this.isPlaying;
  }

  public getCurrentShloka(): string {
    return this.currentShloka;
  }

  public getFrequencyData(): Uint8Array | null {
    if (!this.analyser) return null;
    const data = new Uint8Array(this.analyser.frequencyBinCount);
    this.analyser.getByteFrequencyData(data);
    return data;
  }
}

export const SanskritAudio = new SanskritAudioEngine();
