#!/bin/bash
mkdir -p VintedBot
git mv cogs VintedBot/
git mv data VintedBot/
git mv docs VintedBot/
git mv utils VintedBot/
git mv main.py VintedBot/
git mv critere.md VintedBot/
git mv market_data.db VintedBot/ || true
git mv requirements.txt VintedBot/
git mv test_*.py VintedBot/ || true

echo "VintedBot files moved"
