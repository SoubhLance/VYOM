import shlokaData from './shlokaDirectory.json';

export interface ShlokaItem {
  verseId: string;
  chapter: number;
  verseNumber: number;
  sanskrit: string;
  transliteration?: string;
  audio_url: string;
  clip_id: string;
}

export interface ChapterMeta {
  chapter: number;
  sanskritName: string;
  englishTitle: string;
  totalVerses: number;
}

export const CHAPTER_METAS: ChapterMeta[] = [
  { chapter: 1, sanskritName: 'अर्जुनविषादयोग', englishTitle: 'Arjuna Vishada Yoga', totalVerses: 47 },
  { chapter: 2, sanskritName: 'सांख्ययोग', englishTitle: 'Sankhya Yoga', totalVerses: 72 },
  { chapter: 3, sanskritName: 'कर्मयोग', englishTitle: 'Karma Yoga', totalVerses: 43 },
  { chapter: 4, sanskritName: 'ज्ञानकर्मसंन्यासयोग', englishTitle: 'Jnana Karma Sannyasa Yoga', totalVerses: 42 },
  { chapter: 5, sanskritName: 'कर्मसंन्यासयोग', englishTitle: 'Karma Sannyasa Yoga', totalVerses: 29 },
  { chapter: 6, sanskritName: 'आत्मसंयमयोग', englishTitle: 'Atma Samyama / Dhyana Yoga', totalVerses: 47 },
  { chapter: 7, sanskritName: 'ज्ञानविज्ञानयोग', englishTitle: 'Jnana Vijnana Yoga', totalVerses: 30 },
  { chapter: 8, sanskritName: 'अक्षरब्रह्मयोग', englishTitle: 'Akshara Brahma Yoga', totalVerses: 28 },
  { chapter: 9, sanskritName: 'राजविद्याराजगुह्ययोग', englishTitle: 'Raja Vidya Raja Guhya Yoga', totalVerses: 34 },
  { chapter: 10, sanskritName: 'विभूतियोग', englishTitle: 'Vibhuti Yoga', totalVerses: 42 },
  { chapter: 11, sanskritName: 'विश्वरूपदर्शनयोग', englishTitle: 'Vishwarupa Darshana Yoga', totalVerses: 55 },
  { chapter: 12, sanskritName: 'भक्तियोग', englishTitle: 'Bhakti Yoga', totalVerses: 20 },
  { chapter: 13, sanskritName: 'क्षेत्रक्षेत्रज्ञविभागयोग', englishTitle: 'Kshetra Kshetrajna Vibhaga Yoga', totalVerses: 35 },
  { chapter: 14, sanskritName: 'गुणत्रयविभागयोग', englishTitle: 'Gunatraya Vibhaga Yoga', totalVerses: 27 },
  { chapter: 15, sanskritName: 'पुरुषोत्तमयोग', englishTitle: 'Purushottama Yoga', totalVerses: 20 },
  { chapter: 16, sanskritName: 'दैवासुरसम्पद्विभागयोग', englishTitle: 'Daivasura Sampad Vibhaga Yoga', totalVerses: 24 },
  { chapter: 17, sanskritName: 'श्रद्धात्रयविभागयोग', englishTitle: 'Shraddhatraya Vibhaga Yoga', totalVerses: 28 },
  { chapter: 18, sanskritName: 'मोक्षसंन्यासयोग', englishTitle: 'Moksha Sannyasa Yoga', totalVerses: 78 },
];

export const SHLOKA_DIRECTORY: ShlokaItem[] = shlokaData as ShlokaItem[];

