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
  const textWords = text.split(/\s+/);
  const maxDist = word.length <= 3 ? 0 : word.length <= 6 ? 1 : 2;

  return textWords.some((tw) => {
    // Check substring of text word
    if (tw.includes(word) || word.includes(tw)) return true;
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
 * Client-side fuzzy filter hook.
 * Splits search into words and checks each word fuzzy-matches the text extracted from items.
 * Tolerates 1-2 character typos depending on word length.
 */
export default function useFuzzyFilter<T>(
  items: T[],
  search: string,
  getText: (item: T) => string,
): T[] {
  return useMemo(() => {
    if (!search.trim()) return items;
    const words = search.toLowerCase().trim().split(/\s+/);
    return items.filter((item) => {
      const text = getText(item).toLowerCase();
      return words.every((word) => fuzzyWordMatch(word, text));
    });
  }, [items, search, getText]);
}
