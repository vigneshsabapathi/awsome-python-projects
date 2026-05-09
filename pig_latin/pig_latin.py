"""Pig Latin — CLI.

Translate English to Pig Latin (and back, best-effort):

* Words starting with consonants move the leading consonant cluster to the
  end and append ``ay``  (``pig`` -> ``igpay``, ``string`` -> ``ingstray``).
* Words starting with vowels just append ``way``  (``apple`` -> ``appleway``).
* Case of the original is preserved per-letter where reasonable: a Title-Cased
  word stays Title-Cased (``Python`` -> ``Ythonpay``); ALL CAPS stays ALL
  CAPS (``HELLO`` -> ``ELLOHAY``); leading/trailing punctuation rides along
  unchanged (``"hello,"`` -> ``"ellohay,"``); apostrophes inside contractions
  are preserved (``don't`` -> ``on'tday``); hyphenated compounds are
  translated piece-wise (``mother-in-law`` -> ``othermay-inway-awlay``).

Three encoding modes:

================ ================================ ==================
Mode             Suffix / rule                    ``pig`` / ``apple``
================ ================================ ==================
``pig`` (default) move consonants + ``ay`` /     ``igpay`` /
                  vowel + ``way``                  ``appleway``
``greek``         same split, suffix ``uth``     ``iguth`` /
                                                  ``appleuth``
``ubbi``          insert ``ub`` before every     ``pubig`` /
                  vowel sound (Ubbi Dubbi)       ``ubappubluble``
================ ================================ ==================

The functions :func:`translate` and :func:`untranslate` work on free text
preserving whitespace and punctuation.

Run:
    uv run python pig_latin/pig_latin.py
"""
from __future__ import annotations

import re

VOWELS = 'aeiou'
DEFAULT_MODE = 'pig'
MODES = ('pig', 'greek', 'ubbi')

# Common English onset clusters (consonant clusters that can begin a word),
# longest first. Used by :func:`_untranslate_atom` to recover the cluster
# that was rotated to the end. Pig Latin is genuinely ambiguous (``ousehay``
# could be ``house`` or ``shouse``), so we bias toward real English onsets.
_ONSET_CLUSTERS = sorted([
    # Triple onsets
    'str', 'spr', 'scr', 'spl', 'sch', 'thr', 'sph', 'shr', 'squ', 'chr',
    # Double onsets
    'bl', 'br', 'ch', 'cl', 'cr', 'dr', 'fl', 'fr', 'gl', 'gn', 'gr',
    'kn', 'ph', 'pl', 'pr', 'ps', 'qu', 'sc', 'sh', 'sk', 'sl', 'sm',
    'sn', 'sp', 'st', 'sw', 'th', 'tr', 'tw', 'wh', 'wr',
], key=len, reverse=True)

# A "word atom" is a run of letters and apostrophes (so ``don't`` is one
# atom). Anything else is treated as separator and is preserved verbatim.
# We split via a capturing regex so the joins/punctuation come back unchanged.
_TOKEN_RE = re.compile(r"([A-Za-z][A-Za-z']*)")


# ----------------------------------------------------------------- helpers

def _leading_consonants(word: str) -> int:
    """Return the length of the leading consonant cluster in ``word``.

    ``y`` counts as a consonant only if it's the first letter. So ``yellow``
    -> consonant ``y`` is moved (``ellowyay``), but ``rhythm`` keeps ``y``
    as a vowel and only ``rh`` is moved (``ythmrhay``).
    """
    if not word:
        return 0
    n = 0
    while n < len(word):
        ch = word[n].lower()
        if ch in VOWELS:
            return n
        if ch == 'y' and n > 0:
            return n
        n += 1
    return n  # all-consonant word


def _case_pattern(word: str) -> str:
    """Return ``'allcaps'`` | ``'title'`` | ``'lower'`` | ``'mixed'``.

    Used to re-apply the original case after the per-letter translation.
    """
    letters = [c for c in word if c.isalpha()]
    if not letters:
        return 'lower'
    if all(c.isupper() for c in letters):
        return 'allcaps'
    if letters[0].isupper() and all(c.islower() for c in letters[1:]):
        return 'title'
    if all(c.islower() for c in letters):
        return 'lower'
    return 'mixed'


