"""All boss models by key."""
import boss_emperor
import boss_titan
import boss_star
import boss_parasite
import boss_choir

MODELS = {
    "void_emperor": boss_emperor.build,
    "titan": boss_titan.build,
    "devouring_star": boss_star.build,
    "world_parasite": boss_parasite.build,
    "choir": boss_choir.build,
}
