"""Small-talk route: greetings, thanks, "who are you", and one- or two-word fillers get a short fixed
reply with no retrieval and no LLM call ("hi" used to cost ~2.5K tokens for an ungrounded sermon).

Only a message that is *entirely* small talk matches. Anything with a real question in it
("hi, what is karma yoga?") goes on to retrieval as before.
"""

import re
import unicodedata

ROUTE = "smalltalk"

REPLY = (
    "I'm VYOM, a guide to the Bhagavad Gita: ask about duty, fear, loss, desire or any verse, "
    "and I answer from the verses themselves. Try one of these:"
)
THANKS_REPLY = "You're welcome. " + REPLY

_GREETINGS = {
    "hi", "hii", "hiii", "hey", "heya", "hello", "helo", "hallo", "yo", "hiya", "howdy",
    "namaste", "namaskar", "namaskaram", "pranam", "pranaam", "hari om", "om", "jai shri krishna",
    "jai shree krishna", "jai sri krishna", "hare krishna", "radhe radhe", "ram ram", "jai siya ram",
    "good morning", "good afternoon", "good evening", "good night", "greetings", "sup", "whats up",
    "how are you", "how r u", "how are you doing",
    "नमस्ते", "नमस्कार", "प्रणाम", "राधे राधे", "जय श्री कृष्ण", "हरे कृष्ण", "हरि ओम",
}
_THANKS = {
    "thanks", "thank you", "thank u", "thankyou", "thx", "ty", "tysm", "thanks a lot", "thank you so much",
    "thanks so much", "many thanks", "much appreciated", "dhanyavad", "dhanyavaad", "shukriya",
    "धन्यवाद", "शुक्रिया",
}
_ABOUT = {
    "who are you", "what are you", "what is vyom", "who is vyom", "what is this", "what can you do",
    "what do you do", "how do you work", "how does this work", "what can i ask", "what should i ask",
    "help", "about", "about you", "introduce yourself", "are you a bot", "are you ai", "are you human",
}
_FILLERS = {
    "ok", "okay", "k", "kk", "cool", "nice", "great", "good", "fine", "sure", "yes", "no", "yeah", "yep",
    "nope", "hmm", "hm", "hmmm", "lol", "wow", "test", "testing", "ping", "oh", "ah", "alright", "bye",
    "goodbye", "see you", "ok thanks", "okay thanks",
}
# A greeting may be followed by one of these ("hi there", "hello vyom")
_ADDRESSEES = {"there", "vyom", "friend", "all", "everyone", "guys", "ji", "sir", "maam", "krishna", "bot"}


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "").lower().strip()
    text = text.replace("’", "'").replace("'", "")
    # drop punctuation, emoji and symbols; keep letters (incl. Devanagari marks), digits and spaces
    text = "".join(ch if (ch.isalnum() or ch.isspace() or unicodedata.category(ch).startswith("M")) else " " for ch in text)
    return re.sub(r"\s+", " ", text).strip()


def _strip_addressee(t: str) -> str:
    words = t.split()
    if len(words) >= 2 and words[-1] in _ADDRESSEES:
        return " ".join(words[:-1])
    return t


def classify(text: str) -> str | None:
    """'greeting' | 'thanks' | 'about' | 'filler' | None (a real question)."""
    raw = (text or "").strip()
    if not raw or len(raw) > 60:
        return None
    t = _normalize(raw)
    if not t:
        return "filler"  # only punctuation / emoji
    base = _strip_addressee(t)
    if base in _THANKS or t in _THANKS:
        return "thanks"
    if base in _GREETINGS or t in _GREETINGS:
        return "greeting"
    if t in _ABOUT or base in _ABOUT:
        return "about"
    if t in _FILLERS:
        return "filler"
    # two small-talk pieces in a row ("hi thanks", "hello how are you")
    for left in _GREETINGS | _THANKS:
        if t.startswith(left + " ") and classify(t[len(left) + 1 :]) is not None:
            return "thanks" if left in _THANKS else "greeting"
    return None


def reply_for(kind: str) -> str:
    return THANKS_REPLY if kind == "thanks" else REPLY
