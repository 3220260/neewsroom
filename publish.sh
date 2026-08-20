#!/bin/bash
# Ανεβάζει τα τελευταία άρθρα στο GitHub.
# Χρήση:  ./publish.sh  (από το Terminal του Mac)
set -e
cd "$(dirname "$0")"
python3 scripts/build.py
git add -A
git commit -m "Ενημέρωση: $(date '+%d/%m/%Y')" || { echo "Δεν υπάρχουν αλλαγές."; exit 0; }
git push
echo "Έγινε."
