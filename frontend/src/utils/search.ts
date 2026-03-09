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
