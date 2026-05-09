"""Simple Substitution Cipher — CLI.

A monoalphabetic substitution cipher. The encryption key is a permutation
of the 26-letter alphabet: position 0 gives the substitute for 'A', position
1 gives the substitute for 'B', and so on. The decryption key is the
inverse permutation.

This module is a pure-Python core — GUI/TUI front-ends import from it.

Auto-crack uses a hill-climb / simulated-annealing search over the space of
26-letter permutations, scoring candidate plaintexts with bigram +
trigram + word-dictionary signals. It works on ~80-100 letter ciphertexts
in seconds without any external corpus files.

Run:
    uv run python simple_sub/simple_sub.py
"""
from __future__ import annotations

import math
import random
import string
from collections import Counter

ALPHABET = string.ascii_uppercase
ALPHABET_SIZE = 26

# ---------------------------------------------------------------------------
# Letter / bigram / trigram baselines (English).
#
# Letter frequencies: classic Lewand/Cornell percentages.
# Bigrams + trigrams: hand-curated short-list of the most common English
# n-grams with relative frequencies. They're not Practical Cryptography's
# full quadgram tables (we deliberately avoid downloading any external
# corpus), but they're enough to drive a robust hill-climb on short ciphers.
# ---------------------------------------------------------------------------

ENGLISH_FREQ: dict[str, float] = {
    'A':  8.167, 'B':  1.492, 'C':  2.782, 'D':  4.253, 'E': 12.702,
    'F':  2.228, 'G':  2.015, 'H':  6.094, 'I':  6.966, 'J':  0.153,
    'K':  0.772, 'L':  4.025, 'M':  2.406, 'N':  6.749, 'O':  7.507,
    'P':  1.929, 'Q':  0.095, 'R':  5.987, 'S':  6.327, 'T':  9.056,
    'U':  2.758, 'V':  0.978, 'W':  2.360, 'X':  0.150, 'Y':  1.974,
    'Z':  0.074,
}

# Top English bigrams by frequency (rough percentages, sum ~75%).
# Hand-curated from public letter-pair frequency tables (e.g. Norvig's
# count_2l corpus analysis). This is not Practical Cryptography's full
# table, but it's enough to drive the annealer.
ENGLISH_BIGRAMS: dict[str, float] = {
    'TH': 3.88, 'HE': 3.68, 'IN': 2.28, 'ER': 2.17, 'AN': 2.14,
    'RE': 1.74, 'ON': 1.76, 'AT': 1.49, 'EN': 1.45, 'ND': 1.35,
    'TI': 1.34, 'ES': 1.34, 'OR': 1.28, 'TE': 1.20, 'OF': 1.17,
    'ED': 1.17, 'IS': 1.13, 'IT': 1.12, 'AL': 1.09, 'AR': 1.07,
    'ST': 1.05, 'TO': 1.04, 'NT': 1.04, 'NG': 0.95, 'SE': 0.93,
    'HA': 0.93, 'AS': 0.87, 'OU': 0.87, 'IO': 0.83, 'LE': 0.83,
    'VE': 0.83, 'CO': 0.79, 'ME': 0.79, 'DE': 0.76, 'HI': 0.76,
    'RI': 0.73, 'RO': 0.73, 'IC': 0.70, 'NE': 0.69, 'EA': 0.69,
    'RA': 0.69, 'CE': 0.65, 'LI': 0.62, 'CH': 0.60, 'LL': 0.58,
    'BE': 0.58, 'MA': 0.57, 'SI': 0.55, 'OM': 0.55, 'UR': 0.54,
    'CA': 0.54, 'EL': 0.54, 'TA': 0.53, 'LA': 0.53, 'NS': 0.51,
    'DI': 0.50, 'FO': 0.50, 'HO': 0.49, 'PE': 0.49, 'EC': 0.48,
    'PR': 0.48, 'NO': 0.48, 'CT': 0.45, 'US': 0.44, 'AC': 0.44,
    'OT': 0.44, 'IL': 0.43, 'TR': 0.43, 'LY': 0.42, 'NC': 0.42,
    'ET': 0.42, 'UT': 0.41, 'SS': 0.40, 'SO': 0.40, 'RS': 0.40,
    'UN': 0.39, 'LO': 0.39, 'WA': 0.38, 'GE': 0.38, 'IE': 0.38,
    'WH': 0.38, 'EE': 0.38, 'WI': 0.37, 'EM': 0.37, 'AD': 0.37,
    'OL': 0.37, 'RT': 0.36, 'PO': 0.36, 'WE': 0.36, 'NA': 0.35,
    'UL': 0.35, 'NI': 0.34, 'TS': 0.34, 'MO': 0.34, 'OW': 0.33,
    'PA': 0.32, 'IM': 0.32, 'MI': 0.32, 'AI': 0.31, 'SH': 0.31,
    'IR': 0.30, 'SU': 0.30, 'ID': 0.30, 'OS': 0.29, 'IA': 0.29,
    'AM': 0.29, 'EP': 0.28, 'OP': 0.28, 'GO': 0.27, 'IF': 0.27,
    'PL': 0.27, 'IG': 0.26, 'OD': 0.26,
}

