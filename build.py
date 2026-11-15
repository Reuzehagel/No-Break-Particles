"""Build No Break Particles for one or more Minecraft versions.

Usage: python build.py 1.21.11 1.8.9 ...

Downloads the official client jar, copies every vanilla model that sets a
"particle" texture with that texture pointed at a blank image, and writes
dist/NoBreakParticles.<version>.zip.
"""
import json
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).parent
CACHE = ROOT / ".cache"
DIST = ROOT / "dist"
MANIFEST = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
DESCRIPTION = "Makes the break particles invisible! §8by Reuzehagel"
# Jars before 1.14 carry no pack_version in version.json.
SKIP = {"water.json", "lava.json"}  # left out of the hand-made releases
OLD_FORMATS ={"1.8": 1, "1.9": 2, "1.10": 2, "1.11": 3, "1.12": 3, "1.13": 4}


def fetch(url):
    with urllib.request.urlopen(url) as r:
        return r.read()


def client_jar(version):
    jar = CACHE / f"{version}.jar"
    if not jar.exists():
        versions = json.loads(fetch(MANIFEST))["versions"]
        meta_url = next(v["url"] for v in versions if v["id"] == version)
        url = json.loads(fetch(meta_url))["downloads"]["client"]["url"]
        CACHE.mkdir(exist_ok=True)
        jar.write_bytes(fetch(url))
    return jar


def pack_format(jar, version):
    """Resource pack format as (major, minor)."""
    try:
        pv = json.loads(jar.read("version.json"))["pack_version"]
    except KeyError:
        return OLD_FORMATS[".".join(version.split(".")[:2])], 0
    if isinstance(pv, int):  # 1.14 - 1.16.1
        return pv, 0
    if "resource_major" in pv:  # 1.21.9+
        return pv["resource_major"], pv.get("resource_minor", 0)
    return pv["resource"], 0


def mcmeta(fmt):
    major, minor = fmt
    if major >= 65:  # 1.21.9+ reads min_format/max_format instead of pack_format
        pack = {"description": DESCRIPTION, "min_format": [major, minor], "max_format": [major, minor]}
    else:
        pack = {"pack_format": major, "description": DESCRIPTION}
    return json.dumps({"pack": pack}, indent=4)


def build(version):
    with zipfile.ZipFile(client_jar(version)) as jar:
        fmt = pack_format(jar, version)
        # Before the 1.13 flattening the block texture folder was "blocks".
        tex_dir = "blocks" if fmt[0] < 4 else "block"
        out = DIST / f"NoBreakParticles.{version}.zip"
        DIST.mkdir(exist_ok=True)
        count = 0
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as pack:
            pack.writestr("pack.mcmeta", mcmeta(fmt))
            pack.write(ROOT / "pack" / "pack.png", "pack.png")
            pack.write(ROOT / "pack" / "blank.png", f"assets/minecraft/textures/{tex_dir}/blank.png")
            for name in sorted(jar.namelist()):
                if not (name.startswith("assets/minecraft/models/") and name.endswith(".json")):
                    continue
                if name.rsplit("/", 1)[1] in SKIP:
                    continue
                model = json.loads(jar.read(name))
                if "particle" in model.get("textures", {}):
                    model["textures"]["particle"] = f"{tex_dir}/blank"
                    pack.writestr(name, json.dumps(model, indent=4))
                    count += 1
    print(f"{out.name}: format {fmt[0]}.{fmt[1]}, {count} models")
    return out


if __name__ == "__main__":
    for v in sys.argv[1:]:
        build(v)
