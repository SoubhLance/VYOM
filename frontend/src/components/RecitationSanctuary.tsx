import { GitaBookReader } from './GitaBookReader';

interface RecitationSanctuaryProps {
  onClose: () => void;
  initialVerseId?: string | null;
}

/** Compatibility entry point for the full-page scripture reader. */
export function RecitationSanctuary({ onClose, initialVerseId }: RecitationSanctuaryProps) {
  return <GitaBookReader onBack={onClose} initialVerseId={initialVerseId} />;
}