# Top English trigrams. Same approach — a curated set sufficient to
# distinguish real English from a near-miss substitution.
ENGLISH_TRIGRAMS: dict[str, float] = {
    'THE': 3.51, 'AND': 1.59, 'ING': 1.15, 'HER': 0.82, 'HAT': 0.65,
    'HIS': 0.60, 'THA': 0.59, 'ERE': 0.56, 'FOR': 0.56, 'ENT': 0.53,
    'ION': 0.51, 'TER': 0.46, 'WAS': 0.46, 'YOU': 0.44, 'ITH': 0.43,
    'VER': 0.43, 'ALL': 0.42, 'WIT': 0.40, 'THI': 0.39, 'TIO': 0.38,
    'NDE': 0.36, 'HAS': 0.35, 'NCE': 0.34, 'EDT': 0.33, 'TIS': 0.33,
    'OFT': 0.32, 'STH': 0.32, 'MEN': 0.32, 'OUR': 0.31, 'EAR': 0.30,
    'HAV': 0.29, 'HEY': 0.29, 'NOT': 0.28, 'STO': 0.28, 'BUT': 0.27,
    'WHE': 0.27, 'OME': 0.26, 'ITI': 0.26, 'WIL': 0.25, 'ILL': 0.25,
    'OUT': 0.25, 'THR': 0.24, 'EVE': 0.24, 'COM': 0.24, 'ARE': 0.24,
    'WHI': 0.23, 'ATE': 0.23, 'OUL': 0.23, 'HEM': 0.22, 'ERS': 0.22,
    'OTH': 0.22, 'INT': 0.22, 'EST': 0.22, 'AIN': 0.21, 'ESS': 0.21,
    'ONE': 0.21, 'ETH': 0.21, 'TED': 0.20, 'EAN': 0.20, 'ATI': 0.20,
    'EAT': 0.19, 'TIN': 0.19, 'WOR': 0.19, 'HEN': 0.19, 'STA': 0.18,
    'EWA': 0.18, 'EAS': 0.18, 'TUR': 0.17, 'NDA': 0.17, 'OUN': 0.17,
    'HEA': 0.17, 'TOT': 0.16, 'AST': 0.16, 'HOU': 0.16, 'ICH': 0.16,
    'DTH': 0.16, 'ROM': 0.16, 'PRE': 0.15, 'CON': 0.15, 'ULD': 0.15,
    'IST': 0.15, 'SIN': 0.14, 'IGH': 0.14, 'HAN': 0.14, 'BLE': 0.14,
    'OUS': 0.14, 'ESA': 0.13, 'ESO': 0.13, 'DON': 0.13, 'OTE': 0.13,
    'BEC': 0.12, 'ANC': 0.12, 'STR': 0.12, 'GET': 0.12, 'HAD': 0.12,
    'WHA': 0.12, 'ART': 0.12, 'OWN': 0.12,
}

