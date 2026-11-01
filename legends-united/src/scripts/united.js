// Commands shared by the whole pack.
import { CommandPermissionLevel, CustomCommandStatus, ItemStack, Player, system } from "@minecraft/server";
export const EGGS = [
    "dim11:archon", "dim11:sovereign", "dim11:observer",
    "fb:void_emperor", "fb:titan", "fb:devouring_star", "fb:world_parasite", "fb:choir",
    "legends:taotie", "legends:nidhogg", "legends:hanuman", "legends:alicorn", "legends:tenko", "legends:logos",
];
system.beforeEvents.startup.subscribe((ev) => {
    try {
        ev.customCommandRegistry.registerCommand({ name: "clash:eggs", description: "Receive the spawn egg of every boss", permissionLevel: CommandPermissionLevel.GameDirectors, cheatsRequired: true }, (origin) => {
            const p = origin.sourceEntity;
            if (!(p instanceof Player))
                return { status: CustomCommandStatus.Failure, message: "Players only." };
            system.run(() => {
                const inv = p.getComponent("minecraft:inventory")?.container;
                for (const id of EGGS) {
                    try {
                        inv?.addItem(new ItemStack(`${id}_spawn_egg`, 1));
                    }
                    catch (e) {
                        console.warn(`[clash] no spawn egg for ${id}: ${e}`);
                    }
                }
            });
            return { status: CustomCommandStatus.Success, message: `${EGGS.length} spawn eggs` };
        });
    }
    catch (e) {
        console.warn(`[clash] commands unavailable: ${e}`);
    }
});
