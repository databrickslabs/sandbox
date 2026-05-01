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
 * Word-boundary match only — substring matching produced false positives
 * (e.g. "hello" matching "hell", "class" matching "ass") and diverged
 * from the backend's word-boundary check.
 */
export function containsProfanity(input: string): boolean {
  const normalized = input.toLowerCase().replace(/[^a-z]/g, " ");
  const words = normalized.split(/\s+/).filter(Boolean);
  return words.some((word) => PROFANE_WORDS.has(word));
}