# Common short words — strong signal on short ciphertexts where n-gram
# stats are noisy.
COMMON_WORDS: frozenset[str] = frozenset({
    'THE', 'BE', 'TO', 'OF', 'AND', 'A', 'IN', 'THAT', 'HAVE', 'I',
    'IT', 'FOR', 'NOT', 'ON', 'WITH', 'HE', 'AS', 'YOU', 'DO', 'AT',
    'THIS', 'BUT', 'HIS', 'BY', 'FROM', 'THEY', 'WE', 'SAY', 'HER',
    'SHE', 'OR', 'AN', 'WILL', 'MY', 'ONE', 'ALL', 'WOULD', 'THERE',
    'THEIR', 'WHAT', 'SO', 'UP', 'OUT', 'IF', 'ABOUT', 'WHO', 'GET',
    'WHICH', 'GO', 'ME', 'WHEN', 'MAKE', 'CAN', 'LIKE', 'TIME', 'NO',
    'JUST', 'HIM', 'KNOW', 'TAKE', 'PEOPLE', 'INTO', 'YEAR', 'YOUR',
    'GOOD', 'SOME', 'COULD', 'THEM', 'SEE', 'OTHER', 'THAN', 'THEN',
    'NOW', 'LOOK', 'ONLY', 'COME', 'ITS', 'OVER', 'THINK', 'ALSO',
    'BACK', 'AFTER', 'USE', 'TWO', 'HOW', 'OUR', 'WORK', 'FIRST',
    'WELL', 'WAY', 'EVEN', 'NEW', 'WANT', 'BECAUSE', 'ANY', 'THESE',
    'GIVE', 'DAY', 'MOST', 'US', 'IS', 'WAS', 'ARE', 'WERE', 'BEEN',
    'HAS', 'HAD', 'HELLO', 'WORLD', 'YES', 'OK', 'AM',
    # A few extras that show up a lot in classic cryptogram exercises.
    'QUICK', 'BROWN', 'FOX', 'JUMPS', 'OVER', 'LAZY', 'DOG',
    'SECRET', 'MESSAGE', 'CIPHER', 'CRYPTOGRAM', 'ENGLISH',
    'ATTACK', 'DAWN', 'MEET', 'NOON', 'CODE', 'KEY',
})


# ---------------------------------------------------------------------------
# Key utilities
# ---------------------------------------------------------------------------

def random_key(rng: random.Random | None = None) -> str:
    """Return a fresh random 26-character substitution key.

    The key is a permutation of A-Z. `key[i]` is the cipher letter
    substituted for the plaintext letter at position `i`.

    >>> k = random_key(random.Random(0))
    >>> sorted(k) == list(ALPHABET)
    True
    >>> len(k)
    26
    """
    if rng is None:
        rng = random.Random()
    letters = list(ALPHABET)
    rng.shuffle(letters)
    return ''.join(letters)


def inverse_key(key: str) -> str:
    """Return the inverse permutation of `key`.

    If `encrypt(text, key)` produces ciphertext C, then
    `encrypt(C, inverse_key(key))` recovers the original plaintext.
    Equivalently, `decrypt(ct, key) == encrypt(ct, inverse_key(key))`.
    """
    _validate_key(key)
    inv = [''] * ALPHABET_SIZE
    for i, ch in enumerate(key):
        inv[ord(ch) - ord('A')] = ALPHABET[i]
    return ''.join(inv)


def _validate_key(key: str) -> None:
    if len(key) != ALPHABET_SIZE:
        raise ValueError(
            f'key must be exactly {ALPHABET_SIZE} characters, got {len(key)}'
        )
    upper = key.upper()
    if sorted(upper) != list(ALPHABET):
        raise ValueError(
            'key must be a permutation of A-Z (each letter exactly once)'
        )


