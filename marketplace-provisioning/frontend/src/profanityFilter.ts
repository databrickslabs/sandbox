/**
 * Simple profanity filter for nickname validation.
 * Checks against a list of common profane words.
 */

const PROFANE_WORDS = new Set([
  "ass", "asshole", "bastard", "bitch", "bullshit", "cock", "crap", "cunt",
  "damn", "dick", "douchebag", "fag", "faggot", "fuck", "fucker", "fucking",
  "goddamn", "hell", "jackass", "motherfucker", "nigger", "nigga", "penis",
  "piss", "prick", "pussy", "shit", "shitty", "slut", "twat", "vagina",
  "whore", "wanker", "retard", "retarded",
]);

/**
 * Returns true if the input contains profanity.
 * Checks whole words (case-insensitive) and also catches
 * attempts to embed profanity inside longer strings.
 */
export function containsProfanity(input: string): boolean {
  const normalized = input.toLowerCase().replace(/[^a-z]/g, " ");
  const words = normalized.split(/\s+/).filter(Boolean);

  // Check each word
  for (const word of words) {
    if (PROFANE_WORDS.has(word)) return true;
  }

  // Also check if any profane word appears as a substring in the full input
  const compressed = input.toLowerCase().replace(/[^a-z]/g, "");
  for (const profane of PROFANE_WORDS) {
    if (compressed.includes(profane)) return true;
  }

  return false;
}
