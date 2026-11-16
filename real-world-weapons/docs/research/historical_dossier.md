# Historical Sword Dossier: Rapier, Zweihänder, Katana

*For cube-based (low-poly) 3D weapon models in a Minecraft Bedrock add-on. Compiled 2026-11-16.*

---

## 0. Method, conventions and caveats (read first)

**How the data was gathered.** Every museum figure here comes from the official collection record cited next to it (Met, Wallace Collection, V&A, Royal Armouries, Cleveland Museum of Art, KHM Vienna, Fitzwilliam, Worcester Art Museum, Tokyo National Museum via the Agency for Cultural Affairs database, and others). This session's network policy blocked direct page fetches from `metmuseum.org` (and its API). So all record text was obtained as **search-engine extractions of those official pages**, not by opening the pages. I transcribed the figures as the records give them, cross-checked several with a second independent query, and flagged anything that came from a single extraction or that conflicted. **Before final sign-off, spot-check any number you build geometry from against the live page.**

**Evidence labels used throughout**

| Tag | Meaning |
|---|---|
| **[S]** | Measurement of a specific cited specimen, as published by the holding institution |
| **[T]** | Typical range, derived from the cited specimens (or from a cited secondary source, named) |
| **[I]** | My own inference or arithmetic. Not a published figure |
| **n.p.** | "Not published": not present in the record text retrieved in this session. The field may still exist on the live page |

**Measurement-convention warnings**
- Met "W." and "D." on swords are the **hilt's** width and depth (guard span and front-to-back), not blade width.
- Wallace "Width … at top of the ricasso" is **blade** width. Wallace balance points are measured "forward of the guard block".
- Cleveland gives separate *Overall / Blade / Quillons / Grip / Ricasso* fields. On several CMA swords, blade + grip ≈ overall, so the CMA "grip" figure **may include the pommel** [I]. Treat CMA grip numbers as grip-plus-pommel unless verified.
- V&A "Blade (tip to hilt)" and Fitzwilliam "hilt length" may exclude or include the ricasso section enclosed by the guard. Conventions differ between museums.
- Japanese records give *nagasa* (刃長, straight line from the back notch, *munemachi*, to the tip) and *sori* (反り, deepest gap between the back of the blade and that straight line). The Met's "L. of cutting edge" is close to nagasa.

---

## 1. RAPIER: European swept-hilt rapier, c. 1580–1640 (primary focus)

### 1.1 Specimen table

**Primary specimens (build from these)**