# ---------------------------------------------------------------------------
# Encrypt / decrypt
# ---------------------------------------------------------------------------

def _translate(text: str, key: str) -> str:
    """Apply substitution table `key` to `text`, preserving case.

    `key` is the plaintext->ciphertext mapping; for decryption pass
    `inverse_key(...)`.
    """
    _validate_key(key)
    upper_key = key.upper()
    out: list[str] = []
    for ch in text:
        if 'A' <= ch <= 'Z':
            out.append(upper_key[ord(ch) - ord('A')])
        elif 'a' <= ch <= 'z':
            out.append(upper_key[ord(ch) - ord('a')].lower())
        else:
            out.append(ch)
    return ''.join(out)


def encrypt(text: str, key: str) -> str:
    """Encrypt `text` with substitution key `key` (26-char permutation).

    Case is preserved; non-letters pass through untouched.

    >>> encrypt('hello', 'QWERTYUIOPASDFGHJKLZXCVBNM')
    'itssg'
    """
    return _translate(text, key)


def decrypt(text: str, key: str) -> str:
    """Decrypt `text` with the same key used to encrypt.

    Internally inverts the key and applies the substitution. Equivalent
    to `encrypt(text, inverse_key(key))`.

    >>> k = 'QWERTYUIOPASDFGHJKLZXCVBNM'
    >>> decrypt(encrypt('hello world', k), k)
    'hello world'
    """
    return _translate(text, inverse_key(key))


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def letter_frequencies(text: str) -> dict[str, float]:
    """Return percent-frequency of each letter A-Z in `text`.

    Non-letters are ignored. Returns 0.0 for letters that don't appear.
    """
    letters = [c.upper() for c in text if c.isalpha()]
    n = len(letters)
    if n == 0:
        return {ch: 0.0 for ch in ALPHABET}
    counts = Counter(letters)
    return {ch: counts.get(ch, 0) / n * 100.0 for ch in ALPHABET}


def _chi_squared(text: str) -> float:
    """Chi-squared distance from the English letter distribution.

    Lower is better. Returns inf for empty text.
    """
    letters = [c.upper() for c in text if c.isalpha()]
    n = len(letters)
    if n == 0:
        return float('inf')
    counts = Counter(letters)
    chi = 0.0
    for letter in ALPHABET:
        observed = counts.get(letter, 0)
        expected = ENGLISH_FREQ[letter] / 100.0 * n
        chi += (observed - expected) ** 2 / expected
    return chi


def _ngram_score(text: str, n: int, table: dict[str, float]) -> float:
    """Sum of log-frequencies of n-grams in `text` against `table`.

    Higher is better (more English-like). Unknown n-grams contribute a
    floor penalty so that "ZZ" doesn't quietly score as well as "TH".

    NOT normalised by length: each correctly-decoded common n-gram
    contributes a meaningful fixed amount to the score, so a single
    key-letter swap that fixes a few common bigrams produces a clearly
    positive delta the annealer will accept.
    """
    letters = [c.upper() for c in text if c.isalpha()]
    if len(letters) < n:
        return 0.0
    floor = math.log10(0.01)  # penalty for unseen n-grams
    score = 0.0
    seq = ''.join(letters)
    count = len(seq) - n + 1
    for i in range(count):
        gram = seq[i:i + n]
        freq = table.get(gram)
        if freq is None:
            score += floor
        else:
            score += math.log10(freq)
    return score


def _word_hits(text: str) -> int:
    """Count tokens of `text` that appear in the COMMON_WORDS set.

    Single-letter words that aren't 'A' or 'I' are skipped — random
    monoalphabetic gibberish trips on those constantly otherwise.
    """
    hits = 0
    token: list[str] = []
    for ch in text:
        if ch.isalpha():
            token.append(ch.upper())
        else:
            if token:
                word = ''.join(token)
                if word in COMMON_WORDS and (len(word) > 1 or word in ('A', 'I')):
                    hits += 1
            token = []
    if token:
        word = ''.join(token)
        if word in COMMON_WORDS and (len(word) > 1 or word in ('A', 'I')):
            hits += 1
    return hits


