"""The block ledger marker (src/lib/ledger.ts): one invisible persistent entity per chunk a spell changes,
holding the record of that chunk's changed blocks so they come back after a crash or a quit."""


def build(pack):
    pack.marker("ledger", display="Grimoire Block Ledger")
