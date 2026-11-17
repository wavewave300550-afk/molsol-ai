/**
 * Terms that subtitles must never split across two pages.
 *
 * Thai word segmentation (Intl.Segmenter) only knows dictionary words, so it
 * cuts most transliterated science terms into fragments: "ไมโทคอนเดรีย"
 * becomes ไม|โท|คอน|เด|รีย. Terms listed here, an episode's own "glossary",
 * every cue's words and every chart label are kept whole.
 * Add a term when a rendered subtitle splits one.
 */
export const SCIENCE_GLOSSARY = [
  "โปรเจกต์",
  "เรนเดอร์",
  "เบนซีน",
  "แนฟทาลีน",
  "แอนทราซีน",
  "ไพรีน",
  "ไฮโดรคาร์บอน",
  "อะโรมาติก",
  "อาร์เอ็นเอ",
  "ไมโทคอนเดรีย",
  "คลอโรพลาสต์",
  "คลอโรฟิลล์",
  "ไซโทพลาซึม",
  "ไรโบโซม",
  "โครโมโซม",
  "นิวคลีโอไทด์",
  "โฟตอน",
  "ควอนตัม",
  "คลอไรด์",
  "ไฮดรอกไซด์",
  "เปอร์ออกไซด์",
  "ซูเปอร์โนวา",
  "หลุมดำ",
  "แรงโน้มถ่วง",
  "ปีแสง",
  "พันธะไฮโดรเจน",
] as const;

/** Thai words a subtitle page should not end with: they lead into the next word. */
export const NO_BREAK_AFTER = new Set([
  "ความ",
  "การ",
  "ผู้",
  "นัก",
  "ที่",
  "ซึ่ง",
  "ของ",
  "แห่ง",
  "และ",
  "หรือ",
  "แต่",
  "กับ",
  "ใน",
  "จาก",
  "ด้วย",
  "เพื่อ",
  "โดย",
  "ต่อ",
  "ว่า",
  "จะ",
]);
