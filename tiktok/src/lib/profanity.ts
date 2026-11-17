/**
 * Word lists for the "no profanity" narration rule.
 *
 * Thai has no spaces between words, so matching is done on Intl.Segmenter
 * word tokens rather than substrings: "หีบ" (chest) or "แม่งาน" (organiser)
 * must not trip the rule. Only phrase-like terms that cannot occur inside an
 * innocent word are also matched as substrings.
 *
 * blocked: always rejected.
 * review: has an innocent meaning too (e.g. สัด = estrus in animal science),
 *         so it is reported for the reviewer to confirm, not rejected.
 * allowed: compounds that contain a blocked syllable but are fine.
 */
export const PROFANITY = {
  blocked: {
    th: [
      "เหี้ย",
      "เชี่ย",
      "เชี้ย",
      "สัส",
      "ควย",
      "หี",
      "เย็ด",
      "แม่ง",
      "มึง",
      "กู",
      "อีดอก",
      "อีตัว",
      "แตด",
      "ร่าน",
    ],
    thPhrases: ["ไอ้สัตว์", "อีสัตว์", "ไอ้เหี้ย", "อีเหี้ย", "ชิบหาย", "ฉิบหาย", "ระยำ", "จัญไร", "ส้นตีน", "กะหรี่"],
    en: ["fuck", "fucking", "fucked", "fucker", "motherfucker", "shit", "bullshit", "bitch", "asshole", "bastard", "cunt", "wtf"],
  },
  review: {
    th: ["สัด", "ตีน", "ห่า", "เวร", "เสือก", "ดอกทอง"],
    en: ["damn", "crap", "hell", "dick", "pussy"],
  },
  allowed: ["กูเกิล", "กูเกิ้ล", "กูรู"],
} as const;

/** Hints shown when a blocked word has a polite alternative. */
export const PROFANITY_HINTS: Record<string, string> = {
  เหี้ย: 'for the animal (Varanus salvator) say "ตัวเงินตัวทอง"',
};
