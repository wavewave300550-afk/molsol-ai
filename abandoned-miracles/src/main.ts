/**
 * The Abandoned Miracles - script entry point.
 *
 * Wiring only: the encounter framework lives in ./core, each boss in ./bosses/<name>.
 * Stable Script API only (@minecraft/server 2.11.0, @minecraft/server-ui 2.3.0);
 * no beta modules and no experimental toggles.
 */
import { boot } from "./boot";
import { MODULE as cantor } from "./bosses/cantor";
import { MODULE as nomos } from "./bosses/nomos";
import { MODULE as orison } from "./bosses/orison";
import { MODULE as vesperra } from "./bosses/vesperra";

boot({ vesperra, cantor, nomos, orison });
