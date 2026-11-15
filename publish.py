# /// script
# dependencies = ["requests"]
# ///
"""Build packs and publish them to CurseForge, Modrinth and a GitHub release.

Usage:
  uv run publish.py              dry run: what new Minecraft releases need a pack
  uv run publish.py --go         build and publish those
  uv run publish.py --go 1.8.9   build and publish specific packs (see GROUPS)

Env: MODRINTH_TOKEN, CURSEFORGE_TOKEN; GitHub release uses the gh CLI.
"""
import datetime
import json
import os
import subprocess
import sys

import requests

import build

MODRINTH_PROJECT = "ctcDyQTJ"
CURSEFORGE_PROJECT = 988824
UA = {"User-Agent": "Reuzehagel/No-Break-Particles"}
# Pack built from the newest patch of each format range -> every version it serves.
GROUPS = {
    "1.8.9": ["1.8", "1.8.1", "1.8.2", "1.8.3", "1.8.4", "1.8.5", "1.8.6", "1.8.7", "1.8.8", "1.8.9"],
    "1.10.2": ["1.9", "1.9.1", "1.9.2", "1.9.3", "1.9.4", "1.10", "1.10.1", "1.10.2"],
    "1.12.2": ["1.11", "1.11.1", "1.11.2", "1.12", "1.12.1", "1.12.2"],
    "1.14.4": ["1.13", "1.13.1", "1.13.2", "1.14", "1.14.1", "1.14.2", "1.14.3", "1.14.4"],
    "1.16.1": ["1.15", "1.15.1", "1.15.2", "1.16", "1.16.1"],
    "1.16.5": ["1.16.2", "1.16.3", "1.16.4", "1.16.5"],
    "1.17.1": ["1.17", "1.17.1"],
    "1.20.6": ["1.20.5", "1.20.6"],
    "1.21.8": ["1.21.7", "1.21.8"],
    "1.21.10": ["1.21.9", "1.21.10"],
    "26.1.2": ["26.1", "26.1.1", "26.1.2"],
}


def modrinth_versions():
    r = requests.get(f"https://api.modrinth.com/v2/project/{MODRINTH_PROJECT}/version", headers=UA)
    r.raise_for_status()
    return r.json()


def new_releases(published):
    """Mojang releases newer than the newest version any published pack covers."""
    covered = {gv for v in published for gv in v["game_versions"]}
    manifest = requests.get(build.MANIFEST, headers=UA).json()["versions"]
    new = []
    for v in manifest:  # newest first
        if v["type"] != "release":
            continue
        if v["id"] in covered:
            break
        new.append(v["id"])
    return new[::-1]


def curseforge(zip_path, label, game_versions, changelog):
    token = {"X-Api-Token": os.environ["CURSEFORGE_TOKEN"], **UA}
    api = "https://minecraft.curseforge.com/api"
    types = {t["id"] for t in requests.get(f"{api}/game/version-types", headers=token).json()
             if t["slug"].startswith("minecraft-")}
    ids = {v["name"]: v["id"] for v in requests.get(f"{api}/game/versions", headers=token).json()
           if v["gameVersionTypeID"] in types}
    missing = [g for g in game_versions if g not in ids]
    if missing:
        raise SystemExit(f"CurseForge has no game version {missing}")
    meta = {"changelog": changelog, "changelogType": "markdown", "displayName": label,
            "gameVersions": [ids[g] for g in game_versions], "releaseType": "release"}
    with open(zip_path, "rb") as f:
        r = requests.post(f"{api}/projects/{CURSEFORGE_PROJECT}/upload-file", headers=token,
                          data={"metadata": json.dumps(meta)}, files={"file": f})
    r.raise_for_status()


def modrinth(zip_path, label, game_versions, changelog):
    data = {"name": f"No Break Particles {game_versions[0]}", "version_number": label,
            "changelog": changelog, "dependencies": [], "game_versions": game_versions,
            "version_type": "release", "loaders": ["minecraft"], "featured": False,
            "project_id": MODRINTH_PROJECT, "file_parts": ["file"], "primary_file": "file"}
    with open(zip_path, "rb") as f:
        r = requests.post("https://api.modrinth.com/v2/version",
                          headers={"Authorization": os.environ["MODRINTH_TOKEN"], **UA},
                          data={"data": json.dumps(data)}, files={"file": (zip_path.name, f, "application/zip")})
    r.raise_for_status()


def github_release(zips, changelog):
    tag = datetime.date.today().strftime("%d.%m.%Y")
    files = [str(z) for z in zips]
    if subprocess.run(["gh", "release", "view", tag], capture_output=True).returncode == 0:
        subprocess.run(["gh", "release", "upload", tag, "--clobber", *files], check=True)
    else:
        subprocess.run(["gh", "release", "create", tag, "--title", "🎊 Release", "--notes", changelog, *files], check=True)


def main(args):
    go = "--go" in args
    published = modrinth_versions()
    taken = {v["version_number"] for v in published}
    targets = [a for a in args if a != "--go"] or new_releases(published)
    # A release inside a known group publishes as that group's pack, once.
    in_group = {gv: key for key, gvs in GROUPS.items() for gv in gvs}
    targets = list(dict.fromkeys(in_group.get(t, t) for t in targets))
    if not targets:
        print("Nothing new to publish.")
        return
    done, notes = [], []
    for version in targets:
        game_versions = GROUPS.get(version, [version])
        label = f"{game_versions[0]}a"
        span = game_versions[0] if len(game_versions) == 1 else f"{game_versions[0]} - {game_versions[-1]}"
        changelog = f"- Added compatibility for Minecraft {span}"
        if label in taken:
            print(f"skip {version}: Modrinth already has {label}")
            continue
        zip_path = build.build(version)
        print(f"{'publish' if go else 'would publish'} {zip_path.name} as {label} for {span}")
        if go:
            # CurseForge first: a version on Modrinth marks the pack as fully published.
            curseforge(zip_path, label, game_versions, changelog)
            modrinth(zip_path, label, game_versions, changelog)
        taken.add(label)
        done.append(zip_path)
        notes.append(changelog)
    if go and done:
        github_release(done, "🎊 Release\n\n" + "\n".join(notes))


if __name__ == "__main__":
    main(sys.argv[1:])
