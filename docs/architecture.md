# Architecture

![Architecture diagram](architecture_diagram.png)

## Pipeline

1. Student submits a Sanskrit sentence through the frontend.
2. The backend normalizes the text (Unicode NFC, strip stray non-Devanagari characters).
3. The normalized sentence is sent down two independent branches in parallel:
   - **Sandhi + morphology branch**: sandhi-splitter separates the sentence into
     component words, then the morphological analyzer tags each word (root, case,
     gender, number, tense as applicable).
   - **Translation branch**: the *original, unsplit* sentence is sent to the
     fine-tuned IndicTrans2 model. It is not pre-split, since the translation model
     was trained on natural (unsplit) text and splitting first would change how it
     reads sentence context.
4. The backend merges both branches into a single structured response.
5. The frontend renders translation, split words, and gloss in separate sections.

## Module contracts (fill in as each module is finalized)

| Module | Owner | Input | Output |
|---|---|---|---|
| Translation | Satyam | Sanskrit sentence (string) | English translation (string) |
| Sandhi splitter | Mayank | Sanskrit sentence (string) | Ordered list of split word-units |
| Morphological analyzer | Shrinivas | List of split words | Gloss per word: root, POS, case/tense |

Agree on the exact JSON shape for each of these before building against real modules —
the frontend and backend can be developed against mocked responses in this shape while
the actual models/tools are still being integrated.

## Known limitations

- Sandhi-splitting is not always deterministic — ambiguous input may return multiple
  candidate splits with a confidence indicator rather than a single guess.
- Morphological fields that can't be resolved by the analyzer are left unset rather
  than guessed.
- The system targets contemporary textbook prose (NCERT), not classical/Vedic verse.
