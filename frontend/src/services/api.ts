import { lookupVerse } from '../data/gitaVerses';

export interface AskRequestPayload {
  query: string;
  top_k?: number;
}

export interface AskResponseData {
  query: string;
  routed: boolean;
  cited_verses: string[];
  answer: string;
  isOfflineFallback?: boolean;
}

export interface HealthResponseData {
  status: string;
  searcher_ready?: boolean;
  valid_ids_count?: number;
}

/**
 * Check backend health status
 */
export async function checkBackendHealth(): Promise<{ online: boolean; details?: HealthResponseData }> {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 2500);
    const res = await fetch('/api/health', {
      method: 'GET',
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (res.ok) {
      const data: HealthResponseData = await res.json();
      return { online: true, details: data };
    }
    return { online: false };
  } catch {
    return { online: false };
  }
}

/**
 * Query the VYOM RAG endpoint
 */
export async function askGitaQuestion(payload: AskRequestPayload): Promise<AskResponseData> {
  const top_k = payload.top_k ?? 5;

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 20000); // 20s timeout for LLM synthesis

    const res = await fetch('/api/ask', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ query: payload.query, top_k }),
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (res.status === 502) {
      throw new Error('502_GENERATION_ERROR');
    }

    if (!res.ok) {
      throw new Error(`HTTP_${res.status}`);
    }

    const data: AskResponseData = await res.json();
    return data;
  } catch (err: unknown) {
    const errMessage = err instanceof Error ? err.message : String(err);

    // Propagate 502 to trigger the serene golden banner
    if (errMessage === '502_GENERATION_ERROR') {
      throw new Error('The divine intelligence is contemplating deep synthesis. Please inquire again momentarily.');
    }

    // If backend is unreachable (e.g. not running on 8000), provide enlightened local fallback
    console.warn('[VYOM] Backend offline or unreachable. Providing local grounded Gita synthesis.', errMessage);
    return generateOfflineGitaWisdom(payload.query);
  }
}

/**
 * Local Grounded Synthesis Engine for when backend is offline
 */
