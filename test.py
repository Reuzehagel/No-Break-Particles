"""Load built packs in the real game and report what the log says about them.

Usage: python test.py 1.21.11 1.8.9 ...   (needs portablemc: uv tool install portablemc)

Starts each version offline with dist/NoBreakParticles.<version>.zip enabled,
waits for resources to load, closes the game and prints pack-related log lines.
"""
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).parent
GAME = ROOT / ".cache" / "game"  # shared versions, libraries, assets, JVMs
LOADED_GRACE = 60  # seconds to let model baking finish after the reload line
TIMEOUT = 1200  # first run of a version downloads the game
# Errors an offline account always causes; not about the pack.
OFFLINE_NOISE = re.compile(r"realms|authlib|user properties|Status: 401|profile", re.I)
SUSPECT = re.compile(r"NoBreakParticles|incompatib|missing texture|unable to load|failed to load|exception|ERROR", re.I)


def run(version):
    pack = ROOT / "dist" / f"NoBreakParticles.{version}.zip"
    mc = ROOT / ".cache" / "test" / version
    (mc / "resourcepacks").mkdir(parents=True, exist_ok=True)
    shutil.copy(pack, mc / "resourcepacks" / pack.name)
    # 1.13+ names folder/zip packs "file/<name>"; older versions use the bare name.
    old = version.startswith("1.") and int(version.split(".")[1]) < 13
    packs = f'["{pack.name}"]' if old else f'["vanilla","file/{pack.name}"]'
    (mc / "options.txt").write_text(f"resourcePacks:{packs}\nonboardAccessibility:false\n")
    log = mc / "logs" / "latest.log"
    log.unlink(missing_ok=True)

    proc = subprocess.Popen(["portablemc", "--main-dir", str(GAME), "start", version,
                             "--mc-dir", str(mc), "-u", "Tester"],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace")
    out, start, loaded_at = [], time.time(), None
    threading.Thread(target=lambda: out.extend(proc.stdout), daemon=True).start()
    while time.time() - start < TIMEOUT and proc.poll() is None:
        text = log.read_text(errors="replace") if log.exists() else "".join(out)
        if loaded_at is None and "Reloading ResourceManager" in text:
            loaded_at = time.time()
        if loaded_at and time.time() - loaded_at > LOADED_GRACE:
            break
        time.sleep(2)
    subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
    time.sleep(2)

    text = log.read_text(errors="replace") if log.exists() else "".join(out)
    lines = [l for l in text.splitlines() if SUSPECT.search(l) and not OFFLINE_NOISE.search(l)]
    status = "loaded" if loaded_at else "NEVER REACHED RESOURCE RELOAD"
    print(f"\n===== {version}: {status} ({len(lines)} suspect lines)")
    for l in lines[:60]:
        print("  " + l[:300])
    if not loaded_at:
        print("  last output:", *out[-15:], sep="\n  ")


if __name__ == "__main__":
    for v in sys.argv[1:]:
        run(v)
