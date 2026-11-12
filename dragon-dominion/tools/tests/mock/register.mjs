// Node loader hook: resolves "@minecraft/server" to the test mock.
// Used as: node --import ./tools/tests/mock/register.mjs --test ...
import { register } from "node:module";

register("./hooks.mjs", import.meta.url);