def english_score(text: str) -> float:
    """Combined English-likelihood score. Higher = more English-like.

    The hill-climber maximises this. It blends:

    - bigram log-frequency  (weight 1.0, summed not averaged)
    - trigram log-frequency (weight 2.0 — stronger signal on short text)
    - common-word hits      (weight 5.0 — decisive on short cipher)

    Each component is a SUM (not an average) so longer ciphertexts
    produce larger absolute scores. A single key-swap that fixes a
    handful of common n-grams or one common word produces a clearly
    positive delta the annealer accepts; on short texts every signal
    counts, so we don't average them away.
    """
    bigram = _ngram_score(text, 2, ENGLISH_BIGRAMS)
    trigram = _ngram_score(text, 3, ENGLISH_TRIGRAMS)
    words = _word_hits(text)
    return bigram + 2.0 * trigram + 5.0 * float(words)


# ---------------------------------------------------------------------------
# Auto-crack: simulated annealing over key permutations
# ---------------------------------------------------------------------------

def _seed_key_from_freq(ciphertext: str) -> str:
    """Build an initial key by aligning ciphertext letter frequencies with
    English letter frequencies: most-common cipher letter → 'E', second
    → 'T', and so on. Letters that don't appear get assigned the leftover
    English letters in their canonical order.
    """
    letters = [c.upper() for c in ciphertext if c.isalpha()]
    counts = Counter(letters)
    # Cipher letters ordered by frequency (most common first).
    cipher_by_freq = [ch for ch, _ in counts.most_common()]
    for ch in ALPHABET:
        if ch not in counts:
            cipher_by_freq.append(ch)

    # Plaintext letters ordered by English frequency.
    plain_by_freq = sorted(ALPHABET,
                           key=lambda c: ENGLISH_FREQ[c],
                           reverse=True)

    # Build plaintext->cipher map (this is the encryption key).
    pt_to_ct = dict(zip(plain_by_freq, cipher_by_freq))
    return ''.join(pt_to_ct[ch] for ch in ALPHABET)


def _swap(key: str, i: int, j: int) -> str:
    """Return a copy of `key` with positions i and j swapped."""
    chars = list(key)
    chars[i], chars[j] = chars[j], chars[i]
    return ''.join(chars)


def _anneal(ciphertext: str,
            initial_key: str,
            *,
            iterations: int,
            start_temp: float,
            end_temp: float,
            rng: random.Random) -> tuple[str, str, float]:
    """One simulated-annealing run starting from `initial_key`.

    Returns the best `(plaintext, key, score)` seen, not just the final
    state — annealing can drift past the optimum near the end.
    """
    current_key = initial_key
    current_plain = decrypt(ciphertext, current_key)
    current_score = english_score(current_plain)

    best_key = current_key
    best_plain = current_plain
    best_score = current_score

    # Geometric cool-down from start_temp -> end_temp over `iterations`.
    if iterations <= 1:
        cool = 1.0
    else:
        cool = (end_temp / start_temp) ** (1.0 / (iterations - 1))
    temp = start_temp

    for _ in range(iterations):
        i = rng.randrange(ALPHABET_SIZE)
        j = rng.randrange(ALPHABET_SIZE - 1)
        if j >= i:
            j += 1
        candidate_key = _swap(current_key, i, j)
        candidate_plain = decrypt(ciphertext, candidate_key)
        candidate_score = english_score(candidate_plain)

        delta = candidate_score - current_score
        if delta > 0 or rng.random() < math.exp(delta / max(temp, 1e-9)):
            current_key = candidate_key
            current_plain = candidate_plain
            current_score = candidate_score
            if current_score > best_score:
                best_key = current_key
                best_plain = current_plain
                best_score = current_score

        temp *= cool

    return best_plain, best_key, best_score


