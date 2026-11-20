import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

answer = """**1. Maintaining Composure and Cultivating Virtue**  

- **Calm‑mindedness and fearlessness** – *BG 6.14*  
  > “He should remain seated with a placid mind, free from fear, firm in the vow of celibacy, and with the mind fixed on Me by controlling it through concentration, having Me as the supreme goal.”  

- **Qualities that constitute wisdom and virtue** – *BG 13.8*  
  > “Humility, unpretentiousness, non‑injury, forbearance, sincerity, service to the teacher, cleanliness, steadiness, and control of the body and its organs.”  

- **Purified intellect and renunciation of attachment** – *BG 18.51* (one translation)  
  > “Guided always by pure reason, bravely restraining himself, renouncing the objects of sense and giving up attachment and hatred; he attains peace.”  

**Interpretation (my inference)** – By steadying the mind (as in 6.14), practicing the ethical qualities listed in 13.8, and letting pure reason govern one’s actions (18.51), a seeker can keep composure and develop virtue. The verses describe the mental attitude (calm, fearless) and the character traits (humility, non‑violence, self‑control) that together sustain equanimity.

---

**2. Guidance on Practising Celibacy (Brahmacarya)**  

- **Celibacy as part of the yogic disposition** – *BG 6.14* (same verse quoted above) emphasizes “firm in the vow of celibacy.”  

- **Celibacy as a means to the immutable Goal** – *BG 8.11*  
  > “I will briefly tell you about that immutable Goal which the knowers of the Vedas declare; those who are diligent, free from attachment, and aspire for it, enter into it. People practice celibacy for it.”  

**Interpretation (my inference)** – The Gita presents celibacy not as an isolated rule but as a supportive discipline for those who are diligent, unattached, and seeking the ultimate, imperishable goal. Maintaining the vow of celibacy helps steady the mind and focus on the divine (6.14) and aligns the aspirant with the supreme aim described in 8.11.

---

**3. Does Killing a Mosquito Constitute a Sin?**  

The supplied verses do **not** speak directly about the act of killing a mosquito or any specific insect.  

- The nearest teaching on the moral quality of actions is *BG 3.13*:  
  > “Pious people who eat the remnants of sacrifices are freed from all sins, whereas those who are sinful and cook only for their own sake will only incur sin.”  

- A broader description of the three “gates” that lead to ruin (often interpreted as hell) is given in *BG 16.21*:  
  > “Desire, wrath, and greed—these are the three gateways to Naraka, ruinous to the self. Therefore, one should abandon these three.”  

**Interpretation (my inference)** – Since the Gita does not explicitly address the killing of a mosquito, it cannot be said that the text classifies that specific act as a sin. The verses highlight that sin is linked to inner qualities such as selfish desire, anger, and greed (16.21) and to actions performed with impure motives (3.13). Whether an act like killing an insect is sinful would depend on the underlying intention and attachment, which the Gita frames in terms of desire, anger, and greed.

---

**4. Actions or Conditions That Lead a Person to Hell (Naraka)**  

- **Three gateways to hell** – *BG 16.21*  
  > “Desire, wrath, and greed—these are the three gateways to Naraka, ruinous to the self. Therefore, one should abandon these three.”  

The verse identifies **kāma** (desire/lust), **krodha** (anger/wrath), and **lobha** (greed) as the specific mental afflictions that open the door to the state described as hell (Naraka). Abandoning these three is presented as the remedy.

**Interpretation (my inference)** – According to the Gita, a person moves toward the condition of Naraka when they are dominated by intense desire, uncontrolled anger, or excessive greed. Cultivating detachment from these passions is the prescribed way to avoid that destiny.
"""

paragraphs = [p.strip() for p in re.split(r'\n\s*\n', answer) if p.strip()]
print(f"Total paragraphs: {len(paragraphs)}")

citation_pattern = re.compile(r'\b(?:BG|Śrī Bhagavad‑gītā|Bhagavad Gita)\s*([0-9]{1,2}\.[0-9]{1,2})\b|\((?:BG\s*)?([0-9]{1,2}\.[0-9]{1,2})\)')

for i, p in enumerate(paragraphs):
    quotes = list(re.finditer(r'["“]([^"”]+?)["”]', p))
    for m in quotes:
        q_text = m.group(1).strip()
        if len(q_text.split()) >= 4:
            after = p[m.end():]
            cit_after = citation_pattern.search(after)
            before = p[:m.start()]
            cit_before = list(citation_pattern.finditer(before))
            
            print(f"\nQuote: {repr(q_text[:40])}...")
            print(f"  Following citation: {cit_after.groups() if cit_after else None}")
            print(f"  Preceding citation: {cit_before[-1].groups() if cit_before else None}")
