import { registerSpell } from "../core/registry";
import dw01 from "./dw01_seraphic_litany";
import dw02 from "./dw02_cherubic_testament";
import dw03 from "./dw03_ophanim";
import dw04 from "./dw04_sanctuary";
import dw05 from "./dw05_heavenly_throne";
import dw06 from "./dw06_word_before_creation";
import dn01 from "./dn01_reverie_procession";
import dn02 from "./dn02_nightmare_intrusion";
import dn03 from "./dn03_shifting_house";
import dn04 from "./dn04_lullaby_and_scream";
import dn05 from "./dn05_sleeping_city";
import dn06 from "./dn06_the_dreamer";
import ed01 from "./ed01_genesis_colossus";
import ed02 from "./ed02_thermal_tyrant";
import ed03 from "./ed03_abyssal_cryotitan";
import ed04 from "./ed04_aether_raptor";
import ed05 from "./ed05_buried_kingdoms";
import ed06 from "./ed06_world_before_names";

export function registerAllSpells(): void {
  for (const s of [dw01, dw02, dw03, dw04, dw05, dw06, dn01, dn02, dn03, dn04, dn05, dn06, ed01, ed02, ed03, ed04, ed05, ed06]) registerSpell(s);
}
