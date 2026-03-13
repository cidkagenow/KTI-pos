import { useMemo } from 'react';

/**
 * Levenshtein distance — number of edits to turn `a` into `b`.
 * Used for typo-tolerant matching.
 */
function levenshtein(a: string, b: string): number {
  const m = a.length;
  const n = b.length;
  if (m === 0) return n;
  if (n === 0) return m;

  let prev = Array.from({ length: n + 1 }, (_, i) => i);
  let curr = new Array<number>(n + 1);

  for (let i = 1; i <= m; i++) {
    curr[0] = i;
    for (let j = 1; j <= n; j++) {
      const cost = a[i - 1] === b[j - 1] ? 0 : 1;
      curr[j] = Math.min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + cost);
    }
    [prev, curr] = [curr, prev];
  }
  return prev[n];
}

/**
 * Check if `word` fuzzy-matches any part of `text`.
 * First tries exact substring match, then Levenshtein on each word in text.
 */
function fuzzyWordMatch(word: string, text: string): boolean {
  // Exact substring match
  if (text.includes(word)) return true;

  // Fuzzy match against individual words in text
  const textWords = text.split(/\s+/).filter(Boolean);
  const maxDist = word.length <= 3 ? 0 : word.length <= 6 ? 1 : 2;

  return textWords.some((tw) => {
    // Check substring of text word
    if (tw.includes(word) || (tw.length >= 3 && word.includes(tw))) return true;
    // Levenshtein on full words
    if (levenshtein(word, tw) <= maxDist) return true;
    // Check if word is a fuzzy prefix of text word
    if (tw.length >= word.length) {
      const prefix = tw.substring(0, word.length);
      if (levenshtein(word, prefix) <= maxDist) return true;
    }
    return false;
  });
}

/**
 * Score how well `word` matches within `text`. Lower = better.
 * 0 = exact substring, 1+ = fuzzy (Levenshtein distance).
 * Returns -1 if no match.
 */
function fuzzyWordScore(word: string, text: string): number {
  const textWords = text.split(/\s+/).filter(Boolean);
  const maxDist = word.length <= 3 ? 0 : word.length <= 6 ? 1 : 2;

  // Check for exact substring — score by position (earlier = better)
  if (text.includes(word)) {
    // Word starts a text word → best (score 0)
    for (const tw of textWords) {
      if (tw.startsWith(word)) return 0;
    }
    // Substring but not at word boundary → score 1
    return 1;
  }

  let best = -1;
  for (const tw of textWords) {
    if (tw.includes(word) || (tw.length >= 3 && word.includes(tw))) return 1;
    const dist = levenshtein(word, tw);
    if (dist <= maxDist && (best === -1 || dist < best)) best = dist === 0 ? 2 : dist + 2;
    if (tw.length >= word.length) {
      const prefixDist = levenshtein(word, tw.substring(0, word.length));
      if (prefixDist <= maxDist) {
        const s = prefixDist === 0 ? 2 : prefixDist + 2;
        if (best === -1 || s < best) best = s;
      }
    }
  }
  return best;
}

/**
 * Client-side fuzzy filter hook.
 * Splits search into words and checks each word fuzzy-matches the text extracted from items.
 * Tolerates 1-2 character typos depending on word length.
 * Results are sorted by relevance (best matches first).
 */
export default function useFuzzyFilter<T>(
  items: T[],
  search: string,
  getText: (item: T) => string,
): T[] {
  return useMemo(() => {
    if (!search.trim()) return items;
    const words = search.toLowerCase().trim().split(/\s+/);

    const scored: { item: T; score: number }[] = [];
    for (const item of items) {
      const text = getText(item).toLowerCase();
      let totalScore = 0;
      let matched = true;
      for (const word of words) {
        const s = fuzzyWordScore(word, text);
        if (s === -1) { matched = false; break; }
        totalScore += s;
      }
      if (matched) {
        // Bonus: text starts with the full search query → prioritize
        const fullSearch = words.join(' ');
        if (text.startsWith(fullSearch)) totalScore -= 1;
        scored.push({ item, score: totalScore });
      }
    }

    scored.sort((a, b) => a.score - b.score);
    return scored.map((s) => s.item);
  }, [items, search, getText]);
}