def _apply_case(translated: str, pattern: str) -> str:
    """Re-apply a case pattern detected by :func:`_case_pattern`."""
    if pattern == 'allcaps':
        return translated.upper()
    if pattern == 'title':
        # Lowercase everything, then uppercase the first letter.
        low = translated.lower()
        for i, ch in enumerate(low):
            if ch.isalpha():
                return low[:i] + ch.upper() + low[i + 1:]
        return low
    if pattern == 'lower':
        return translated.lower()
    return translated  # mixed: leave as-is (per-letter case already preserved)


# ---------------------------------------------------------------- per-word

def _translate_atom(atom: str, mode: str) -> str:
    """Translate one all-letters/apostrophes atom (no surrounding punct)."""
    if not atom or not any(c.isalpha() for c in atom):
        return atom

    pattern = _case_pattern(atom)
    low = atom.lower()

    if mode == 'ubbi':
        # Ubbi Dubbi: insert ``ub`` before every vowel sound (run of vowels).
        out: list[str] = []
        i = 0
        in_vowel_run = False
        while i < len(low):
            ch = low[i]
            if ch in VOWELS:
                if not in_vowel_run:
                    out.append('ub')
                    in_vowel_run = True
                out.append(ch)
            else:
                in_vowel_run = False
                out.append(ch)
            i += 1
        return _apply_case(''.join(out), pattern)

    suffix = 'ay' if mode == 'pig' else 'uth'

    # Find the first vowel position; everything before it is the cluster.
    cluster_len = _leading_consonants(low)

    if cluster_len == 0:
        # Vowel-initial: just append the vowel-suffix.
        translated_low = low + ('w' + suffix if mode == 'pig' else suffix)
    elif cluster_len == len(low):
        # No vowels at all (e.g. ``shh``, ``rhythm``-like edge): just append
        # the suffix without rotating.
        translated_low = low + suffix
    else:
        cluster = low[:cluster_len]
        rest = low[cluster_len:]
        translated_low = rest + cluster + suffix

    return _apply_case(translated_low, pattern)


def translate_word(word: str, mode: str = DEFAULT_MODE) -> str:
    """Translate a single word, preserving leading/trailing punctuation.

    Hyphenated compounds are split on ``-`` and each piece is translated
    independently. Embedded apostrophes (contractions) ride along inside
    the atom, so ``don't`` -> ``on'tday``.

    >>> translate_word('pig')
    'igpay'
    >>> translate_word('apple')
    'appleway'
    >>> translate_word('Python')
    'Ythonpay'
    >>> translate_word('HELLO')
    'ELLOHAY'
    >>> translate_word("don't")
    "on'tday"
    >>> translate_word('mother-in-law')
    'othermay-inway-awlay'
    """
    if mode not in MODES:
        raise ValueError(f'mode must be one of {MODES!r}, got {mode!r}')
    if not word:
        return word

    # Split on hyphens so each piece is translated independently while
    # preserving the hyphens.
    if '-' in word:
        return '-'.join(translate_word(p, mode) for p in word.split('-'))

    # Strip leading/trailing non-letter (and non-apostrophe-inside) chars,
    # so wrapping punctuation ("hello,") rides along.
    m = re.match(r"^([^A-Za-z]*)([A-Za-z][A-Za-z']*?)([^A-Za-z]*)$", word)
    if not m:
        return word
    pre, atom, post = m.groups()
    # Trim a trailing apostrophe off the atom (e.g. ``rock'`` -> atom=``rock``,
    # post=``'``) — apostrophes only count as part of the atom if a letter
    # follows them.
    while atom.endswith("'"):
        atom = atom[:-1]
        post = "'" + post
    if not atom:
        return word
    return pre + _translate_atom(atom, mode) + post


# ------------------------------------------------------------ free-text API

def translate(text: str, mode: str = DEFAULT_MODE) -> str:
    """Translate every word in ``text``, preserving whitespace + punctuation.

    >>> translate('The quick brown fox.')
    'Ethay uickqay ownbray oxfay.'
    >>> translate('apple', mode='greek')
    'appleuth'
    """
    if mode not in MODES:
        raise ValueError(f'mode must be one of {MODES!r}, got {mode!r}')

    def _sub(match: re.Match[str]) -> str:
        return translate_word(match.group(1), mode)

    return _TOKEN_RE.sub(_sub, text)


# ------------------------------------------------------------------- decode

