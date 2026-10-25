export interface GitaVerse {
  verse_id: string; // e.g. "2.47"
  chapter: number;
  verse: number;
  sanskrit: string;
  transliteration: string;
  word_meanings: string;
  translation: string;
  author: string;
  commentary_summary: string;
  theme: string;
}

export const GITA_VERSES: Record<string, GitaVerse> = {
  "2.47": {
    verse_id: "2.47",
    chapter: 2,
    verse: 47,
    sanskrit: "कर्मण्येवाधिकारस्ते मा फलेषु कदाचन।\nमा कर्मफलहेतुर्भूर्मा ते सङ्गोऽस्त्वकर्मणि॥",
    transliteration: "karmaṇy-evādhikāras te mā phaleṣhu kadāchana\nmā karma-phala-hetur bhūr mā te saṅgo 'stvakarmaṇi",
    word_meanings: "karmaṇi—in prescribed duty; eva—only; adhikāraḥ—right; te—of you; mā—not; phaleṣhu—in the fruits; kadāchana—at any time; mā—never; karma-phala-hetuḥ—motivated by the fruits of action; bhūḥ—be; mā—not; te—your; saṅgaḥ—attachment; astu—be; akarmaṇi—in inaction",
    translation: "You have a right to perform your prescribed duty, but you are not entitled to the fruits of action. Never consider yourself the cause of the results of your activities, and never be attached to inaction.",
    author: "Swami Sivananda",
    commentary_summary: "Sri Krishna reveals the foundational principle of Nishkama Karma (selfless action). By relinquishing anxiety over future outcomes, the mind attains serene clarity and performs work with supreme mastery without psychological burden.",
    theme: "Duty, Selfless Action (Nishkama Karma)"
  },
  "18.66": {
    verse_id: "18.66",
    chapter: 18,
    verse: 66,
    sanskrit: "सर्वधर्मान्परित्यज्य मामेकं शरणं व्रज।\nअहं त्वां सर्वपापेभ्यो मोक्षयिष्यामि मा शुचः॥",
    transliteration: "sarva-dharmān parityajya mām ekaṁ śharaṇaṁ vraja\nahaṁ tvāṁ sarva-pāpebhyo mokṣhayiṣhyāmi mā śhuchaḥ",
    word_meanings: "sarva-dharmān—all varieties of dharmas/duties; parityajya—abandoning; mām—unto Me; ekam—alone; śharaṇam—refuge; vraja—take; aham—I; tvām—you; sarva—from all; pāpebhyaḥ—sins; mokṣhayiṣhyāmi—shall liberate; mā—do not; śhuchaḥ—grieve",
    translation: "Abandoning all duties and concepts of righteousness, take refuge in Me alone. I will liberate you from all sins; do not grieve.",
    author: "Swami Adidevananda",
    commentary_summary: "The pinnacle (Charama Shloka) of the Bhagavad Gita. Sri Ramanujacharya explains that when an earnest soul surrenders all egoistic claims of being the doer, God Himself assumes complete responsibility for their ultimate spiritual liberation.",
    theme: "Absolute Surrender (Sharanagati / Prapatti)"
  },
  "2.20": {
    verse_id: "2.20",
    chapter: 2,
    verse: 20,
    sanskrit: "न जायते म्रियते वा कदाचिन्\nनायं भूत्वा भविता वा न भूयः।\nअजो नित्यः शाश्वतोऽयं पुराणो\nन हन्यते हन्यमाने शरीरे॥",
    transliteration: "na jāyate mriyate vā kadāchin\nnāyaṁ bhūtvā bhavitā vā na bhūyaḥ\najo nityaḥ śhāśhvato 'yaṁ purāṇo\nna hanyate hanyamāne śharīre",
    word_meanings: "na—never; jāyate—is born; mriyate—dies; vā—or; kadāchit—at any time; na—not; ayam—this; bhūtvā—having come into being; bhavitā—will come into being; vā—or; na—not; bhūyaḥ—again; ajaḥ—unborn; nityaḥ—eternal; śhāśhvataḥ—everlasting; ayam—this; purāṇaḥ—primeval; na—not; hanyate—is slain; hanyamāne—when is slain; śharīre—in the body",
    translation: "The soul is never born, nor does it die at any time. It has not come into being, does not come into being, and will not come into being. It is unborn, eternal, everlasting, and primeval. It is not slain when the body is slain.",
    author: "Swami Sivananda",
    commentary_summary: "Adi Shankaracharya emphasizes the unchanging, deathless nature of the Atman (pure consciousness). Fear of bodily mortality dissolves when one realizes the indestructible eternity of the inner witness.",
    theme: "Immortality of the Soul (Atma Tattva)"
  },
  "4.7": {
    verse_id: "4.7",
    chapter: 4,
    verse: 7,
    sanskrit: "यदा यदा हि धर्मस्य ग्लानिर्भवति भारत।\nअभ्युत्थानमधर्मस्य तदात्मानं सृजाम्यहम्॥",
    transliteration: "yadā yadā hi dharmasya glānir bhavati bhārata\nabhyutthānam adharmasya tadātmānaṁ sṛijāmy aham",
    word_meanings: "yadā yadā—whenever; hi—certainly; dharmasya—of righteousness; glāniḥ—decline; bhavati—is; bhārata—O descendant of Bharata; abhyutthānam—ascendancy; adharmasya—of unrighteousness; tadā—at that time; ātmānam—Myself; sṛijāmi—manifest; aham—I",
    translation: "Whenever there is a decline of righteousness, O Arjuna, and an ascendancy of unrighteousness, then I manifest Myself.",
    author: "Swami Gambhirananda",
    commentary_summary: "The cosmic law of Divine Incarnation (Avatara). Whenever the moral equilibrium of existence is jeopardized by tyranny and chaos, the Supreme Divine Consciousness assumes form to restore Dharma.",
    theme: "Cosmic Dharma & Divine Descent (Avatara)"
  },
  "4.8": {
    verse_id: "4.8",
    chapter: 4,
    verse: 8,
    sanskrit: "परित्राणाय साधूनां विनाशाय च दुष्कृताम्।\nधर्मसंस्थापनार्थाय सम्भवामि युगे युगे॥",
    transliteration: "paritrāṇāya sādhūnāṁ vināśhāya cha duṣhkṛitām\ndharma-saṁsthāpanārthāya sambhavāmi yuge yuge",
    word_meanings: "paritrāṇāya—for the protection; sādhūnām—of the righteous; vināśhāya—for the annihilation; cha—and; duṣhkṛitām—of the wicked; dharma-saṁsthāpanā-arthāya—to firmly establish righteousness; sambhavāmi—I appear; yuge yuge—millennium after millennium",
    translation: "For the protection of the good, for the destruction of the wicked, and for the establishment of righteousness, I come into being from age to age.",
    author: "Swami Sivananda",
    commentary_summary: "The threefold purpose of the Divine incarnation: shielding the seekers of truth, subduing malevolence, and anchoring eternal moral values in the collective consciousness.",
    theme: "Restoration of Dharma"
  },
  "6.5": {
    verse_id: "6.5",
    chapter: 6,
    verse: 5,
    sanskrit: "उद्धरेदात्मनात्मानं नात्मानमवसादयेत्।\nआत्मैव ह्यात्मनो बन्धुरात्मैव रिपुरात्मनः॥",
    transliteration: "uddhared ātmanātmānaṁ nātmānam avasādayet\nātmaiva hyātmano bandhur ātmaiva ripur ātmanaḥ",
    word_meanings: "uddharet—elevate; ātmanā—by the self; ātmānam—the self; na—not; ātmānam—the self; avasādayet—degrade; ātmā—the self; eva—certainly; hi—indeed; ātmanaḥ—of the self; bandhuḥ—friend; ātmā—the self; eva—certainly; ripuḥ—enemy; ātmanaḥ—of the self",
    translation: "One must elevate oneself by one's own mind, and not degrade oneself. The mind is indeed the friend of the self, and the mind is also the enemy of the self.",
    author: "Swami Sivananda",
    commentary_summary: "Self-mastery through internal agency. A controlled and disciplined mind acts as one's greatest guardian and ally; an unruly mind swayed by impulse becomes one's deadliest foe.",
    theme: "Mind Mastery & Self-Elevation"
  },
  "6.35": {
    verse_id: "6.35",
    chapter: 6,
    verse: 35,
    sanskrit: "श्रीभगवानुवाच\nअसंशयं महाबाहो मनो दुर्निग्रहं चलम्।\nअभ्यासेन तु कौन्तेय वैराग्येण च गृह्यते॥",
    transliteration: "śhrī-bhagavān uvācha\nasaṁśhayaṁ mahā-bāho mano durnigrahaṁ chalam\nabhyāsena tu kaunteya vairāgyeṇa cha gṛihyate",
    word_meanings: "śhrī-bhagavān uvācha—the Supreme Lord said; asaṁśhayam—undoubtedly; mahā-bāho—O mighty-armed one; manaḥ—the mind; durnigraham—difficult to curb; chalam—restless; abhyāsena—by practice; tu—but; kaunteya—O son of Kunti; vairāgyeṇa—by detachment; cha—and; gṛihyate—is restrained",
    translation: "The Supreme Lord said: Undoubtedly, O mighty-armed Arjuna, the mind is restless and difficult to curb; but by constant practice (Abhyasa) and detachment (Vairagya), it can be restrained.",
    author: "Swami Gambhirananda",
    commentary_summary: "Lord Krishna acknowledges Arjuna's distress regarding mental agitation, providing the two classical keys of Yoga: persistent meditative practice (Abhyasa) and non-attachment to sensory distractions (Vairagya).",
    theme: "Overcoming Mental Turbulence"
  },
  "9.22": {
    verse_id: "9.22",
    chapter: 9,
    verse: 22,
    sanskrit: "अनन्याश्चिन्तयन्तो मां ये जनाः पर्युपासते।\nतेषां नित्याभियुक्तानां योगक्षेमं वहाम्यहम्॥",
    transliteration: "ananyāśh chintayanto māṁ ye janāḥ paryupāsate\nteṣhāṁ nityābhiyuktānāṁ yoga-kṣhemaṁ vahāmy aham",
    word_meanings: "ananyāḥ—unalloyed; chintayantaḥ—meditating; mām—upon Me; ye—who; janāḥ—people; paryupāsate—worship exclusively; teṣhām—of them; nitya-abhiyuktānām—always absorbed; yoga—spiritual attainment; kṣhemam—preservation of welfare; vahāmi—bear/carry; aham—I",
    translation: "To those people who worship Me with singular devotion, meditating on My transcendental form, I personally carry what they lack and preserve what they have.",
    author: "Swami Sivananda",
    commentary_summary: "The divine promise of Yoga-Kshema. When one anchors their core trust in the Supreme Divine, the universe orchestrates the acquisition of necessary spiritual sustenance and shields their inner peace.",
    theme: "Divine Providence (Yoga-Kshema)"
  },
  "11.32": {
    verse_id: "11.32",
    chapter: 11,
    verse: 32,
    sanskrit: "कालोऽस्मि लोकक्षयकृत्प्रवृद्धो\nलोकान्समाहर्तुमिह प्रवृत्ततः।\nऋतेऽपि त्वां न भविष्यन्ति सर्वे\nयेऽवस्थिताः प्रत्यनीकेषु योधाः॥",
    transliteration: "kālo 'smi loka-kṣhaya-kṛit pravṛiddho\nlokān samāhartum iha pravṛittaḥ\nṛite 'pi tvāṁ na bhaviṣhyanti sarve\nye 'vasthitāḥ pratyanīkeṣhu yodhāḥ",
    word_meanings: "kālaḥ—time/death; asmi—I am; loka-kṣhaya-kṛit—the destroyer of worlds; pravṛiddhaḥ—mighty; lokān—the worlds; samāhartum—to annihilate; iha—here; pravṛittaḥ—engaged; ṛite—without; api—even; tvām—you; na—not; bhaviṣhyanti—shall live; sarve—all; ye—who; avasthitāḥ—stationed; pratyanīkeṣhu—in opposing ranks; yodhāḥ—warriors",
    translation: "I am Time, the great destroyer of the world, engaged here in annihilating the people. Even without your participation, none of the warriors assembled in the opposing armies will survive.",
    author: "Swami Gambhirananda",
    commentary_summary: "Krishna reveals His Viswarupa (Cosmic Universal Form). As relentless Time (Kala), the destiny of the corrupt unrighteous has already been sealed; Arjuna is summoned to be merely an instrument (Nimitta-matram) of divine will.",
    theme: "Cosmic Time & Surrender to Destiny"
  },
  "18.78": {
    verse_id: "18.78",
    chapter: 18,
    verse: 78,
    sanskrit: "यत्र योगेश्वरः कृष्णो यत्र पार्थो धनुर्धरः।\nतत्र श्रीर्विजयो भूतिर्ध्रुवा नीतिर्मतिर्मम॥",
    transliteration: "yatra yogeśhvaraḥ kṛiṣhṇo yatra pārtho dhanur-dharaḥ\ntatra śhrīr vijayo bhūtir dhruvā nītir matir mama",
    word_meanings: "yatra—wherever; yoga-īśhvaraḥ—the Lord of Yoga; kṛiṣhṇaḥ—Lord Krishna; yatra—wherever; pārthaḥ—Arjuna, son of Pritha; dhanuḥ-dharaḥ—the carrier of the bow; tatra—there; śhrīḥ—fortune/prosperity; vijayaḥ—victory; bhūtiḥ—extraordinary opulence; dhruvā—firm; nītiḥ—righteousness/morality; matiḥ mama—such is my conviction",
    translation: "Wherever there is Krishna, the Lord of Yoga, and wherever there is Arjuna, the wielder of the bow, there will surely be fortune, victory, prosperity, and infallible morality. Such is my firm conviction.",
    author: "Swami Sivananda",
    commentary_summary: "Sanjaya concludes the Mahabharata dialogue with this eternal aphorism: when Divine Grace (Krishna) merges with courageous, sincere human initiative (Arjuna with the bow), victory and righteousness are inevitable.",
    theme: "Divine Grace & Human Action in Harmony"
  }
};

export function lookupVerse(ref: string): GitaVerse | null {
  const clean = ref.replace(/^(BG|Gita|Verse)\s*/i, '').trim();
  if (GITA_VERSES[clean]) {
    return GITA_VERSES[clean];
  }
  return null;
}
