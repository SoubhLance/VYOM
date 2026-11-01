/**
 * Shared audio exclusivity coordinator for VYOM.
 * Coordinates between ambient background music, verse clip players, and sacred listening.
 */

let currentPlayingClip: HTMLAudioElement | null = null;
let wasBgMusicPlayingBeforeClip = false;

export function stopAllClips(): void {
  if (currentPlayingClip) {
    currentPlayingClip.pause();
    currentPlayingClip = null;
  }
}

export function onClipPlayStart(clipAudio: HTMLAudioElement): void {
  // 1. Pause any other clip currently playing
  if (currentPlayingClip && currentPlayingClip !== clipAudio) {
    currentPlayingClip.pause();
  }
  currentPlayingClip = clipAudio;

  // 2. Pause background music if it was playing
  const bgAudio = document.querySelector('audio[src="/bg_music.mp3"]') as HTMLAudioElement | null;
  if (bgAudio && !bgAudio.paused) {
    wasBgMusicPlayingBeforeClip = true;
    bgAudio.pause();
  }
}

export function onClipPlayEndOrPause(clipAudio: HTMLAudioElement): void {
  if (currentPlayingClip === clipAudio) {
    currentPlayingClip = null;

    // Resume bg_music only if no clip is playing and music was on before
    setTimeout(() => {
      if (!currentPlayingClip && wasBgMusicPlayingBeforeClip) {
        wasBgMusicPlayingBeforeClip = false;
        const bgAudio = document.querySelector('audio[src="/bg_music.mp3"]') as HTMLAudioElement | null;
        bgAudio?.play().catch(() => {});
      }
    }, 150);
  }
}