def _untranslate_atom(atom: str, mode: str) -> str:
    """Best-effort reverse of :func:`_translate_atom`. Ambiguous in general."""
    if not atom or not any(c.isalpha() for c in atom):
        return atom

    pattern = _case_pattern(atom)
    low = atom.lower()

    if mode == 'ubbi':
        # Strip every ``ub`` that immediately precedes a vowel.
        out: list[str] = []
        i = 0
        n = len(low)
        while i < n:
            if i + 2 < n and low[i:i + 2] == 'ub' and low[i + 2] in VOWELS:
                # skip the 'ub'
                i += 2
                continue
            out.append(low[i])
            i += 1
        return _apply_case(''.join(out), pattern)

    suffix = 'ay' if mode == 'pig' else 'uth'
    if not low.endswith(suffix):
        return atom  # not pig-latin shaped, leave alone
    body = low[:-len(suffix)]

    # In pig mode, vowel-initial words get a 'w' inserted before the suffix
    # (``apple`` -> ``appleway``). If body ends with 'w' and the part before
    # starts with a vowel, prefer the vowel-initial reading. (This is still
    # ambiguous — ``orry`` and ``worry`` both encode to ``orryway`` — but
    # vowel-initial is the more common reading for real text.)
    if mode == 'pig' and body.endswith('w') and len(body) >= 2 \
            and body[0] in VOWELS:
        return _apply_case(body[:-1], pattern)

    # Consonant-initial: pick the longest known English onset cluster that
    # matches the trailing consonants of ``body``. This is heuristic — pig
    # latin is genuinely ambiguous — but it gets common English words right
    # most of the time. Falls back to a single trailing consonant if no
    # known cluster matches.
    cluster = ''
    for onset in _ONSET_CLUSTERS:
        if body.endswith(onset) and len(body) > len(onset):
            head = body[:-len(onset)]
            if head and (head[0] in VOWELS or head[0] == 'y'):
                cluster = onset
                break
    if not cluster:
        # Fall back: single trailing consonant if the rest starts with vowel.
        if len(body) >= 2 and body[-1] not in VOWELS and body[0] in VOWELS:
            cluster = body[-1]
    if not cluster:
        # Vowel-initial in pig mode strips a trailing 'w' (handled above).
        # In greek mode there is no extra letter; just return the body.
        return _apply_case(body, pattern)
    rest = body[:-len(cluster)]
    return _apply_case(cluster + rest, pattern)


def untranslate(text: str, mode: str = DEFAULT_MODE) -> str:
    """Best-effort reverse of :func:`translate`.

    Pig Latin is lossy: ``ousehay`` could decode to ``house`` or
    ``shouse``. We pick the largest plausible consonant cluster (greedy
    longest tail of consonants) which is right far more often than not for
    real English words.

    >>> untranslate('igpay')
    'pig'
    >>> untranslate('appleway')
    'apple'
    >>> untranslate('Ethay ickquay ownbray oxfay.')
    'The quick brown fox.'
    """
    if mode not in MODES:
        raise ValueError(f'mode must be one of {MODES!r}, got {mode!r}')

    def _sub(match: re.Match[str]) -> str:
        word = match.group(1)
        if '-' in word:
            return '-'.join(untranslate(p, mode) for p in word.split('-'))
        # Preserve leading/trailing non-letter punctuation as in translate().
        m = re.match(
            r"^([^A-Za-z]*)([A-Za-z][A-Za-z']*?)([^A-Za-z]*)$", word
        )
        if not m:
            return word
        pre, atom, post = m.groups()
        while atom.endswith("'"):
            atom = atom[:-1]
            post = "'" + post
        if not atom:
            return word
        return pre + _untranslate_atom(atom, mode) + post

    return _TOKEN_RE.sub(_sub, text)


# ---------------------------------------------------------------- CLI glue

def _prompt_mode(default: str = DEFAULT_MODE) -> str:
    raw = input(f'Mode [pig/greek/ubbi] (default {default}): ').strip().lower()
    if not raw:
        return default
    if raw not in MODES:
        print(f'  unknown mode {raw!r}, using {default!r}')
        return default
    return raw


def main() -> None:
    print('Pig Latin')
    print('=' * 40)
    print('Modes: (e)ncode  (d)ecode  (q)uit')
    while True:
        action = input('\nAction [e/d/q]: ').strip().lower()
        if action in ('q', 'quit', 'exit'):
            print('Bye.')
            return
        if action not in ('e', 'd'):
            print('  pick one of e, d, q')
            continue

        text = input('Text: ')
        mode = _prompt_mode()
        if action == 'e':
            print('Pig   :', translate(text, mode=mode))
        else:
            print('Plain :', untranslate(text, mode=mode))


if __name__ == '__main__':
    main()
