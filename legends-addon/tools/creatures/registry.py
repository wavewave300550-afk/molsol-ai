"""All creature builders, in build order."""
from . import alicorn, hanuman, logos, nidhogg, props, taotie, tenko

ALL = {
    "taotie": taotie.build,
    "nidhogg": nidhogg.build,
    "hanuman": hanuman.build,
    "alicorn": alicorn.build,
    "tenko": tenko.build,
    "logos": logos.build_logos,
    "seraph": logos.build_seraph,
    "cherub": logos.build_cherub,
    "ophan": logos.build_ophan,
}
BOSSES = ["taotie", "nidhogg", "hanuman", "alicorn", "tenko", "logos"]
CHOIR = ["seraph", "cherub", "ophan"]
PROPS = list(props.ALL)
ALL.update(props.ALL)