function generateOfflineGitaWisdom(query: string): AskResponseData {
  const lower = query.toLowerCase();

  // 1. Direct Verse routing check
  const verseMatch = query.match(/(?:bg|gita|verse)?\s*([1-9]|1[0-8])\s*[\.:]\s*([1-9]|[1-6][0-9]|7[0-8])/i);
  if (verseMatch) {
    const vid = `${parseInt(verseMatch[1], 10)}.${parseInt(verseMatch[2], 10)}`;
    const found = lookupVerse(vid);
    if (found) {
      return {
        query,
        routed: true,
        cited_verses: [found.verse_id],
        answer: `### Sacred Discourse on Verse ${found.verse_id}\n\n**Sanskrit Shloka:**\n> ${found.sanskrit.replace(/\n/g, '  \n> ')}\n\n**Transliteration:**\n*${found.transliteration.replace(/\n/g, '  \n* ')}*\n\n**Word-by-Word Essence:**\n${found.word_meanings}\n\n**Translation (${found.author}):**\n"${found.translation}"\n\n**Philosophical Exposition:**\n${found.commentary_summary}\n\n*In the Kurukshetra of your daily life, apply this principle by detaching from ephemeral anxieties and anchoring your consciousness in steadfast devotion.*`,
        isOfflineFallback: true,
      };
    }
  }

  // 2. Surrender / Sharanagati
  if (lower.includes('surrender') || lower.includes('sharanagati') || lower.includes('refuge') || lower.includes('whom should i')) {
    return {
      query,
      routed: false,
      cited_verses: ['18.66', '9.22'],
      answer: `In the Bhagavad Gita, Lord Sri Krishna reveals that the supreme sanctuary for an earnest soul is absolute surrender (*Sharanagati*) to the Divine Supreme.\n\n### The Supreme Promise (Charama Shloka — BG 18.66)\n> *sarva-dharmān parityajya mām ekaṁ śharaṇaṁ vraja*\n> *ahaṁ tvāṁ sarva-pāpebhyo mokṣhayiṣhyāmi mā śhuchaḥ*\n\n*"Abandoning all duties and varieties of dharma, surrender unto Me alone. I will liberate you from all sins; grieve not."*\n\n### Key Teachings on Surrender:\n1. **Relinquishing the Illusion of Agency**: True surrender is not helplessness, but realizing that the individual ego (*Ahamkara*) is not the solitary master of destiny.\n2. **The Guarantee of Divine Care (BG 9.22)**: Krishna declares *Yoga-kshemam vahamy aham*—He Personally protects what the surrendered devotee possesses and grants what they lack.\n3. **Practical Application**: Surrender every action as an offering (*Yajna*), accepting favorable and unfavorable conditions with serene equanimity.`,
      isOfflineFallback: true,
    };
  }

  // 3. Karma Yoga / Duty / 2.47
  if (lower.includes('karma') || lower.includes('duty') || lower.includes('work') || lower.includes('action') || lower.includes('nishkama')) {
    return {
      query,
      routed: false,
      cited_verses: ['2.47'],
      answer: `The Bhagavad Gita articulates the foundational doctrine of **Nishkama Karma** (action performed without self-centered clinging to fruits).\n\n### The Sacred Maxim (BG 2.47)\n> *karmaṇy-evādhikāras te mā phaleṣhu kadāchana*\n> *mā karma-phala-hetur bhūr mā te saṅgo 'stvakarmaṇi*\n\n*"You have a right only to work, but never to its fruits. Let not the fruit of action be your motive, nor let your attachment be to inaction."*\n\n### Guiding Pillars:\n- **Full Presence in Execution**: Pour 100% of your energy, devotion, and cognitive presence into your prescribed duty.\n- **Equanimity in Outcome**: Success and failure are cosmic variables governed by multiple forces (*Kala*, *Karma*, *Prakriti*). Clinging to results produces debilitating anxiety.\n- **Immunity from Lethargy**: Krishna sternly warns against *akarma* (inertia or fatalistic surrender to laziness).`,
      isOfflineFallback: true,
    };
  }

  // 4. Fear / Death / Immortality / 2.20
  if (lower.includes('fear') || lower.includes('death') || lower.includes('soul') || lower.includes('atman') || lower.includes('failure')) {
    return {
      query,
      routed: false,
      cited_verses: ['2.20', '18.78'],
      answer: `Lord Krishna addresses Arjuna's paralyzing grief and fear by dismantling the false identification with the mortal physical shell.\n\n### Eternal Reality of the Self (BG 2.20)\n> *na jāyate mriyate vā kadāchin*\n> *nāyaṁ bhūtvā bhavitā vā na bhūyaḥ*\n> *ajo nityaḥ śhāśhvato 'yaṁ purāṇo na hanyate hanyamāne śharīre*\n\n*"The Atman is neither born nor does it ever die. It is unborn, eternal, everlasting and primeval; it is not destroyed when the physical body is destroyed."*\n\n### Overcoming Fear:\n- Fear is born of the illusion of separation and loss (*Moha*).\n- When you recognize yourself as the deathless Witness (*Sakshi*), external challenges cease to threaten your inherent core.\n- Stand upright with courageous resolve like Partha (*dhanur-dharaḥ*), confident that moral righteousness and divine grace guarantee inner victory.`,
      isOfflineFallback: true,
    };
  }

  // 5. Mind control / 6.5 / 6.35
  if (lower.includes('mind') || lower.includes('focus') || lower.includes('distraction') || lower.includes('meditation') || lower.includes('control')) {
    return {
      query,
      routed: false,
      cited_verses: ['6.5', '6.35'],
      answer: `When Arjuna laments that the mind is as turbulent as the raging gale wind (*vāyor iva su-duṣhkaram*), Krishna offers practical, non-dogmatic psychological discipline.\n\n### Self-Elevation (BG 6.5)\n*"Let a man lift himself by his own Self, let him not depress himself; for this Self alone is the friend of oneself, and this Self alone is the enemy of oneself."*\n\n### The Twofold Remedy (BG 6.35)\n> *abhyāsena tu kaunteya vairāgyeṇa cha gṛihyate*\n\n1. **Abhyasa (Persistent Practice)**: Gently and consistently redirecting the drifting mind back to its center without frustration.\n2. **Vairagya (Dispassionate Detachment)**: Discerning the transient nature of sensory cravings and mental agitation, refusing to feed reactionary thoughts.`,
      isOfflineFallback: true,
    };
  }

  // General Synthesis Default
  return {
    query,
    routed: false,
    cited_verses: ['2.47', '18.66'],
    answer: `In response to your inquiry regarding *"${query}"*, the wisdom of the Bhagavad Gita invites you to harmonize duty (*Dharma*), unwavering discernment (*Buddhi Yoga*), and loving devotion (*Bhakti*).\n\nWhen we offer each moment with reverence without attachment to personal gain (as enunciated in **BG 2.47**), the turbulence of the heart subsides. Surrendering outcomes to the Supreme Divine (**BG 18.66**) transforms life's battlefield into a sacred pathway of self-realization.`,
    isOfflineFallback: true,
  };
}
