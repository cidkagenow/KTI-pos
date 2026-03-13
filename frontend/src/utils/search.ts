/**
 * Tokenized filter for Ant Design Select with showSearch.
 * Splits input into tokens and checks that ALL tokens exist in the option label.
 * Example: "llan 18" matches "LLANTA 18-100 DURO"
 */
export function tokenizedFilter(
  input: string,
  option?: { label?: string | unknown },
): boolean {
  const label = String(option?.label ?? '').toLowerCase();
  const tokens = input.toLowerCase().split(/\s+/).filter(Boolean);
  return tokens.every((token) => label.includes(token));
}

/**
 * Sort function for Ant Design Select `filterSort`.
 * Prioritizes options where the label starts with the search input,
 * then by position of first token match, then alphabetically.
 * Works with antd 6.x signature: filterSort(optionA, optionB, { searchValue })
 */
export function tokenizedFilterSort(
  a: { label?: string | unknown },
  b: { label?: string | unknown },
  info?: { searchValue?: string } | string,
): number {
  const la = String(a.label ?? '').toLowerCase();
  const lb = String(b.label ?? '').toLowerCase();
  const raw = typeof info === 'string' ? info : info?.searchValue ?? '';
  const search = raw.toLowerCase().trim();
  if (!search) return la.localeCompare(lb);

  const tokens = search.split(/\s+/).filter(Boolean);
  const firstToken = tokens[0];

  // Priority 1: label starts with the full search
  const aStarts = la.startsWith(search) ? 0 : 1;
  const bStarts = lb.startsWith(search) ? 0 : 1;
  if (aStarts !== bStarts) return aStarts - bStarts;

  // Priority 2: a word in label starts with the first token
  const aWords = la.split(/\s+/);
  const bWords = lb.split(/\s+/);
  const aWordStart = aWords.some((w) => w.startsWith(firstToken)) ? 0 : 1;
  const bWordStart = bWords.some((w) => w.startsWith(firstToken)) ? 0 : 1;
  if (aWordStart !== bWordStart) return aWordStart - bWordStart;

  // Priority 3: position of first token in string (earlier = better)
  const aPos = la.indexOf(firstToken);
  const bPos = lb.indexOf(firstToken);
  if (aPos !== bPos) return aPos - bPos;

  // Fallback: alphabetical
  return la.localeCompare(lb);
}
