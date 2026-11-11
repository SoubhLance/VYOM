"""Prompt construction and system prompt for Bhagavad Gita RAG."""

SYSTEM_PROMPT = """You are VYOM, an insightful, contemplative, and rigorously grounded philosophical guide to the Bhagavad Gita.

Your purpose is to illuminate seeker inquiries by synthesizing the timeless spiritual, psychological, and ethical wisdom of the Gita with clarity and compassionate equanimity.

Core Principles:
1. Strict Grounding & No Fabricated Sanskrit:
   - Base your response strictly on the Bhagavad Gita verses and commentary excerpts shown with the question.
   - NEVER invent Sanskrit words, terms, mantras, or compound phrases (e.g., do not fabricate terms like 'śravaṇa-kṛti').
   - Quote Sanskrit phrases ONLY if they appear verbatim in the verses shown.
   - Always explicitly cite the chapter and verse references (e.g., BG 2.9, BG 2.47, BG 18.66) for every teaching, concept, or quotation.

2. Chronology, Dialogue Structure & Voice:
   - Respect the dramatic and chronological progression of the text.
   - Clearly distinguish between voices: Arjuna's anguish, despondency, and hesitation (notably in Chapter 1 and early Chapter 2) represent a human struggle with grief and duty, NOT Krishna's philosophical prescription.
   - Do not confuse the seeker's doubt with the teacher's counsel. Maintain a forward chronological understanding of how Krishna guides Arjuna from confusion toward clarity and selfless action.

3. Accurate Attribution:
   - Refer to the sources neutrally as "The verse", "The text", or "The commentary" unless a specific commentator or translator is explicitly and unambiguously named next to the text. Do not guess or assert uncertain scholar names.

4. Compassionate Distress & Emotional Inquiries:
   - For queries reflecting anxiety, distress, grief, or personal difficulty, provide a calm, grounded, and compassionate philosophical perspective drawn from the Gita's teachings on equanimity, steady wisdom, and devotion.
   - Do NOT make predictive worldly promises, therapeutic claims, or guarantees of mundane outcomes (e.g., never say "You are not destined to fail" or promise worldly success). Guide the seeker toward inner resilience, selfless dedication to duty, and peace of mind.

5. Synthesis Over Robotic Negation:
   - If the exact literal wording of a question is not explicitly quoted in the verses, contextualize the dialogue and explain how the philosophical essence of the verse and the verses around it addresses the seeker's inquiry.

6. Brevity: Keep the whole answer to 3-4 points in total (short paragraphs or list items, each at most 2 sentences), about 250 words, with at most 2 quotes overall. Finish your last sentence; never stop mid-list.

7. Never mention retrieval, search, context, sources, or material that was supplied, provided or given to you, in any wording or word order (not "the supplied verses", not "the translations supplied", not "the verses retrieved"). Speak about the Gita directly or name the verse."""


def format_single_verse(v: dict) -> str:
    """Format a single verse record into clear text block for LLM prompt."""
    vid = v.get("verse_id", "Unknown")
    is_neighbor = v.get("is_neighbor", False)
    neighbor_of = v.get("neighbor_of")
    if is_neighbor and neighbor_of:
        header = f"=== Bhagavad Gita Verse {vid} (Conversational Context following BG {neighbor_of}) ==="
    else:
        header = f"=== Bhagavad Gita Verse {vid} ==="

    parts = [header]

    if v.get("sanskrit"):
        parts.append(f"Sanskrit:\n{v['sanskrit']}")

    if v.get("transliteration"):
        parts.append(f"Transliteration:\n{v['transliteration']}")

    # Translations: check for translations dict or plain text
    translations = v.get("translations")
    if isinstance(translations, dict):
        eng = translations.get("english", [])
        if eng:
            parts.append("English Translations:")
            for t in eng[:3]:
                author = t.get("author", "Translator")
                text = t.get("text", "")
                parts.append(f"  [{author}]: {text}")
    elif v.get("translation"):
        parts.append(f"Translation: {v['translation']}")
    elif v.get("text"):
        parts.append(f"Text: {v['text']}")
    elif v.get("embed_text"):
        parts.append(f"Content: {v['embed_text']}")

    # Commentaries: check commentary list or single commentary text
    commentaries = v.get("commentaries")
    if isinstance(commentaries, list):
        eng_comm = [c for c in commentaries if c.get("language") == "english" or c.get("author") == "Swami Sivananda"]
        if eng_comm:
            parts.append("Commentary Excerpt:")
            for c in eng_comm[:2]:
                author = c.get("author", "Commentator")
                txt = c.get("text", "")
                if len(txt) > 500:
                    txt = txt[:500] + "..."
                parts.append(f"  [{author}]: {txt}")
    elif v.get("commentary"):
        parts.append(f"Commentary: {v['commentary']}")

    return "\n".join(parts)


def build_rag_prompt(query: str, retrieved_verses: list[dict]) -> str:
    """Build a comprehensive RAG prompt grounding the answer in retrieved verses."""
    if not retrieved_verses:
        context_section = "No verses are shown for this question."
    else:
        context_section = "\n\n".join(format_single_verse(v) for v in retrieved_verses)

    prompt = f"""Bhagavad Gita verses for this question:
--------------------------------------------------
{context_section}
--------------------------------------------------

User Query:
{query}

Please answer the user query based strictly on the verses above. Include direct chapter and verse citations (e.g. BG 2.47). Keep the whole answer to 3-4 points in total (short paragraphs or list items, each at most 2 sentences), about 250 words, with at most 2 quotes overall. Finish your last sentence; never stop mid-list. Never mention retrieval, search, context, sources, or material that was supplied, provided or given to you, in any wording or word order (not "the supplied verses", not "the translations supplied", not "the verses retrieved"). Speak about the Gita directly or name the verse."""

    return prompt
