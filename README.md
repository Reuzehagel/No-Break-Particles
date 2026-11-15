# The Resource Pack To Keep Your Screen Clean
No Break Particles removes those crazy breaking particles!
![Feature Image](https://i.imgur.com/wNxbpnD.png)

## Compatibility
Every Minecraft release from 1.8 on. New releases get a pack automatically within a week.

## Building
- `uv run build.py <version> ...` downloads that version's client jar from Mojang and writes `dist/NoBreakParticles.<version>.zip`.
- `uv run test.py <version> ...` loads the built pack in the real game (needs `uv tool install portablemc`) and prints any pack errors from the log.
- `uv run publish.py` shows which new releases need a pack; `--go` builds them and uploads to CurseForge, Modrinth and a GitHub release. The weekly workflow in `.github/workflows` runs this.

## Mod Support
Do you want to see your favorite mod without particles?
Request a mod to be added [here](https://github.com/Reuzehagel/No-Break-Particles/issues/new/choose).

## Screenshots
Without NBP
![Without NBP](https://github.com/Reuzehagel/No-Break-Particles/blob/main/Without%20NBP_compressed.gif)

With NBP
![With NBP](https://github.com/Reuzehagel/No-Break-Particles/blob/main/With%20NBP_compressed.gif)
