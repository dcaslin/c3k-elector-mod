# c3k-elector-mod

Crusader Kings III mod: **Elector Status**, a right-click character interaction that shows
which of your currently held titles the selected character votes in. Covers every elective
law (Tanistry, Saxon, Feudal, Princely, Scandinavian, Tribal, Confederation, clerical, and
modded ones) because it reads the game's own elector data. It is read-only.

Built for CK3 1.20.1.1.

```sh
scripts/install-macos.sh        # install to ~/Documents/Paradox Interactive/Crusader Kings III/mod
python3 scripts/validate.py     # static checks
scripts/load-test-macos.sh      # headless CK3 load test
```

Then enable "Elector Status" in your launcher playset. See [AGENTS.md](AGENTS.md) for the
architecture and development workflow, and [docs/TESTING.md](docs/TESTING.md) for the
in-game test plan.
