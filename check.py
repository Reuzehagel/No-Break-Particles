"""Golden test: build.py must reproduce the hand-made 1.21.4 release exactly.

Usage: uv run check.py   (needs the gh CLI to fetch the release asset)
"""
import json
import subprocess
import sys
import zipfile

import build

GOLDEN_TAG, GOLDEN_ASSET = "02.02.2025", "NoBreakParticles.1.21.4.zip"


def models(path):
    with zipfile.ZipFile(path) as z:
        return {n: json.loads(z.read(n)) for n in z.namelist() if n.endswith(".json") and "/models/" in n}


def main():
    build.CACHE.mkdir(exist_ok=True)
    subprocess.run(["gh", "release", "download", GOLDEN_TAG, "-p", GOLDEN_ASSET, "-D", str(build.CACHE), "--clobber"], check=True)
    want, got = models(build.CACHE / GOLDEN_ASSET), models(build.build("1.21.4"))
    problems = [f"missing {n}" for n in sorted(set(want) - set(got))]
    problems += [f"extra {n}" for n in sorted(set(got) - set(want))]
    problems += [f"differs {n}" for n in sorted(set(want) & set(got)) if want[n] != got[n]]
    print("\n".join(problems) or f"OK: {len(got)} models match the 1.21.4 release")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