| # | Institution / accession | Date, origin, maker | Overall | Blade | Blade width (base / near point) | Grip / hilt length | Guard (quillon) span | Weight | Point of balance | Record |
|---|---|---|---|---|---|---|---|---|---|---|
| R1 | **Wallace Collection A569** | c. 1590. Toledo. Blade by Gonzalo Simón (crowned G and Toledo marks on ricasso) | **120.4 cm** [S] | **105.5 cm** [S] | **2.0 cm** "just above the ricasso" [S] / n.p. | n.p. | **21.1 cm** (guard width) [S] | **1.155 kg** [S] | **10 cm** forward of guard block [S] | [Wallace objectId 61062](https://wallacelive.wallacecollection.org/eMP/eMuseumPlus?service=ExternalInterface&module=collection&objectId=61062&viewType=detailView) |
| R2 | **Wallace Collection A570** | c. 1620–1630. "Toledo rapier" (crowned-P ricasso mark) | **139.4 cm** [S] | **123.4 cm** [S] | **2.8 cm** at top of ricasso [S] / n.p. | n.p. | n.p. | **1.62 kg** [S] | **17.3 cm** forward of guard block [S] | [Wallace objectId 61063](https://wallacelive.wallacecollection.org/eMP/eMuseumPlus?service=ExternalInterface&module=collection&objectId=61063&viewType=detailView) |
| R3 | **V&A M.52-1947** | 1600–1620. Bavaria. Hilt attributed to Emanuel or Daniel Sadeler, after designs by Étienne Delaune | n.p. (blade + hilt = 122.0 cm [I]) | **106.5 cm** [S] | n.p. | **Hilt length 15.5 cm** [S] | **Hilt width 25 cm** [S]. Hilt depth 11 cm [S] | **1.25 kg** [S] | n.p. | [V&A O97250](https://collections.vam.ac.uk/item/O97250/swept-hilt-rapier-sadeler-daniel) |
| R4 | **Met 28.100.3** | ca. 1600–20. German (record links to Saxony). Gift of Prince Albrecht Radziwill, by exchange, 1928 | **121.9 cm** (48 in) [S] | **106.1 cm** (41¾ in) [S] | n.p. | n.p. (overall − blade = 15.8 cm [I]) | **W. 19.1 cm** (7½ in) [S]. D. 13.3 cm [S] | **1446.8 g** (3 lb 3 oz) [S] | n.p. | [Met 23042](https://www.metmuseum.org/art/collection/search/23042) |

**Supplementary data points (cross-checks and extra fields)**

| # | Institution / accession | Date, origin | Overall | Blade | Blade width | Grip | Guard span | Weight | POB | Notes / record |
|---|---|---|---|---|---|---|---|---|---|---|
| R5 | Wallace Collection (objectId 61101; inventory no. not captured) | c. 1580–1620. Hilt possibly Milan. Blade N. Italy, ricasso incised "Caino" and crown | 131.4 [S] | 114.1 [S] | 2.8 at top of ricasso [S] | n.p. | n.p. | 1.3 kg [S] | 12.5 cm [S] | Swept hilt [S]. [Record](https://wallacelive.wallacecollection.org/eMP/eMuseumPlus?service=ExternalInterface&module=collection&objectId=61101&viewType=detailView) |
| R6 | Wallace A572 | c. 1590–1600. Milan / Solingen | n.p. | 111.5 [S] | n.p. | n.p. | n.p. | 1.24 kg [S] | 15.8 cm [S] | Swept loop-guard, pierced oval shell, hexagonal blade. [Record](https://wallacelive.wallacecollection.org/eMP/eMuseumPlus?service=ExternalInterface&module=collection&objectId=61065&viewType=detailView) |
| R7 | Wallace A599 | Probably 2nd quarter 17th c. Hilt probably Italian, blade probably German | 119.7 (record does not label which length) [S] | n.p. | 2.6 (unlabelled; probably blade) [S] | n.p. | n.p. | 1.31 kg [S] | n.p. | Blued, filed swept hilt [S]. [Record](https://wallacelive.wallacecollection.org/eMP/eMuseumPlus?service=ExternalInterface&module=collection&objectId=61092&viewType=detailView) |
| R8 | Cleveland 1916.1719 | c. 1610. Germany | 125.2 [S] | 110 [S] | n.p. | **13.5** [S] | **Quillons 25** [S] | n.p. | n.p. | "Hilt of deeply blued steel; wood" [S]. [Record](https://www.clevelandart.org/print/art/1916.1719) |
| R9 | Cleveland 1916.1634 | c. 1600 (1595–1605). Italy | 110 [S] | 94 [S] | n.p. | 14.7 [S] | Quillons 16.2 [S] | n.p. | n.p. | "Wire grip; hilt blued and chiseled with foliate pattern" [S]. [Record](https://www.clevelandart.org/print/art/1916.1634) |
| R10 | Cleveland 1916.702 | c. 1600. Germany, Solingen | 125.4 [S] | 111 [S] | n.p. | 12.7 [S] | Quillons 15 [S] | n.p. | n.p. | [Record](https://www.clevelandart.org/print/art/1916.702) |
| R11 | Met 1973.27.5 | ca. 1610–20. Solingen. Blade by Meves Berns | 120.2 [S] | 104.1 [S] | n.p. | n.p. | W. 22.1 [S] | 1275.7 g [S] | n.p. | Steel, silver, copper [S]. [Met 24867](https://www.metmuseum.org/art/collection/search/24867) |
| R12 | Met 04.3.32 | ca. 1580. Italian | 130.8 [S] | 115.5 [S] | n.p. | n.p. | W. 18.2, D. 13.3 [S] | 1275.7 g [S] | n.p. | Steel, silver [S]. [Met 25063](https://www.metmuseum.org/art/collection/search/25063) |
| R13 | Royal Armouries IX.879 | About 1610. Probably Italian | 119.4 (1194 mm) [S] | 102.2 (1022 mm) [S] | n.p. | n.p. | n.p. | n.p. | n.p. | Blued swept hilt, chain-pierced, silver pointillé, silver-wire grip. Front quillon modern, pommel 19th c. [S]. [Record (page as returned by search)](https://collections.royalarmouries.org/object/rac-object-40750.html) |
| R14 | Fitzwilliam HEN.M.220-1933 | Date not confirmed in retrieved text. Blade inscribed "PIETRO HERNANDES" in the fullers | n.p. | 104.3 [S] | **2.2 at hilt** [S] | "Hilt length" 23.4 [S] | Quillons 27.5 [S] | n.p. | n.p. | Flat shield-shaped pommel with barrel-shaped button [S]. [Record](https://data.fitzmuseum.cam.ac.uk/id/object/18950) |
| R15 | V&A M.184-1921 | ca. 1600. Hilt French. Spanish blade "VALENCIA ME FECIT" | 131.5 [S] | 108.8 [S] | n.p. | n.p. | n.p. | 1280 g [S] | n.p. | Chain-form hilt, blued and gold-inlaid [S]. [V&A O97533](https://collections.vam.ac.uk/item/O97533) |

Other records seen but not tabulated: Met 14.25.1048, German, 127 cm overall, 107.3 cm blade, 1474.2 g, shagreen grip, hilt 16th c. and blade 17th c. (a composite) ([Met 27433](https://www.metmuseum.org/art/collection/search/27433)). Met 14.25.1199, ca. 1600–1620, hilt possibly Munich, 125.3 cm, 1275.7 g ([Met 22368](https://www.metmuseum.org/art/collection/search/22368)).

### 1.2 Typical-range summary (c. 1580–1640 swept and related hilts)

| Parameter | Range in cited specimens [T] | Notes |
|---|---|---|
| Overall length | 110–139.4 cm (most 120–131 cm) | R1–R15 |
| Blade length | 94–123.4 cm (most 104–115 cm) | |
| Blade as % of overall | 85.5–88.5 % (Met / Wallace / CMA conventions) [I] | e.g. R4 87.0 %, R1 87.6 %, R2 88.5 %, R8 87.9 % |
| Hilt (overall − blade) | 14.4–17.3 cm [I] | V&A gives hilt length 15.5 cm [S] |
| Grip alone (CMA) | 12.7–14.7 cm [S] (may include pommel) | R8–R10 |
| Guard / quillon span | 15–27.5 cm. Swept hilts mostly 19–25 cm | R1 21.1, R3 25, R4 19.1, R8 25, R11 22.1, R14 27.5 |
| Hilt depth (front–back) | 11–13.3 cm [S] | R3, R4, R12 |
| Blade width at ricasso / forte | 2.0–2.8 cm [S] | R1 2.0, R14 2.2, R7 2.6, R2 and R5 2.8. Virtus Martialis notes "about 2.4 cm" as common for three-ring rapiers [T, secondary] |
| Blade width near point | n.p. for every specimen | |
| Ricasso length | n.p. for every specimen | |
| Weight | 1.155–1.62 kg (most 1.24–1.45 kg) [S] | Fortner & Schrattenecker study of 7 historical rapiers: 1130–1630 g, as summarised by Academie Duello [T, secondary] |
| Point of balance | 10–17.3 cm forward of guard block [S] | Wallace R1, R2, R5, R6. Same study: 3.7–6.1 in (9.4–15.5 cm) "from the hilt" [T, secondary] |

### 1.3 Anatomy notes for modelling

**Hilt components (terms as used in the Wallace, Royal Armouries and Met records)**

| Component | What the records say | Modelling note |
|---|---|---|
| **Pommel** | Fluted cylindrical (Wallace A580, A599), flattened cylindrical with button (R5), grooved (R2), "flat, shield-shaped with barrel-shaped button" (R14), oval (R13, a replacement) | A 3–4 cm block or octagonal stack topped by a small tang button [I] |
| **Grip** | "Oval, wire-bound" (R5). Wooden grip "bound with silver wire" (R13). Wooden grip of oval section "bound with twisted and braided iron wire" (Met 27313, Pietro de Formicano blade). "Spirally fluted, wire-bound" (R2) | 12.7–14.7 cm long. Texture with diagonal wire lines and small "Turk's head" ferrule bands at each end [I] |
| **Quillons (cross)** | "Long straight quillons support a knuckle-guard and arms of the hilt" (R13). "Straight crossguard ending in small shells" (R2). "Single curving rear quillon" (R5) | Total span 19–25 cm, centred on the quillon block (écusson). The rear quillon often curves back toward the hand [S] |
| **Knuckle-guard (knuckle-bow)** | Rises from the front quillon to the pommel. "Joined by a loop to the hilt-arms" (R5). "Two loop-guards, one joining the ring-guard, the other dividing into three at the back and joining the hilt-arms" (R2) | Arc from the front of the quillon block up to the pommel, on the outside (thumb) side of the knuckles |
| **Arms of the hilt (pas d'âne)** | "Hilt-arms" in Wallace records. Met lists pommel, knuckle guard, quillons, arms of the hilt and side rings as the hilt's parts | Two small loops below the quillons that straddle the ricasso. They shield the index finger that hooks over the cross |
| **Ring-guard / side-ring(s)** | "Side-ring of circular section" (R2). "Double ring-guards" (R5). "Triple ring-guard" (A599). The upper side ring connected to the knuckle guard (Met description) | On the outside face: one to three concentric or stacked rings springing from the quillon block, joined to the knuckle-bow by sweeping bars |
| **Loop-guards / counter-guards** | Swept bars linking knuckle-bow, rings and hilt-arms. "Swept loop-guard and a pierced oval shell" (R6) | For cubes, 2–4 thin curved bars rising from the ring area to the knuckle-bow on the outside, plus a mirrored, smaller inner set [I] |

**Blade**
- **Cross-section.** Flattened diamond (R1), diamond (R2), hexagonal (R6, A599, A676) [S]. A single short fuller at the forte is documented on R1 ("single flute at the ricasso"). R14 has inscribed fullers [S]. Long, stiff and tapering (R2) [S].
- **Ricasso.** A blunt, unsharpened section directly below the quillon block, enclosed by the arms of the hilt. Maker's marks are stamped on it (R1, R2, R6, R13) [S]. **Length n.p.** Inference: about 4–6 cm, about as long as the hilt-arms reach below the cross [I].

**Proportions for a cube build** (computed [I] from R1–R4 and R8)
- Blade about 87 % of overall. Hilt (grip, pommel and quillon block) about 13 %.
- Guard span about 18–24 % of blade length (R4 18 %, R1 20 %, R8 22.7 %, R3 23.5 %).
- Blade width at the forte about 2–2.5 % of blade length (2.0–2.8 cm on a 105–123 cm blade). The model blade should look very thin. At Minecraft scale it may need to be exaggerated to stay visible [I].
- Hilt depth (front–back) about 45–75 % of guard span (R3 44 %, R4 70 %, R12 73 %). The cage is a 3D volume, not a flat cross [I].
- The hilt (overall − blade) is only 15–16 cm, and the CMA "grip" (12.7–14.7 cm) probably includes the pommel. So the wire-wrapped grip itself is about 10 cm, a one-hand grip [I].

**Reference proportions (recommended build) [I, derived from R1–R4 and R8]**

| Part | Reference value | % of overall (122 cm) |
|---|---|---|
| Overall | 122 cm | 100 % |
| Blade (incl. ricasso) | 106 cm | 87 % |
| Ricasso (inside hilt-arms) | about 5 cm [I] | 4 % |
| Blade width at forte → near tip | 2.4 cm → about 1.0 cm [I. Tip width n.p.] | |
| Quillon block (écusson) | about 2 cm [I] | 2 % |
| Grip (wire-wrapped) | about 10 cm [I] (CMA grip plus pommel 12.7–14.7 [S]) | 8 % |
| Pommel (incl. button) | about 3.5 cm [I] | 3 % |
| Whole hilt (block + grip + pommel) | 15.5–16 cm [S-derived: V&A 15.5, Met 15.8] | 13 % |
| Quillon span | 22 cm | 18 % (21 % of blade) |
| Guard depth | 12 cm | 10 % |
| Target mass / POB (for animation feel) | 1.25–1.45 kg, POB 10–15 cm ahead of the guard | |

**Colours and materials for textures (all [S] from the cited records)**
- Blued steel hilts: R8 "deeply blued", R9 "blued and chiseled", A599 "blued and filed", R13 blued with silver pointillé, R3 "chiselled… blued and gilt".
- Blackened ground with silver encrustation: R2 (silver scrolls and dots on blackened ground). R1 and A597 heavy silver-encrusted pommel and guards.
- Gilt or once-gilt: A580 (punched and hatched for gilding). R5 gilt guards.
- Gold damascening plus chiselled silver: V&A M.51-1947. Gold inlay on blued steel: R15.
- Grips: silver wire (R13), iron wire (Met 27313), shagreen (Met 14.25.1048).
- Blade: bright steel.

### 1.4 Handling and documented technique (for animation)

1. **Grip: index finger over the cross.** The usual rapier grip passes the index finger over the forward quillon and around the ricasso. The finger-rings and arms of the hilt (pas d'âne) are widely explained as protection for that finger. Sources: grip study at [bop.unibe.ch](https://bop.unibe.ch/apd/article/download/11602/16402/64116); HEMA and collector sources surfaced in search, e.g. [David Biggs, "How to hold the rapier"](https://davidbiggs.substack.com/p/how-to-hold-the-rapier) and the Ethnographic Arms & Armour forum. Treat this as practitioner consensus. I found no museum record stating it explicitly. **Animation:** forefinger hooked over the front quillon, thumb on the grip or ricasso side, other three fingers on the grip.
2. **Guards are defined by hand rotation (Fabris 1606).** Prima is the hand position as the sword is drawn (hand high). Seconda is reached by turning the hand a little downward. Terza is the natural position of the hand, "neither turned one way nor the other". Quarta is the hand turned inward. Quarta cannot be reached from prima without passing through the others ([Fabris, *Lo Schermo*, Wiktenauer p. 10](https://wiktenauer.com/wiki/Page:Lo_Schermo,_overo_Scienza_d’Arme_(Salvator_Fabris)_1606.pdf/10)). Capoferro (1610) uses the same four-guard nomenclature. Modern glosses describe prima as thumb-down and seconda as palm-down ([ARMA glossary](https://thearma.org/rapierglossary.htm)).
3. **Attack: the lunge.** Capoferro sizes the sword to the body: "twice as long as the arm, and as much as my extraordinary pace (i.e. the lunge)" ([Wikipedia: Ridolfo Capo Ferro](https://en.wikipedia.org/wiki/Ridolfo_Capo_Ferro); [Guy Windsor](https://guywindsor.net/2015/07/size-matters-how-long-should-your-rapier-be/)). His thrust is delivered by extending the body and stepping forward, not by the arm alone ([Wiktenauer scan p. 34](https://wiktenauer.com/wiki/Page:Gran_Simulacro_dell'Arte_e_dell'Uso_della_Scherma_(Ridolfo_Capo_Ferro_da_Cagli)_1601.pdf/34)). Thrust names (Saviolo 1595 and Dell'Agocchie 1572, via glossaries):
   - **stoccata**: rising or straight thrust passing under the opponent's sword
   - **imbroccata**: downward thrust over it, from a high hand, palm to the right, point angled down at the face
   - **punta riversa**: thrust from the left or inside line with the hand supinated

   Sources: [ARMA Saviolo glossary](https://www.thearma.org/essays/saviologlossary.htm), [UNC glossary](https://cs.unc.edu/~hudson/saviolo/glossary.html), [NAU Dell'Agocchie](https://jan.ucc.nau.edu/wew/fencing/agocchie.html).
4. **Recovery.** The plates and modern reconstructions show a return from the lunge to guard by withdrawing the front foot and the body. I did not retrieve treatise text describing the recovery in this session, so this step is [I/general HEMA practice].
5. **Spanish/Thibault alternative (1630).** The blade should not exceed the swordsman's navel height when he stands naturally (cross level with the navel). Straight quillons should equal the length of the sole of the foot. These figures are reported by secondary summaries ([Wikipedia: Thibault](https://en.wikipedia.org/wiki/G%C3%A9rard_Thibault_d%27Anvers); [Wikipedia: Rapier](https://www.wikipedia.org/wiki/Rapier)). Thibault's posture is upright, with a straight arm aligning the point at the opponent, in contrast to the Italians' deep lean [general description, not quoted from text this session].
6. **Weight feel.** The Wallace notes that very long rapier blades were "somewhat heavy and their balance point could be quite far forward of the guard" (seen in Wallace rapier records, e.g. objectId 61098). Measured POBs are 10–17.3 cm ahead of the guard block. **Animation [I]:** point-led, linear thrusts with small wrist rotations between guards. Avoid whippy, wide sabre-like cuts.

### 1.5 Evidence vs. inference (rapier)

- **Evidence [S]:** all overall, blade, guard, grip, weight and POB numbers in the tables; blade sections; hilt component descriptions; finishes.
- **Secondary but cited [T]:** the weight and POB range from the Fortner & Schrattenecker study (via Academie Duello), "about 2.4 cm" typical base width (Virtus Martialis), Thibault's proportions (secondary summaries).
- **Inference [I]:** ricasso length (about 5 cm), pommel size, tip width (about 1 cm), the reference build, the percentages, and the recovery mechanics.
- **Unresolved:** Fitzwilliam R14's date. Whether Wallace A599's 119.7 cm is the overall length. The exact Royal Armouries page URL for IX.879.

---

## 2. ZWEIHÄNDER: German/Swiss two-handed sword, c. 1500–1600 (straight blade as base model)

### 2.1 Specimen table

**Primary (combat-type) specimens**

| # | Institution / accession | Date, origin | Overall | Blade (incl. ricasso) | Blade width | Grip | Ricasso | Quillon span | Weight | POB | Record |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Z1 | **Cleveland 1919.70** "Two-Handed Sword" | 1550–1600. Germany | **170.5 cm** [S] | **125.6** [S] | n.p. | **43.2** [S] | **34.7** [S] | **53.7** [S] | n.p. | n.p. | [CMA 1919.70](https://www.clevelandart.org/art/1919.70) |
| Z2 | **Wallace Collection A472** | About 1530. Italy and Germany | n.p. | **122** [S] | **4.5** (record "width"; probably blade at base) [S] | **42.2** [S] | **12** [S] | **42.5** [S] | **3.01 kg** [S] | n.p. | [Wallace objectId 60965](https://wallacelive.wallacecollection.org/eMP/eMuseumPlus?service=ExternalInterface&module=collection&objectId=60965&viewType=detailView) |
| Z3 | **Royal Armouries IX.991** | Dated 1529. Germany | **156.5** (1565 mm) [S] | **118.1** (1181 mm) [S] | n.p. | n.p. | n.p. | n.p. | **2.3 kg** [S] (Shore 2004 also lists 5 lb 1 oz) | n.p. | [RA record (page returned by search)](https://collections.royalarmouries.org/object/rac-object-17332.html) |
| Z4 | **Cleveland 1919.71** "Two-Handed Sword with Flamboyant Blade" *(flamberge variant)* | 1550–1600. Germany | **168.9** [S] | **118.7** [S] | n.p. | **49.2** [S] | **26.7** [S] | **50.5** [S] | **2.98** (unit not shown; presumably kg) [S] | n.p. | [CMA 1919.71](https://clevelandart.org/art/1919.71) |

**Supplementary combat-type and comparison specimens**

| # | Institution / accession | Date, origin | Overall | Blade | Grip | Ricasso | Quillons | Weight | Notes / record |
|---|---|---|---|---|---|---|---|---|---|
| Z5 | Cleveland 1919.68 | 1550–1600. Germany | 191.5 [S] | 144.8 [S] | 40.7 [S] | 33.4 [S] | 41.5 [S] | n.p. | [Record](https://www.clevelandart.org/print/art/1919.68) |
| Z6 | Royal Armouries IX.633 | About 1500 | 162.0 [S] | 113.0 [S] | n.p. | n.p. | n.p. | 3.17 kg [S] | Large roughly spherical pommel, straight quillons, flattened-lozenge blade, modern leather grip binding [S] |
| Z7 | Royal Armouries IX.926 | c. 1550. German | n.p. | n.p. | n.p. | n.p. | n.p. | 7 lb 6 oz (3.35 kg) [S, as quoted by Shore 2004] | [Shore, JWMA 2004](https://ejmas.com/jwma/articles/2004/jwmaart_shore_1004.htm) |
| Z8 | Worcester Art Museum (ex-Higgins) object 48774 | About 1600 (1600–1650). German | 175.3 [S] | 127.6 [S] (second dimension, presumed blade) | n.p. | n.p. | n.p. | 7 lb 15 oz (about 3.6 kg) [S] | Restored black wooden grip [S]. [Record](https://worcester.emuseum.com/objects/48774/twohanded-sword) |
| Z9 | KHM Vienna, Hofjagd- und Rüstkammer A 975 | Undated in snippet | L 164 [S] | n.p. | n.p. | n.p. | B (width) 45.5 [S]. T 17 | n.p. | Blackened iron, wood, leather [S]. [Record](https://www.khm.at/en/artworks/bihaender-373423) |
| Z10 | KHM A 863 | n.p. | L 184.5 [S] | n.p. | n.p. | n.p. | B 44 [S] | n.p. | [Record](https://www.khm.at/en/artworks/bihaender-373301-1) |
| Z11 | Cleveland 1916.1509 *(Iberian montante comparison)* | 1550–1600. Spain, Toledo | 168.3 [S] | 126.4 [S] | 41.3 [S] | 20.3 [S] | 35.2 [S] | 2.2 kg [S] | Wood and leather grip, fluted pommel (third-party mirror). [Record](https://www.clevelandart.org/art/1916.1509) |
| Z12 | Cleveland 1916.1507 *(Iberian comparison)* | 1550–1600. Spain, Toledo(?) | 167.3 [S] | 126 [S] | 40 [S] | 17.2 [S] | 31.8 [S] | 2.24 kg [S] | [Record](https://www.clevelandart.org/print/art/1916.1507) |

**Ceremonial, guard and processional ("Paratschwert") specimens: do not use for combat feel**

| # | Institution / accession | Date | Overall | Blade | Quillons / width | Weight | Notes / record |
|---|---|---|---|---|---|---|---|
| C1 | **Met 04.3.60**, Two-Handed Processional Sword carried by the Guard of Duke Julius of Brunswick | 1573 | 195.5 cm (77 in) [S] | n.p. | W. 53 cm, D. 21 cm [S] | **4653 g** (10 lb 4 oz) [S] | Steel, wood, leather, velvet [S]. [Met 25077](https://www.metmuseum.org/art/collection/search/25077) |
| C2 | Cleveland 1916.1508, Two-Handed Sword of the State Guard of Julius of Brunswick-Lüneburg | 1574 | 186.1 [S] | 132.1 [S] | Quillons 51.4 [S]. Grip 45.7, ricasso 25.1 [S] | n.p. | "Steel, leather and wire bound grip" [S]. [Record](https://www.clevelandart.org/print/art/1916.1508) |
| C3 | Royal Armouries IX.628 (arms of the Cologne Beer Brewers' Guild) | 1571–1599 | 190.5 (1905 mm) [S] | 128.3 (1283 mm) [S] | Long quillons, side-rings [S] | **9 lb 9 oz (4.34 kg)** [S] | Flattened-diamond blade, long ricasso, "rather feeble horns or flukes" like the 1573 Brunswick guard set (e.g. IX.629) [S]. [Record](https://collections.royalarmouries.org/object/rac-object-1434.html) |
| C4 | Met, Two-Handed Sword (accession not captured; Riggs gift 1913) | ca. 1560. South German, Munich(?) | 182.8 (72 in) [S] | 132 (52 in) [S] | n.p. | **4677.7 g** (10 lb 5 oz) [S] | Weight puts it in the guard/parade class [I]. [Met 27347](https://www.metmuseum.org/art/collection/search/27347) |

### 2.2 Typical-range summary

| Parameter | Combat-type range [T] | Ceremonial / guard [T] | Notes |
|---|---|---|---|
| Overall | 156.5–191.5 cm (most 165–175) | 182.8–195.5 cm | |
| Blade (incl. ricasso) | 113–144.8 cm (most 118–128) | 128–132 cm | |
| Blade as % of overall | 70–76 % [I] | 67–72 % [I] | Z1 73.7 %, Z3 75.5 %, Z4 70.3 %, Z5 75.6 % |
| **Grip** | **40–49.2 cm** [S] (Z1 43.2, Z2 42.2, Z4 49.2, Z5 40.7. CMA figures may include the pommel) | 45.7 cm (C2) | The brief's "45–55 cm?" is **slightly long**: measured grips are 40–49 cm |
| Ricasso | 12 cm (c. 1530, Z2) to 26.7–34.7 cm (1550–1600, Z1, Z4, Z5) | 25.1 cm (C2) | Iberian 17.2–20.3 cm. A trend toward longer ricassos later in the century is my inference from these data [I], consistent with Melville (2000) |
| Ricasso as % of blade | 10 % (Z2) to 22–28 % (Z1, Z4, Z5) [I] | 19 % (C2) | |
| Quillon span | 41.5–53.7 cm [S] | 51.4–53 cm | KHM widths 42.5–45.5 cm. Iberian 31.8–35.2 cm |
| Quillons as % of blade | 29–43 % [I] | about 39 % | Z1 42.8 %, Z4 42.5 %, Z2 34.8 %, Z5 28.7 % |
| Blade width at base | **4.5 cm** (Z2 only) [S] | n.p. | No other base or point widths were published in the records found |
| Weight | **2.2–3.6 kg** [S] (Z3 2.3, Z2 3.01, Z4 2.98, Z6 3.17, Z7 3.35, Z8 about 3.6) | **4.34–4.68 kg** [S] | Woosnam-Savage (Royal Armouries), quoted by Shore: "fighting two-handed sword weighed (on average) between 5–7 lbs" (2.3–3.2 kg) [T, secondary quote] |
| POB | n.p. for every specimen | n.p. | |

### 2.3 Anatomy notes for modelling (straight-blade base model)

- **Pommel.** Spherical (Z2 "spherical pommel chiselled with acanthus leaves"; Z6 "large, roughly spherical") or pear-shaped (Joanneum Graz description of the type) [S]. Fluted on Iberian examples (Z11) [S].
- **Grip.** Very long: 40–49 cm, about 25 % of overall [S, I]. Z2: "tapering wooden octagon bound with black leather" [S]. C2: "leather and wire bound grip" [S]. Many have a swelling in the middle. CMA has one grip "cloth-covered middle" [S, from a CMA record extraction]. **Model** as an octagonal or square stack, slightly waisted, so two hands can sit 15–25 cm apart [I].
- **Cross-guard.** A long straight or slightly recurved bar: 41.5–53.7 cm span, about 29–43 % of blade length [S, I]. **Side-rings** are documented on the cross (C3 "long quillons, side-rings") [S]. A Wallace-based replica description says side rings protected the ungauntleted hand during binds [secondary]. **Model:** one ring on each face of the cross, centred on the blade, about 8–10 cm diameter [I. Ring size n.p.].
- **Ricasso.** An unsharpened section below the cross, often leather-covered. A Fitzwilliam two-hander (HEN.M.195-1933) is catalogued "with flamboyant blade and leather covered ricasso" [S]. Another Fitzwilliam record has its ricasso "covered with leather and reinforced with steel studs" [S]. Its length is 25–35 cm on later-16th-c. German swords (Z1, Z4, Z5) and only 12 cm on c. 1530 Z2 [S].
- **Parierhaken (parrying hooks, "flukes", "lugs").** Located at the top (blade end) of the ricasso, where the leather cover ends and the sharpened blade begins [general typology; consistent with Melville 2000]. Late examples have "longer lugs hooked strongly towards the point". Lugs set so close to the hilt that the ricasso cannot be gripped behind them suggest the sword was no longer meant mainly for war ([Melville, JWMA 2000](https://ejmas.com/jwma/articles/2000/jwmaart_melville_0100.htm)). RA IX.628 has "rather feeble horns or flukes" [S]. **Size n.p.** for all specimens. **Model:** two pointed hooks, each projecting about 4–7 cm from the blade edge and angled toward the tip [I].
- **Blade.** Hexagonal section (Z2), flattened diamond (C3), flattened lozenge (Z6) [S]. Base width 4.5 cm (Z2) [S]. Point width n.p. A gradual taper to an acute point is described on Z6 [S]. **Model:** about 4.5 cm wide at the hooks, tapering to about 2.5–3 cm before the point [I].
- **Flamberge variant.** Cleveland 1919.71 has the same hilt layout with a flamboyant (wavy) blade: 118.7 cm blade, 2.98 kg [S]. A Fitzwilliam flamboyant two-hander has a leather-covered ricasso [S]. Treat it as a blade-swap variant of the straight model.

**Reference proportions (recommended straight-blade build) [I, derived mainly from Z1, Z2 and Z4]**

| Part | Reference value | % of overall (170 cm) |
|---|---|---|
| Overall | 170 cm | 100 % |
| Pommel | about 7 cm [I] | 4 % |
| Grip (wrapped section) | about 38 cm [I], between CMA Z1 "grip" 43.2 (probably incl. pommel) and Wallace Z2 42.2 | 22 % |
| Cross-guard bar thickness (along blade axis) | about 3 cm [I] | 2 % |
| Blade incl. ricasso | 122 cm [T: Z2 122, Z4 118.7, Z1 125.6] | 72 % |
| of which ricasso (leather-covered) | 28 cm [T: Z1 34.7, Z4 26.7, Z5 33.4] | 16.5 % (23 % of blade) |
| of which sharpened blade beyond hooks | about 94 cm | 55 % |
| Parierhaken | at the top of the ricasso, projecting about 5 cm each side [I] | |
| Blade width | 4.5 cm at hooks [S, Z2] → about 3 cm before point [I] | |
| Quillon span | 50 cm | 29 % (41 % of blade) |
| Side rings | one per face, about 9 cm diameter [I] | |
| Target mass | 3.0 kg (combat). Parade variant: 4.5 kg | |

**Colours and materials for textures (all [S])**
- Blackened iron hilt (KHM A 975, KHM 371491).
- Black leather over a wooden grip (Z2).
- Leather, or leather with steel studs, on the ricasso (Fitzwilliam two-handers).
- Brass wire and velvet (KHM 536710). Velvet, leather and wood (Met C1).
- Etched, chiselled and gilded decoration (Z2).
- Iron hilt with chiselled pommel (C3). Etched guild arms on the blade (C3).

### 2.4 Handling and documented technique (for animation)

**What is documented**
1. **Two hands on a long grip, plus a ricasso grip for close quarters.** "Two-handed swords typically have a generous ricasso to allow the blade to be safely gripped below the quillons and thus wielded more effectively at close quarters" ([Shore, ARMA](https://thearma.org/essays/twohandedgreatsword.html)). Melville describes later two-handers with long, wood- and leather-bound ricassos and strongly hooked lugs ([JWMA 2000](https://ejmas.com/jwma/articles/2000/jwmaart_melville_0100.htm)). **Animation:** a main stance with both hands on the grip; an alternate "short" stance with the lead hand on the leather ricasso behind the Parierhaken.
2. **Closest surviving written method: the Iberian montante.**
   - **Godinho, *Arte de Esgrima* (1599).** Manuscript in Spanish. It contains the longest known text on the montante. Its rules cover situations such as facing another montante, a narrow street, being surrounded in a wide street, four streets, and a plaza ([hroarr](https://hroarr.com/?p=18494); [Freelance Academy Press, Rivera translation](https://www.freelanceacademypress.com/iberianswordplaydomingoluisgodinhosartoffencing1599.aspx)).
   - **Figueyredo, *Memorial da Prattica do Montante* (1651; some sources give 1653).** Written for Prince Teodósio of Bragança. Catalogued as 16 rules plus general advice on cutting and thrusting sequences ([HEMA overview](https://www.historicaleuropeanmartialarts.com/?p=12407)).
   - **Character of the method.** The montante is used against several opponents, in confined and open spaces. One French study note reads Figueyredo's *talho* as a rising diagonal false-edge cut with the hand pronated, and says each rule starts with the point on the ground and the right hand at the guard. That note is a personal study chart, so treat these details as unverified.
   - **Animation [I]:** continuous alternating diagonal cuts (forehand/backhand) with passing steps, wide arcs crossing the centreline, and recovery through a high or rear chamber rather than a return to a static guard.
3. **Italian two-hand sword (spadone).** Marozzo (1536) and Alfieri's *Lo Spadone* (1653) illustrate guards for the two-handed sword ([AEMMA, Alfieri](https://aemma.org/onlineResources/alfieri/alfieriHome_body.htm); [archive.org, *Lo spadone*](https://archive.org/details/lospadone00alfi)). I could not retrieve guard-by-guard text in this session.
4. **German sources are thin.** Rüther notes that technical descriptions of the German battle sword are scarce. Information comes mainly from battle descriptions, military theorists (Frönsperger 1555 is cited) and paintings. The battle sword was grouped with halberds as a "short weapon" in formations ([Rüther, Hroarr](https://hroarr.com/?p=36074)). Joachim Meyer (1570) teaches the **longsword** ("Schwert"). Two-handed swords appear in his illustrations, but his system is not a dedicated Zweihänder method ([Wikipedia: Meyer](https://en.wikipedia.org/wiki/Joachim_Meyer)). By the later 16th century the great sword survived mostly in sportive school fencing ([Wikipedia: Zweihänder](https://en.wikipedia.com/wiki/Zweihander)).
5. **Doppelsöldner role: disputed.** Doppelsöldner were Landsknechte who took front-line risk for double pay. The tradition that Zweihänder training itself earned double pay, and the "breaking the pike hedge" use, are not confirmed by primary sources and are probably a later myth (traceable at least to the 17th c.) ([Wikipedia: Doppelsöldner](https://en.wikipedia.org/wiki/Doppels%C3%B6ldner)). Guarding the standard (banner) is another commonly cited role (secondary).

**For animation [I]:** heavy, committed, whole-body cuts driven by the hips and steps. Wind-ups over the shoulder or from a low hanging guard. Use the ricasso grip for short thrusts. Recover by continuing the blade's arc into the next cut, not by stopping dead. Combat pieces at 2.2–3.2 kg move faster than the "huge and slow" stereotype.

### 2.5 Evidence vs. inference (Zweihänder)

- **Evidence [S]:** all lengths, grips, ricassos, quillon spans and weights in the tables; blade sections; leather-covered ricassos; side-rings; flukes; finishes.
- **Secondary [T]:** Woosnam-Savage's 5–7 lb average (via Shore); Melville's lug and ricasso observations; montante treatise contents (overviews, not the primary texts).
- **Inference [I]:** Parierhaken projection, ring diameter, pommel length, point width, the reference build, and the cut-flow animation.
- **Caveat:** Cleveland's "grip" may include the pommel. Z1's blade shape (straight) is inferred from its title, which contrasts with Z4's "Flamboyant Blade". Its hooks and rings are not described in the retrieved text.

---

## 3. KATANA: Edo period (1603–1868), in koshirae

### 3.1 Specimen table

| # | Institution / accession | Date, smith | Overall (mounted) | Nagasa / blade | Sori | Motohaba / sakihaba | Kasane | Nakago (tang) | Tsuka | Tsuba | Record |
|---|---|---|---|---|---|---|---|---|---|---|---|
| K1 | **Met 91.2.56** (pair with wakizashi 91.2.84) | Blade dated 1839 by Naotane Taikei (1778–1857), Bizen style. Engraving attributed to (Honjō) Yoshitane. Tsuba by Yukinaka (Hagi). Mounting 19th c. | **99.8 cm** (39¼ in) [S] | **Cutting edge 72.7 cm** (28⅝ in) [S]. "L. of blade" 93.8 cm (incl. tang) [S] | **3.1 cm** (1 7/32 in) [S] | n.p. | n.p. | about 21.1 cm [I: 93.8 − 72.7] | n.p. (hilt plus guard about 27.1 cm [I: 99.8 − 72.7]) | n.p. | [Met 21889](https://www.metmuseum.org/art/collection/search/21889); pair [Met 638804](https://www.metmuseum.org/art/collection/search/638804) |
| K2 | **Fitzwilliam HEL/ARM.274-1946** (katana blade in *tachi* mounting) | 1625–1645 | **99.7 cm** [S] | **69.5 cm** [S] | **1.9 cm** [S] | n.p. | n.p. | **21.4 cm** (ubu, slender, narrowing) [S] | n.p. (hilt plus guard about 30.2 cm [I], tachi-style) | **7.8 × 7.2 cm** (gilt tachi mokkō type) [S] | [Fitzwilliam 163255](https://data.fitzmuseum.cam.ac.uk/id/object/163255) |
| K3 | **Tokyo National Museum**: 刀 水心子正秀 (Katana, Suishinshi Masahide), signed and dated Bunka 5 (1808) | 1808 | n.p. | **73.3 cm** [S] | **2.0 cm** [S] | n.p. | n.p. | n.p. | n.p. | n.p. | [Bunka Isan Online 564028](https://online.bunka.go.jp/heritages/detail/564028) |
| K4 | **Tokyo National Museum**: 刀 銘 肥前国忠吉／同国刳物宗長 (Hizen Tadayoshi; carving by Munenaga) | Edo, 17th c. | n.p. | **68.2 cm** [S] | **1.8 cm** [S] | n.p. | n.p. | n.p. | n.p. | n.p. | [Bunka Isan Online 506699](https://online.bunka.go.jp/index.php/heritages/detail/506699) |
| K5 | **Tokyo Fuji Art Museum**, katana signed "Nagasone Okisato Nyūdō Kotetsu" | Early Edo (17th c.), Musashi | n.p. | **70.5 cm** [S] | **1.5 cm** [S]. "Shallow… slight koshi-zori" | n.p. | n.p. | n.p. | n.p. | n.p. | [Fujibi 07601](https://www.fujibi.or.jp/en/collection/artwork/07601/) |

**Mounting-only and fitting data points**
- **Tokugawa Art Museum.** Daishō mountings of Tokugawa Yoshikatsu (14th lord of Owari), fish-bone inlay, **black-lacquered scabbard**, Edo 1857/1854. Katana mounting **l. 95.1 cm**, wakizashi 54.5 cm [S] ([record](https://tokugawa-art-museum.jp/en/about/treasures/armor-metal/101)).
- **Hikone Castle Museum.** Daishō mountings for Ii Naoaki, 19th c. Total lengths: long sword 107.0 cm, short 75.4 cm [S] ([record](https://hikone-castle-museum.jp/en/?p=2004)). On a related Ii set the handle is wound with lacquer-coated sharkskin and bound with braid [S] ([record](https://hikone-castle-museum.jp/en/?p=2006)).
- **Cleveland 1919.364.** Iron tsuba (Chōshū type), **diameter 7.6 cm** [S] ([record](https://openaccess-api.clevelandart.org/api/collectiononline/metadata/1919.364)).
- **Met tsuba records** (Edo and Edo-dated) surfaced by search give **H. 7.0–8.6 cm, W. 6.5–8.3 cm, thickness 0.3–0.8 cm** [S]. I could not map each figure to its exact page in this session (e.g. [Met 29520](https://www.metmuseum.org/art/collection/search/29520), [Met 35912](https://www.metmuseum.org/art/collection/search/35912)).
- **Met 36.25.1728a, b** (toppei-koshirae, a style that emerged at the end of the Edo period; blade 16th c.): L. 81.6 cm, blade 71.8 cm, cutting edge 56.4 cm, curvature 0.9 cm [S] ([Met 24378](https://www.metmuseum.org/art/collection/search/24378)). This is a short blade, so it is not used for the reference build.

### 3.2 Typical-range summary

| Parameter | Range [T] | Source / notes |
|---|---|---|
| Nagasa (Edo specimens) | **68.2–73.3 cm** [S] | K1–K5 |
| Edo "standard length" (*jōsun* 定寸) | **2 shaku 3 sun 5 bu ≈ 71.2 cm** per [Nihonto Club glossary](https://nihontoclub.com/glossary-terms/j%C5%8Dsun). Wikipedia reports a cap of **2 shaku 3 sun ≈ 69.7 cm** under Iemitsu for some classes of sword-carrier, and 2 shaku 2 sun 8 bu (68.6 cm) under Ietsuna ([Wikipedia: Katana](https://www.wikipedia.org/wiki/Katana)) | **Verify flag:** forum-quoted edicts (1638: katana ≤ 84.8 cm; Kanbun 10/1670: ≤ 2 shaku 8–9 sun) conflict ([NMB thread](https://militaria.co.za/nmb/topic/47265-edo-period-length-and-ownership-restrictions)). Conclusion: about 69.7–71.2 cm is the documented *conventional* standard. The legal limits are unresolved |
| Sori | **1.5–2.0 cm** (2.1–2.7 % of nagasa) [S, I] for 17th to early 19th c. 3.1 cm on the 1839 Bizen-style revival blade (K1) | Kanbun-era (1661–73) *shintō* shape: about 70 cm, strong taper, very shallow sori, compact chū-kissaki ([Markus Sesko, Kantei 1 – Sugata #6](https://markussesko.com/2015/04/03/kantei-1-sugata-6/)) |
| Nakago | 21.1–21.4 cm [S, I] | K1, K2 |
| Overall mounted | 95.1–107 cm (99.7–99.8 for K1 and K2) [S] | Tokugawa 95.1. Hikone 107.0 (may include scabbard; unlabelled) |
| Tsuka (incl. fuchi and kashira) | **n.p.** for all cited specimens | About 26 cm inferred from K1 (27.1 cm hilt plus guard, minus about 1 cm tsuba and seppa) [I]. A secondary source cites about 24 cm average [T, weak] |
| Tsuba | 7.0–8.6 cm high, 6.5–8.3 cm wide, 0.3–0.8 cm thick [S] | Cleveland 7.6 cm diameter. K2 7.8 × 7.2 |
| Motohaba / sakihaba / kasane | **n.p.** for the cited Edo specimens | NBTHK-published examples (era not stated in the retrieved text): motohaba 2.9 cm, sakihaba 2.0 cm, motokasane 0.65 cm, kissaki length 3.65 cm on a 2 shaku 3 sun blade ([NBTHK translations, e.g. no. 818](https://www.touken.or.jp/Portals/0/pdf/english/tobi_translation/818_NBTHK_March_2025.pdf)) [T]. An NBTHK issue 691 Kan'ei-era Kunisuke entry gave **conflicting** extractions, so it is not used |

### 3.3 Anatomy notes for modelling

**Blade (shinogi-zukuri)**
- A ridge line (*shinogi*) runs the length of the blade, nearer the back (*mune*) than the edge. *Shinogi-ji* is the flat between ridge and back; *hira-ji* is the flat between ridge and edge.
- The *yokote* is the transverse line that separates the point (*kissaki*) from the body. Sakihaba is measured at the yokote ([NBTHK term definitions via search](https://www.touken.or.jp/Portals/0/pdf/english/tobi_translation/675_NBTHK_April_2013.pdf)).
- The **chū-kissaki** is typical of Edo shintō (Sesko). Kissaki length is about 2.85–3.65 cm in NBTHK examples [T].
- Mune: *iori-mune* (peaked, two-faced) is the usual form. The NBTHK commentary vocabulary uses "ihorimune" [T, general].
- **Sori types.** *Torii-zori*: deepest curve around the centre of the blade. *Koshi-zori*: deepest curve near or inside the tang ([NCJSC glossary](https://www.ncjsc.org/visual-glossary/sori)). K5 (Kotetsu) is "shallow, with slight koshi-zori" [S]. **Model:** torii-zori, with the deepest point at about 45–50 % of the nagasa from the munemachi, 1.6–1.9 cm deep [I].

**Mounting (koshirae), from tip to pommel**

| Part | Function | Modelling note |
|---|---|---|
| *Habaki* | Blade collar that locks the blade into the saya | About 3–4 cm long, just above the tang shoulders [I] |
| *Seppa* | Thin washers on either side of the tsuba | Two plates about 0.1–0.2 cm thick [I] |
| *Tsuba* | Guard | Round or slightly oval, 7–8 cm across, 0.3–0.8 cm thick [S] |
| *Fuchi* | Collar at the guard end of the hilt | |
| *Tsuka* | Hilt: wooden core covered in *same* (ray skin) and wrapped in *tsuka-ito* braid. A Met record defines the tsuka as "the hilt of a sword or dagger mounting, including the grip and all of the fittings above the tsuba" (Met tsuka record surfaced by search; exact page ID not confirmed) | About 26 cm [I]. Diamond (*hishi*) pattern of exposed same between ito crossings |
| *Menuki* | Grip ornaments under the wrap, one on each side | Small raised bumps mid-grip, offset (omote and ura) |
| *Kashira* | Pommel cap; secures the final knot of the ito | |
| *Saya* | Scabbard; black lacquer common (Tokugawa, Hikone, BM 1998,1217.2) | About nagasa + 5 cm [I] |

**Reference proportions (recommended build) [I, derived from K1–K5 and the typical NBTHK values]**

| Part | Reference value | % of overall (100 cm) |
|---|---|---|
| Overall (tip to kashira) | 100 cm | 100 % |
| Nagasa | 71 cm | 71 % |
| Sori | 1.8 cm, deepest about mid-blade | 2.5 % of nagasa |
| Motohaba → sakihaba | 3.0 → 2.1 cm [T] | |
| Kasane | 0.7 → 0.5 cm [T, I] | |
| Kissaki (chū) | about 3.3 cm long [T] | |
| Habaki | about 3.5 cm [I] | |
| Tsuba plus seppa | 0.6 + 0.3 cm, Ø 7.5 cm | about 1 % (Ø about 10 % of nagasa) |
| Tsuka | 26–27 cm | 26–27 % |

**Colours and materials for textures**
- Black-lacquered saya [S]: Tokugawa Art Museum 1857; Hikone black-lacquered scabbards; British Museum 1998,1217.2, "black lacquered wood".
- Ray skin (*same*) under silk wrap; ray skin is sometimes lacquered [S]: Hikone.
- Fittings of shakudō (black-patinated copper alloy), shibuichi (grey), gold, silver and copper [S]: V&A O199618, "lacquered wood, ray fish skin and silk; metal fittings of shibuichi, shakudo, gold, silver and copper"; V&A O485276, "lacquered wood, rayfish skin and silk; metal fittings of shakudo and gold".
- Iron tsuba [S]: Cleveland 1919.364.
- **Tsuka-ito colour:** black, dark blue (*kon*) and brown are common on surviving koshirae [I, general knowledge; not verified against a cited specimen].
- Habaki: copper or gilt copper [I, general].

### 3.4 Handling and documented technique (for animation)

1. **How it is worn.** Edge up, thrust through the sash (obi), on the left hip. The Kyoto National Museum's introduction explains: blade facing down = tachi (slung from hangers); blade facing up = katana, wakizashi or tantō ([Kyoto National Museum PDF](https://www.kyohaku.go.jp/old/eng/special/assets/pdf/2018_katana_intro_eng_0929.pdf)). Being thrust through the obi edge-up allowed drawing and cutting in one motion ([Wikipedia: Katana](https://www.wikipedia.org/wiki/Katana)). **Animation:** the draw (*nukitsuke*) comes out edge-up from the left hip, with the left hand turning the saya (*saya-biki*) [I, general practice].
2. **Two-handed grip.** Right hand just behind the tsuba; left hand at the bottom of the tsuka, level with the kashira; a gap between the hands. Grip pressure comes mainly from the little and ring fingers ("little finger tight, index finger light") ([kenshi247: tenouchi](https://kenshi247.net/blog/2014/07/03/tenouchi/)). In Musō Jikiden Eishin-ryū the sword is gripped with all ten fingers, and leaving fingers off the end of the handle is "not appropriate" ([SMAA, Suino](https://www.smaa-hq.com/articles/article/te-no-uchi-gripping-the-sword-in-muso-jikiden-eishin-ryu-iaido)).
3. **Basic cuts** ([Wikipedia: Tameshigiri](https://en.wikipedia.com/wiki/Tameshigiri); [iaido glossary](https://www.funet.fi/~magi/harrasteet/iaido/sanasto.html)):
   - **kesa-giri**: downward diagonal, shoulder to opposite hip
   - **kiri-age / gyaku-kesa**: upward diagonal
   - **yoko (tsuihei)**: horizontal
   - **makkō / jōdan / kiri-oroshi**: straight vertical downward cut ([hyoho.com](https://www.hyoho.com/Tosa4.html))
4. **The iai sequence as an animation template.** Ōmori-ryū *Mae*, the first kata of Musō Jikiden Eishin-ryū: horizontal draw-cut (nukitsuke) → raise overhead (furikaburi) → vertical kiri-oroshi → **chiburi** → **nōtō** ([Universidad de León article](https://revistas.unileon.es/index.php/artesmarciales/article/download/214/173/716); [hyoho.com](https://hyoho.com/Tosaroponme.html)).
   - **Chiburi** ("shaking off the blood") is performed before nōtō ([Wikipedia: Chiburi](https://en.wikipedia.org/wiki/Chiburi)). In MJER the blade moves horizontally to the right with the edge facing right (*yoko-chiburi*).
   - In ZNKR Seitei *Mae* the chiburi is the larger *ō-chiburi*, formally "kesa-ni-furioroshite-no-chiburi" ([AKBAN wiki](https://akban.org/wiki/Seitei_gata_-_Mae_前)).
   - **Nōtō** is re-sheathing; concentration (zanshin) is maintained throughout.
5. **Schools.**
   - **Yagyū Shinkage-ryū and Ono-ha Ittō-ryū** were the two official sword schools of the Tokugawa shogunate. Ono Tadaaki of Ittō-ryū taught Hidetada ([Wikipedia: Ono Tadaaki/Mikogami Tenzen](https://Www.Wikipedia.org/wiki/Mikogami_Tenzen); [Budo Japan](https://budojapan.com/?p=32334)).
   - **Katori Shintō-ryū** (founded by Iizasa Ienao, 15th c.) and **Musō Jikiden Eishin-ryū** (iaijutsu; lineage traced to Hayashizaki Jinsuke) are named here as standard references; their founding details were **not verified in this session** ([Wikipedia: MJER](https://en.wikipedia.com/wiki/Muso_Jikiden_Eishin-ryu)).

### 3.5 Evidence vs. inference (katana)

- **Evidence [S]:** nagasa, sori and nakago of K1–K5; overall mounted lengths; tsuba sizes; edge-up wear; grip and cut terminology; the MJER sequence; materials and finishes.
- **Secondary or typical [T]:** *jōsun* values; the Edo regulation figures (conflicting); NBTHK-sample widths and kasane; Sesko's Kanbun-shintō shape description.
- **Inference [I]:** tsuka length (about 26 cm, derived from K1); habaki and seppa sizes; deepest-sori position; saya length; ito colours; the reference build.

---

## 4. Bibliography: URLs consulted

All of these were consulted through search-engine extraction of the page content. Direct fetch of `metmuseum.org` and `collectionapi.metmuseum.org` was blocked by this session's network allowlist.

**Rapier: museum records**
- https://wallacelive.wallacecollection.org/eMP/eMuseumPlus?service=ExternalInterface&module=collection&objectId=61062&viewType=detailView (A569)
- https://wallacelive.wallacecollection.org/eMP/eMuseumPlus?service=ExternalInterface&module=collection&objectId=61063&viewType=detailView (A570)
- https://wallacelive.wallacecollection.org/eMP/eMuseumPlus?service=ExternalInterface&module=collection&objectId=61101&viewType=detailView (Caino rapier)
- https://wallacelive.wallacecollection.org/eMP/eMuseumPlus?service=ExternalInterface&module=collection&objectId=61065&viewType=detailView (A572)
- https://wallacelive.wallacecollection.org/eMP/eMuseumPlus?service=ExternalInterface&module=collection&objectId=61092&viewType=detailView (A599)
- https://wallacelive.wallacecollection.org/eMP/eMuseumPlus?service=ExternalInterface&module=collection&objectId=61169&viewType=detailView (A676)
- https://wallacelive.wallacecollection.org/eMP/eMuseumPlus?service=ExternalInterface&module=collection&objectId=61098&viewType=detailView
- https://smartify.org/artworks/unknown-artist--maker-rapier (Wallace A580 summary)
- https://collections.vam.ac.uk/item/O97250/swept-hilt-rapier-sadeler-daniel
- https://api.vam.ac.uk/v2/object/O97250
- https://collections.vam.ac.uk/item/O97533
- https://collections.vam.ac.uk/item/O97278/swept-hilt-rapier-unknown
- https://api.vam.ac.uk/v2/object/O97278
- https://www.metmuseum.org/art/collection/search/23042 (28.100.3)
- https://www.metmuseum.org/art/collection/search/626129
- https://www.metmuseum.org/art/collection/search/24867 (1973.27.5)
- https://www.metmuseum.org/art/collection/search/25063 (04.3.32)
- https://www.metmuseum.org/art/collection/search/27433 (14.25.1048)
- https://www.metmuseum.org/art/collection/search/22368 (14.25.1199)
- https://www.metmuseum.org/art/collection/search/27313 (Pietro de Formicano blade)
- https://www.metmuseum.org/art/collection/search/712616 (2016.310)
- https://www.clevelandart.org/print/art/1916.1719
- https://openaccess-api.clevelandart.org/api/collectiononline/metadata/1916.1719
- https://www.clevelandart.org/print/art/1916.1634
- https://www.clevelandart.org/print/art/1916.702
- https://openaccess-api.clevelandart.org/api/collectiononline/metadata/1916.702
- https://www.clevelandart.org/art/1916.695
- https://collections.royalarmouries.org/object/rac-object-40750.html (IX.879, page as returned by search)
- https://data.fitzmuseum.cam.ac.uk/id/object/18950
- https://data.fitzmuseum.cam.ac.uk/id/object/18966
- https://data.fitzmuseum.cam.ac.uk/id/object/18964

**Rapier: treatises and secondary sources**
- https://wiktenauer.com/wiki/Page:Lo_Schermo,_overo_Scienza_d’Arme_(Salvator_Fabris)_1606.pdf/10
- https://wiktenauer.com/wiki/Page:Gran_Simulacro_dell'Arte_e_dell'Uso_della_Scherma_(Ridolfo_Capo_Ferro_da_Cagli)_1601.pdf/34
- https://www.wiktenauer.com/wiki/Gran_Simulacro_dell'Arte_e_dell'Uso_della_Scherma_(Ridolfo_Capo_Ferro_da_Cagli)
- https://en.wikipedia.org/wiki/Ridolfo_Capo_Ferro
- https://guywindsor.net/2015/07/size-matters-how-long-should-your-rapier-be/
- https://www.bookandsword.com/2015/08/01/how-can-ancient-art-help-us-read-ridolfo-capo-ferro/
- https://en.wikipedia.org/wiki/G%C3%A9rard_Thibault_d%27Anvers
- https://wiktenauer.com/wiki/Academie_de_l'Espee_(Gerard_Thibault_d'Anvers)
- https://www.wikipedia.org/wiki/Rapier
- https://thearma.org/rapierglossary.htm
- https://www.thearma.org/essays/saviologlossary.htm
- https://cs.unc.edu/~hudson/saviolo/glossary.html
- https://jan.ucc.nau.edu/wew/fencing/agocchie.html
- https://bop.unibe.ch/apd/article/download/11602/16402/64116
- https://davidbiggs.substack.com/p/how-to-hold-the-rapier
- https://academieduello.com/blog/choosing-right-rapier
- https://virtusmartialis.substack.com/p/a-look-at-three-ring-rapiers
- https://jan.ucc.nau.edu/~wew/fencing/blades.html

**Zweihänder: museum records**
- https://www.clevelandart.org/art/1919.70
- https://openaccess-api.clevelandart.org/api/collectiononline/metadata/1919.70
- https://clevelandart.org/art/1919.71
- https://www.clevelandart.org/print/art/1919.68
- https://www.clevelandart.org/print/art/1916.1508
- https://openaccess-api.clevelandart.org/api/collectiononline/metadata/1916.1508
- https://www.clevelandart.org/art/1916.1509
- https://www.clevelandart.org/print/art/1916.1507
- https://wallacelive.wallacecollection.org/eMP/eMuseumPlus?service=ExternalInterface&module=collection&objectId=60965&viewType=detailView (A472)
- https://collections.royalarmouries.org/object/rac-object-17332.html (IX.991, page as returned by search)
- https://collections.royalarmouries.org/object/rac-object-26.html
- https://collections.royalarmouries.org/object/rac-object-1434.html (IX.628)
- https://www.metmuseum.org/art/collection/search/25077 (04.3.60)
- https://www.metmuseum.org/art/collection/search/27347
- https://worcester.emuseum.com/objects/48774/twohanded-sword
- https://www.khm.at/en/artworks/bihaender-373423
- https://www.khm.at/en/artworks/bihaender-373301-1
- https://www.khm.at/en/artworks/bihaender-371491-1
- https://www.khm.at/en/artworks/schwert-schlachtschwert-zweihaender-bihaender-536710
- https://www.museum-joanneum.at/en/styrian-armoury/discover/collection/edged-weapons/two-handed-swords
- https://data.fitzmuseum.cam.ac.uk/id/object/18867
- https://data.fitzmuseum.cam.ac.uk/id/object/18871

**Zweihänder: technique and secondary sources**
- https://thearma.org/essays/twohandedgreatsword.html
- https://ejmas.com/jwma/articles/2004/jwmaart_shore_1004.htm
- https://ejmas.com/jwma/articles/2000/jwmaart_melville_0100.htm
- https://hroarr.com/?p=36074
- https://hroarr.com/?p=18494
- https://www.historicaleuropeanmartialarts.com/?p=12407
- https://www.freelanceacademypress.com/iberianswordplaydomingoluisgodinhosartoffencing1599.aspx
- https://aemma.org/onlineResources/alfieri/alfieriHome_body.htm
- https://archive.org/details/lospadone00alfi
- https://en.wikipedia.org/wiki/Doppels%C3%B6ldner
- https://en.wikipedia.com/wiki/Zweihander
- https://en.wikipedia.org/wiki/Joachim_Meyer
- https://docs.google.com/document/d/1cCldUOdZ8F62fb_hYnexvuYCBdp3YksRJpPI-_6edi0/export?format=pdf (French montante study note; weak)

**Katana: museum records**
- https://www.metmuseum.org/art/collection/search/21889 (91.2.56)
- https://www.metmuseum.org/art/collection/search/638804
- https://www.metmuseum.org/art/collection/search/21913
- https://www.metmuseum.org/art/collection/search/24378 (36.25.1728a, b)
- https://www.metmuseum.org/art/collection/search/24388 (surfaced alongside the tsuka-definition record; ID not confirmed as that record)
- https://www.metmuseum.org/art/collection/search/29520
- https://www.metmuseum.org/art/collection/search/35912
- https://data.fitzmuseum.cam.ac.uk/id/object/163255
- https://online.bunka.go.jp/heritages/detail/564028
- https://online.bunka.go.jp/index.php/heritages/detail/506699
- https://online.bunka.go.jp/heritages/detail/516969
- https://www.fujibi.or.jp/en/collection/artwork/07601/
- https://tokugawa-art-museum.jp/en/about/treasures/armor-metal/101
- https://hikone-castle-museum.jp/en/?p=2004
- https://hikone-castle-museum.jp/en/?p=2006
- https://openaccess-api.clevelandart.org/api/collectiononline/metadata/1919.364
- https://www.britishmuseum.org/collection/object/A_1998-1217-2
- https://collections.vam.ac.uk/item/O199618
- https://collections.vam.ac.uk/item/O485276
- https://www.kyohaku.go.jp/old/eng/special/assets/pdf/2018_katana_intro_eng_0929.pdf

**Katana: references, technique and secondary sources**
- https://nihontoclub.com/glossary-terms/j%C5%8Dsun
- https://www.wikipedia.org/wiki/Katana
- https://militaria.co.za/nmb/topic/47265-edo-period-length-and-ownership-restrictions
- https://markussesko.com/2015/04/03/kantei-1-sugata-6/
- https://markussesko.com/2015/02/19/
- https://www.ncjsc.org/visual-glossary/sori
- https://www.touken.or.jp/Portals/0/pdf/english/tobi_translation/818_NBTHK_March_2025.pdf
- https://www.touken.or.jp/Portals/0/pdf/english/tobi_translation/691_NBTHK_August_2014.pdf
- https://www.touken.or.jp/Portals/0/pdf/english/tobi_translation/675_NBTHK_April_2013.pdf
- https://kenshi247.net/blog/2014/07/03/tenouchi/
- https://www.smaa-hq.com/articles/article/te-no-uchi-gripping-the-sword-in-muso-jikiden-eishin-ryu-iaido
- https://en.wikipedia.com/wiki/Tameshigiri
- https://www.funet.fi/~magi/harrasteet/iaido/sanasto.html
- https://revistas.unileon.es/index.php/artesmarciales/article/download/214/173/716
- https://hyoho.com/Tosaroponme.html
- https://www.hyoho.com/Tosa4.html
- https://en.wikipedia.org/wiki/Chiburi
- https://akban.org/wiki/Seitei_gata_-_Mae_前
- https://Www.Wikipedia.org/wiki/Mikogami_Tenzen
- https://budojapan.com/?p=32334
- https://en.wikipedia.com/wiki/Muso_Jikiden_Eishin-ryu