def crack_with_key(ciphertext: str,
                   *,
                   restarts: int = 15,
                   iterations: int = 4000,
                   rng: random.Random | None = None) -> tuple[str, str, float]:
    """Auto-crack a substitution cipher via simulated annealing.

    Returns `(plaintext, key, score)`. Strategy:

    1. Seed an initial key by frequency-aligning ciphertext letters
       with English letter frequencies (most-common cipher letter → 'E',
       and so on).
    2. Run several annealing chains (`restarts` of them) — the first
       starts from the frequency seed, the rest from progressively
       more-perturbed variants of it so different basins get explored.
       Each chain proposes random key-letter swaps and accepts moves
       that improve the score; worse moves are accepted with
       probability exp(delta / temperature) — the Boltzmann criterion.
    3. Return the highest-scoring plaintext seen across all chains.

    For ~100-letter ciphertexts this converges in 3-8 seconds on a
    typical CPU. Very short ciphertexts (like "Hello, World!") rarely
    have enough signal for any frequency-based attack to recover the
    full key, but the seed alignment alone often gets close.
    """
    if rng is None:
        rng = random.Random()
    if not any(c.isalpha() for c in ciphertext):
        return ciphertext, ALPHABET, 0.0

    seed_key = _seed_key_from_freq(ciphertext)
    best = (decrypt(ciphertext, seed_key), seed_key,
            english_score(decrypt(ciphertext, seed_key)))

    for r in range(restarts):
        # First restart uses the raw seed. Subsequent restarts perturb
        # it more aggressively — by r=10 we're essentially randomising.
        start_key = seed_key
        perturbations = min(r, 12)
        for _ in range(perturbations):
            i = rng.randrange(ALPHABET_SIZE)
            j = rng.randrange(ALPHABET_SIZE)
            start_key = _swap(start_key, i, j)
        plain, key, score = _anneal(
            ciphertext, start_key,
            iterations=iterations,
            start_temp=20.0, end_temp=0.2,
            rng=rng,
        )
        if score > best[2]:
            best = (plain, key, score)
    return best


def crack(ciphertext: str,
          *,
          restarts: int = 15,
          iterations: int = 4000,
          rng: random.Random | None = None) -> str:
    """Convenience wrapper around `crack_with_key` that returns just the
    best plaintext. See `crack_with_key` for the full algorithm.
    """
    return crack_with_key(ciphertext,
                          restarts=restarts,
                          iterations=iterations,
                          rng=rng)[0]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _prompt_key(prompt: str = 'Key (26 letters, blank for random): ') -> str:
    while True:
        raw = input(prompt).strip().upper()
        if raw == '':
            k = random_key()
            print(f'  using random key: {k}')
            return k
        try:
            _validate_key(raw)
        except ValueError as e:
            print(f'  {e}')
            continue
        return raw


def main() -> None:
    print('Simple Substitution Cipher')
    print('=' * 40)
    print('Modes: (e)ncrypt  (d)ecrypt  (c)rack  (q)uit')
    while True:
        mode = input('\nMode [e/d/c/q]: ').strip().lower()
        if mode in ('q', 'quit', 'exit'):
            print('Bye.')
            return
        if mode not in ('e', 'd', 'c'):
            print('  pick one of e, d, c, q')
            continue

        text = input('Text: ')
        if not text:
            print('  empty text — try again')
            continue

        if mode == 'c':
            print('  cracking (simulated annealing — this may take a few seconds)...')
            plain, key, score = crack_with_key(text)
            print(f'  best key  : {key}')
            print(f'  score     : {score:+.3f}')
            print(f'  plaintext : {plain}')
            continue

        key = _prompt_key()
        if mode == 'e':
            print('Cipher:', encrypt(text, key))
        else:
            print('Plain :', decrypt(text, key))


if __name__ == '__main__':
    main()
