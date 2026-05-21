import random
import sys
from english_words import get_english_words_set
from nltk.corpus import wordnet as wn
from plyer import notification

print("Loading offline database...")
all_words = list(get_english_words_set(["gcide"], lower=True))

# ---------------------------------------------------------------------------
# WordNet lexname → vocabulary domain tag
# These lexicographer file names group words by semantic field.
# ---------------------------------------------------------------------------
EMOTIONAL_LEXNAMES = {
    "noun.feeling", "adj.all",  # emotions, attitudes, moods
}

SOCIAL_LEXNAMES = {
    "noun.communication", "noun.act", "noun.group",
    "verb.communication", "verb.social", "verb.cognition",
}

PROFESSIONAL_LEXNAMES = {
    "noun.cognition", "noun.artifact", "noun.process",
    "verb.creation", "verb.change", "verb.cognition",
    "adj.pert",  # relational/technical adjectives
}

PREFERRED_LEXNAMES = EMOTIONAL_LEXNAMES | SOCIAL_LEXNAMES | PROFESSIONAL_LEXNAMES

POS_MAPPING = {
    "n": "Noun",
    "v": "Verb",
    "a": "Adjective",
    "r": "Adverb",
    "s": "Adjective (satellite)",
}

DOMAIN_EMOJI = {
    "Emotional":     "💡",
    "Social":        "🤝",
    "Professional":  "🧠",
    "General":       "📖",
}


def classify_domain(lexname: str) -> str:
    if lexname in EMOTIONAL_LEXNAMES:
        return "Emotional"
    if lexname in SOCIAL_LEXNAMES:
        return "Social"
    if lexname in PROFESSIONAL_LEXNAMES:
        return "Professional"
    return "General"


def score_word(word: str, synsets) -> int:
    """
    Higher score = more desirable word.
    Criteria:
      +3  word length 8-14 characters (sophisticated but not obscure)
      +2  only 1-3 synsets (precise, specific meaning — not slang/overloaded)
      +2  first synset is in a preferred lexname domain
      +1  has at least one example sentence in WordNet
      -2  word is extremely common (≤ 6 letters gets no bonus from length rule)
      -99 word contains digits, hyphens, or is all-caps
    """
    if not word.isalpha() or not word.islower():
        return -99

    score = 0
    length = len(word)

    if 8 <= length <= 14:
        score += 3
    elif length >= 15:          # too obscure
        score += 1

    num_synsets = len(synsets)
    if 1 <= num_synsets <= 3:
        score += 2
    elif num_synsets >= 10:     # extremely common word
        score -= 2

    first = synsets[0]
    if first.lexname() in PREFERRED_LEXNAMES:
        score += 2

    if first.examples():
        score += 1

    return score


def get_educated_word(min_score: int = 4):
    """
    Randomly samples words until it finds one that meets the quality bar.
    Returns (word, part_of_speech, definition, example, domain).
    """
    attempts = 0
    best = None          # (score, word, pos, definition, example, domain)

    # Sample up to 200 candidates; keep the best-scoring one above min_score.
    sample = random.sample(all_words, min(200, len(all_words)))

    for word in sample:
        attempts += 1
        if len(word) < 6 or not word.isalpha():
            continue

        synsets = wn.synsets(word)
        if not synsets:
            continue

        sc = score_word(word, synsets)
        if sc < min_score:
            continue

        first = synsets[0]
        definition = first.definition()
        examples   = first.examples()
        example    = examples[0] if examples else ""
        pos        = POS_MAPPING.get(first.pos(), "Word")
        domain     = classify_domain(first.lexname())

        if best is None or sc > best[0]:
            best = (sc, word, pos, definition, example, domain)

        # Stop early if we find a great candidate
        if sc >= 7:
            break

    if best:
        _, word, pos, definition, example, domain = best
        # Trim for Windows notification limits
        if len(definition) > 110:
            definition = definition[:107] + "..."
        return word, pos, definition, example, domain

    # Fallback: relax the score requirement and try again
    return get_educated_word(min_score=2)


def trigger_notification():
    """Builds and pushes a rich vocabulary notification."""
    word, pos, definition, example, domain = get_educated_word()

    emoji  = DOMAIN_EMOJI[domain]
    title  = f"{emoji} {word.capitalize()} ({pos}) — {domain}"
    message = f"{definition}"
    if example:
        # Append a short example if it fits
        short_ex = example if len(example) <= 60 else example[:57] + "..."
        message += f'\n\nEx: "{short_ex}"'

    notification.notify(
        title=title,
        message=message,
        app_name="Daily Word",
        timeout=15,
    )

    print(f"\n{'='*60}")
    print(f"  WORD    : {word.upper()}")
    print(f"  DOMAIN  : {domain}")
    print(f"  TYPE    : {pos}")
    print(f"  MEANING : {definition}")
    if example:
        print(f"  EXAMPLE : \"{example}\"")
    print(f"{'='*60}")


def main():
    print("\n--- Educated Vocabulary Generator (Offline) ---")
    print("Targeting: emotional depth · social fluency · professional precision")
    print("\nFetching your first word...\n")

    trigger_notification()

    while True:
        user_input = (
            input("\nPress Enter for another word  |  'e' = emotional  |  's' = social  "
                  "|  'p' = professional  |  'exit' = quit\n> ")
            .strip()
            .lower()
        )

        if user_input == "exit":
            print("Goodbye! Keep building that vocabulary.")
            sys.exit()

        # Optional domain filtering via monkey-patching the preferred set
        global PREFERRED_LEXNAMES
        original = PREFERRED_LEXNAMES

        if user_input == "e":
            PREFERRED_LEXNAMES = EMOTIONAL_LEXNAMES
            print("Filtering for emotional vocabulary...")
        elif user_input == "s":
            PREFERRED_LEXNAMES = SOCIAL_LEXNAMES
            print("Filtering for social vocabulary...")
        elif user_input == "p":
            PREFERRED_LEXNAMES = PROFESSIONAL_LEXNAMES
            print("Filtering for professional/technical vocabulary...")
        else:
            print("Generating next word...")

        trigger_notification()
        PREFERRED_LEXNAMES = original   # restore after each pull


if __name__ == "__main__":
    main()
