/** Boss 001 definition: THE MIGRATING MOUNTAIN. */
import { Player } from "@minecraft/server";
import { BossDefinition, registerBoss } from "../../core/registry.js";
import { ABILITY_IDS } from "./abilities.js";
import { MigratingMountainEncounter } from "./encounter.js";
import { DIMENSION, ENT } from "./ids.js";

export const MIGRATING_MOUNTAIN: BossDefinition = {
  id: "migrating_mountain",
  dimensionId: DIMENSION,
  summonItem: "anatomy:restless_lodestone",
  abilities: ABILITY_IDS,
  entities: Object.values(ENT),
  atlas: {
    number: "001",
    title: "THE MIGRATING MOUNTAIN",
    subtitle: "The Mountain That Never Belonged to the Earth",
    overview:
      "A colossal geological organism whose entire body is a mountain range: living strata, forests, rivers, waterfalls and minerals, all organs of one living system. It wanders the cloud sea, slowly, in search of geological balance.\n\nHeight 60–80 blocks · Length 100–140 blocks\nBody plan: Geological Organism\nLocomotion: Lithic Peristalsis (contraction and expansion of rock layers)",
    anatomy: [
      "§lMountain Shell§r — stratified rock and minerals; its dorsal biome is a forest you can walk on.",
      "§lMineral Circulation§r — glowing red veins carrying minerals and energy to every organ.",
      "§lLithic Heart§r — the amethyst core inside the Organ Cavern; shielded by the Resonance Network.",
      "§lMantle Musculature§r — maroon rock-muscle that moves the body and contracts its cavities.",
      "§lAnchorage Roots§r — fourteen root-legs that balance the body and carry it across the clouds; when it flees, four of them seize the ground.",
    ],
    phases: [
      {
        name: "Phase 1 · The Sleeping Continent §7(100% → 60%)",
        text: "Climb and explore the body. Destroy the three Resonance Nodes: on the summit crag, inside the Organ Cavern (front tunnel), and hanging beneath the body (spiral shaft from the cavern down to the underbelly gallery). Every node broken costs the heart part of its strength.",
      },
      {
        name: "Phase 2 · The Unfolded World §7(60% → 35%)",
        text: "The shell unfolds, exposing the Lithic Heart on a disk of shifting ribs. After Resonance Network or Mantle Contraction its iris opens — strike then. At about half health the world refolds once and the ribs re-bloom, turned. Steam vents throw you back up if you fall onto the mantle floor.",
      },
      {
        name: "Phase 3A · The Last Migration §7(35% → 20%)",
        text: "The shell rises into a crown of walls, the legs start to march and the mountain walks away across the cloud sea. Four Anchorage Roots seize the disk (§6★§r on the locator bar): break each root's glowing sinew knot — every severed root opens the heart for 8 seconds. Jump the rolling ridges of its march. After 4 minutes it walks faster and attacks more often.",
      },
      {
        name: "Phase 3B · The Heart Unbound §7(20% → 0%)",
        text: "The last root snaps: the mountain falls and the disk breaks into nine floating islands. The heart tears itself free and hovers over the centre island — bows and crossbows hurt it (half damage). About every 22 seconds it slams down onto the centre island for 6 seconds: strike it then for full damage. A fall into the clouds throws you back onto the centre island.",
      },
    ],
    abilities: [
      {
        name: "01 Continental Fold",
        text: "Fault lines glow, then the strata buckle into new ridges — paths on its back change. §83A:§r a footfall drives a fault across the disk and a ridge heaves up along it — get off the line. §83B:§r an island cracks and half of it drops away for a while.",
      },
      {
        name: "02 Lithic Peristalsis",
        text: "The roots stomp and rolling waves of rock sweep the surface. Jump each wave in rhythm. §83A:§r its march sends waves across the whole disk. §83B:§r shockwave rings roll out from the centre island.",
      },
      { name: "03 Geological Shedding", text: "The rock skin peels away and huge slabs fall on the marked rings. §83A/3B:§r slabs break from its shell and fall from the sky." },
      {
        name: "04 Resonance Network",
        text: "Rings of resonance pulse from a node or the heart. Stand inside the green gaps. §83A:§r the rings pulse from the roots still holding. §83B:§r Mineral Beams — a warning line, then a molten beam sweeps across the islands: jump to another island.",
      },
      { name: "05 Inverted Strata", text: "A walkway tears free and flips into a wall, or rolls overhead into a ceiling. §83B:§r an island with a glowing rim flips over — get off it." },
      { name: "06 Mantle Contraction", text: "A cavity squeezes shut. Reach a glowing pocket (or the heart's ring) before it closes. §83B:§r the heart drags everyone towards the centre — walk away from the edge." },
      { name: "07 The Great Unfolding", text: "With its network broken the whole body opens like a flower and the arena becomes Phase 2. Near death it refolds and gets up to walk (Phase 3)." },
    ],
    rewards: [
      "§fEvery player§r, straight into the inventory: 3 Lithic Heart Shards, 8–12 diamonds, 16–24 emeralds, 2–3 netherite scrap, 16 gold ingots, 4 golden apples, 32 bottles o' enchanting and 2 enchanted books (Mending, Unbreaking III, Protection IV, Sharpness V, Efficiency V, Fortune III, Feather Falling IV or Power V).",
      "§fAt the heart§r: 64 amethyst shards, more diamonds and emeralds, netherite ingots and 1500 XP — more for a bigger party.",
      "§6Strata Breaker§r — a heavy hammer that hits harder than a netherite sword (2500 durability). Use it for §fFold Slam§r: a ridge of rock bursts 7 blocks forward; mobs on it take 8 damage and are thrown up. 8 s cooldown; never breaks blocks or hurts players.",
      "§6Anchorage Greaves§r — boots (3 armor). No fall damage; sneak to root yourself (Resistance I).",
      "§7Both are certain on your first victory, then 40% each.",
      "§7Lithic Heart Shard: use one for Mountain's Resolve (Health Boost II + Resistance I for 5 minutes).",
    ],
    scale: "≈78 blocks tall, 116 long, 92 wide; a player is 1.8 blocks.",
    arena: "Its own void dimension: the boss's body is the arena, drifting over a sea of clouds.",
    summon: "Use a Restless Lodestone (tuff, amethyst shards, a compass and mossy cobblestone). Players within 32 blocks are drawn in with you.",
    th: {
      subtitle: "ภูเขาที่ไม่เคยเป็นของผืนโลก",
      overview:
        "สิ่งมีชีวิตทางธรณีขนาดมหึมา ที่ทั้งร่างคือเทือกเขา ชั้นหิน ป่า แม่น้ำ น้ำตก และแร่ธาตุ ล้วนเป็นอวัยวะของสิ่งมีชีวิตตัวเดียวกัน มันเร่ร่อนไปบนทะเลเมฆอย่างช้า ๆ เพื่อหาสมดุลของผืนหิน\n\nสูง 60–80 บล็อก · ยาว 100–140 บล็อก\nร่างกาย: สิ่งมีชีวิตทางธรณี\nการเคลื่อนที่: ชั้นหินหดและขยายตัวเป็นจังหวะ (Lithic Peristalsis)",
      anatomy: [
        "§lเปลือกภูเขา§r — ชั้นหินและแร่ธาตุ บนหลังเป็นป่าที่เดินขึ้นไปได้",
        "§lระบบไหลเวียนแร่§r — เส้นเลือดสีแดงเรืองแสง ส่งแร่และพลังงานไปทุกอวัยวะ",
        "§lหัวใจศิลา§r — แกนอเมทิสต์ในถ้ำอวัยวะ มีเครือข่ายผลึกคอยป้องกัน",
        "§lกล้ามเนื้อแมนเทิล§r — หินกล้ามเนื้อสีแดงเข้ม ใช้ขยับร่างและบีบโพรงในตัว",
        "§lรากยึดเกาะ§r — ขาราก 14 ขา ช่วยทรงตัวและพาร่างเดินข้ามเมฆ ตอนมันหนี 4 รากจะลงมาจับพื้นไว้",
      ],
      phases: [
        {
          name: "เฟส 1 · ทวีปที่หลับใหล §7(100% → 60%)",
          text: "ปีนสำรวจตัวภูเขา แล้วทำลายผลึกสีม่วง 3 จุด: บนยอดผาสูงสุด, ในถ้ำอวัยวะ (อุโมงค์ด้านหน้า) และผลึกที่ห้อยใต้ท้องภูเขา (ลงบันไดวนจากถ้ำไปถึงระเบียงใต้ท้อง) ผลึกแตกหนึ่งอัน พลังหัวใจลดลงหนึ่งส่วน",
        },
        {
          name: "เฟส 2 · โลกที่คลี่ออก §7(60% → 35%)",
          text: "เปลือกภูเขาคลี่ออก เห็นหัวใจศิลาอยู่กลางลานซี่โครง หลังท่า Resonance Network หรือ Mantle Contraction ม่านตาของหัวใจจะเปิด ให้ตีตอนนั้น พอพลังเหลือราวครึ่งหนึ่ง ลานจะพับกลับหนึ่งครั้งแล้วซี่โครงหมุนไปตำแหน่งใหม่ ถ้าตกลงไปพื้นด้านล่าง ไอร้อนจะพ่นตัวกลับขึ้นมา",
        },
        {
          name: "เฟส 3A · การอพยพครั้งสุดท้าย §7(35% → 20%)",
          text: "กลีบภูเขาตั้งขึ้นเป็นกำแพง ขาเริ่มก้าวเดิน และภูเขาเดินหนีไปบนทะเลเมฆ รากยึดเกาะ 4 รากจับลานไว้ (§6★§r บนแถบระบุตำแหน่ง) ตีปมเอ็นเรืองแสงของแต่ละรากให้ขาด ทุกรากที่ขาด หัวใจจะเปิดให้ตี 8 วินาที คอยกระโดดข้ามคลื่นหินจากการก้าวเดิน ถ้าช้าเกิน 4 นาที ภูเขาจะเดินเร็วขึ้นและโจมตีถี่ขึ้น",
        },
        {
          name: "เฟส 3B · หัวใจหลุดจากร่าง §7(20% → 0%)",
          text: "รากสุดท้ายขาด ภูเขาล้ม ลานแตกเป็นเกาะลอยฟ้า 9 เกาะ หัวใจฉีกตัวออกจากร่างแล้วลอยอยู่เหนือเกาะกลาง ยิงด้วยธนูหรือหน้าไม้ได้ (ดาเมจครึ่งเดียว) ทุก ๆ ราว 22 วินาที มันจะกระแทกลงเกาะกลาง 6 วินาที ตอนนั้นตีได้ดาเมจเต็ม ตกลงไปในเมฆจะถูกเหวี่ยงกลับมาที่เกาะกลาง",
        },
      ],
      abilities: [
        {
          name: "01 Continental Fold",
          text: "รอยเลื่อนเรืองแสง แล้วชั้นหินดันตัวขึ้นเป็นสันใหม่ ทางเดินบนหลังเปลี่ยนไป §83A:§r ก้าวเท้ากระแทกจนเกิดรอยเลื่อนข้ามลาน แล้วสันหินดันขึ้นตามแนว ให้หลบออกจากเส้น §83B:§r เกาะร้าว ครึ่งหนึ่งร่วงลงไปสักพัก",
        },
        {
          name: "02 Lithic Peristalsis",
          text: "ขารากกระทืบ แล้วคลื่นหินวิ่งผ่านพื้น กระโดดข้ามทีละลูกตามจังหวะ §83A:§r การเดินส่งคลื่นข้ามทั้งลาน §83B:§r คลื่นกระแทกเป็นวงออกจากเกาะกลาง",
        },
        { name: "03 Geological Shedding", text: "ผิวหินลอกออก แผ่นหินยักษ์ร่วงลงในวงที่ทำเครื่องหมายไว้ §83A/3B:§r แผ่นหินหลุดจากเปลือกและร่วงลงมาจากฟ้า" },
        {
          name: "04 Resonance Network",
          text: "วงคลื่นพลังออกมาจากผลึกหรือหัวใจ ให้ยืนในช่องสีเขียว §83A:§r วงคลื่นออกมาจากรากที่ยังไม่ขาด §83B:§r ลำแสงแร่ มีเส้นเตือนก่อน แล้วลำแร่หลอมกวาดผ่านเกาะ ให้กระโดดหนีไปอีกเกาะ",
        },
        { name: "05 Inverted Strata", text: "ทางเดินฉีกออกแล้วพลิกตั้งเป็นกำแพง หรือม้วนขึ้นไปเป็นเพดาน §83B:§r เกาะที่ขอบเรืองแสงจะพลิกคว่ำ รีบออกจากเกาะนั้น" },
        { name: "06 Mantle Contraction", text: "โพรงบีบตัวปิด รีบไปยืนในช่องเรืองแสง (หรือวงรอบหัวใจ) ก่อนมันปิด §83B:§r หัวใจดูดทุกคนเข้าหาตรงกลาง ให้เดินหนีจากขอบ" },
        { name: "07 The Great Unfolding", text: "พอผลึกแตกหมด ทั้งร่างจะบานออกเหมือนดอกไม้ กลายเป็นเฟส 2 ตอนใกล้ตาย มันจะพับตัวกลับแล้วลุกขึ้นเดิน (เฟส 3)" },
      ],
      rewards: [
        "§fทุกคน§r ได้เข้ากระเป๋าโดยตรง: เศษหัวใจศิลา 3, เพชร 8–12, มรกต 16–24, เศษเนเธอไรต์ 2–3, แท่งทอง 16, แอปเปิลทอง 4, ขวดประสบการณ์ 32 และหนังสือเอนชานต์ 2 เล่ม (สุ่มจาก Mending, Unbreaking III, Protection IV, Sharpness V, Efficiency V, Fortune III, Feather Falling IV, Power V)",
        "§fกองกลางที่หัวใจ§r: อเมทิสต์ 64, เพชรและมรกตเพิ่ม, แท่งเนเธอไรต์ และ XP 1500 ยิ่งคนเยอะยิ่งได้เยอะ",
        "§6Strata Breaker (ค้อนชั้นหิน)§r — ค้อนใหญ่ ตีแรงกว่าดาบเนเธอไรต์ ทน 2500 กดใช้ = §fFold Slam§r สันหินพุ่งไปข้างหน้า 7 บล็อก มอนที่โดนเสีย 8 และกระเด็นลอย คูลดาวน์ 8 วินาที ไม่ทำลายบล็อก ไม่โดนผู้เล่น",
        "§6Anchorage Greaves (รองเท้ารากยึด)§r — ค่าเกราะ 3 ไม่เจ็บตอนตก ย่อตัวเพื่อยึดพื้น (ได้ Resistance I)",
        "§7ชนะครั้งแรกได้ทั้ง 2 ชิ้นแน่นอน ครั้งต่อไปได้แต่ละชิ้น 40%",
        "§7เศษหัวใจศิลา: กดใช้ 1 ชิ้น ได้ Mountain's Resolve (Health Boost II + Resistance I นาน 5 นาที)",
      ],
      scale: "สูงราว 78 บล็อก ยาว 116 กว้าง 92 (ผู้เล่นสูง 1.8 บล็อก)",
      arena: "มิติว่างเปล่าของมันเอง ตัวบอสคือสนาม ลอยอยู่เหนือทะเลเมฆ",
      summon: "ใช้ Restless Lodestone (คราฟต์จากหินทัฟฟ์ เศษอเมทิสต์ เข็มทิศ และหินกรวดมีมอส) ผู้เล่นในระยะ 32 บล็อกจะถูกดึงเข้าไปด้วย",
    },
  },
  create(party: Player[]) {
    return new MigratingMountainEncounter(MIGRATING_MOUNTAIN, party);
  },
};

registerBoss(MIGRATING_MOUNTAIN);
