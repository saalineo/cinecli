MODULES = {
    "yts": "yts",
    "eztv": "eztv",
    "tpb": "tpb",
    "x1337": "x1337",
    "solid": "solid_torrents",
    "galaxy": "torrent_galaxy",
    "zooqle": "zooqle",
    "nyaa": "nyaa",
    "lime": "limetorrents",
    "rarbg": "rarbg",
    "btdig": "dht",
}

NAMES = list(MODULES.keys())

for _name, _module in MODULES.items():
    globals()[_name] = __import__(f"search.providers.{_module}", fromlist=["*"])

def get(name):
    return globals()[name]
