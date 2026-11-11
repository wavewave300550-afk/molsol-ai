"""Create a fresh flat BDS test world with the Beta APIs experiment (dev harness only)."""
import sys, os, shutil, json
sys.path.insert(0, os.path.dirname(__file__))
import bnbt
from bnbt import Tag

def make(world_dir, template, beta=True):
    ver, name, root = bnbt.read_level_dat(template)
    B = lambda v: Tag(bnbt.TAG_BYTE, v)
    root['Generator'] = Tag(bnbt.TAG_INT, 2)  # flat
    root['FlatWorldLayers'] = Tag(bnbt.TAG_STRING, json.dumps({
        "biome_id": 1,
        "block_layers": [
            {"block_name": "minecraft:bedrock", "count": 1},
            {"block_name": "minecraft:dirt", "count": 2},
            {"block_name": "minecraft:grass_block", "count": 1}],
        "encoding_version": 6, "structure_options": None, "world_version": "version.post_1_18"}))
    root['domobspawning'] = B(0); root['doweathercycle'] = B(0); root['dodaylightcycle'] = B(0)
    root['cheatsEnabled'] = B(1); root['commandsEnabled'] = B(1); root['showcoordinates'] = B(1)
    root['Time'] = Tag(bnbt.TAG_LONG, 6000)
    root['SpawnX'] = Tag(bnbt.TAG_INT, 0); root['SpawnY'] = Tag(bnbt.TAG_INT, 32767); root['SpawnZ'] = Tag(bnbt.TAG_INT, 0)
    root['LevelName'] = Tag(bnbt.TAG_STRING, os.path.basename(world_dir))
    exp = {'experiments_ever_used': B(1 if beta else 0), 'saved_with_toggled_experiments': B(1 if beta else 0)}
    if beta:
        exp['gametest'] = B(1)
    root['experiments'] = Tag(bnbt.TAG_COMPOUND, exp)
    if os.path.exists(world_dir):
        shutil.rmtree(world_dir)
    os.makedirs(world_dir)
    bnbt.write_level_dat(os.path.join(world_dir, 'level.dat'), ver, name, root)
    open(os.path.join(world_dir, 'levelname.txt'), 'w').write(os.path.basename(world_dir))

if __name__ == '__main__':
    make(sys.argv[1], sys.argv[2], beta=(len(sys.argv) < 4 or sys.argv[3] != 'nobeta'))
