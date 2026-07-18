#!/bin/zsh
set -euo pipefail

PROJECT_DIR="$PWD"
IMPORT_DIR="$PROJECT_DIR/data/imports"
SEED_SRC="$HOME/output/thaiculture_seed.json"
BOOKINGS_SRC="$HOME/output/bookings.csv"
INVOICES_SRC="$HOME/output/invoices.csv"
ITEMS_SRC="$HOME/output/invoice_items.csv"

mkdir -p "$IMPORT_DIR"

missing=0
for f in "$SEED_SRC" "$BOOKINGS_SRC" "$INVOICES_SRC" "$ITEMS_SRC"; do
  if [[ ! -f "$f" ]]; then
    echo "Missing file: $f"
    missing=1
  fi
done

if [[ "$missing" -ne 0 ]]; then
  echo ""
  echo "Expected files are under ~/output, not ./output inside the project."
  echo "Copy step aborted."
  exit 1
fi

cp "$SEED_SRC" "$IMPORT_DIR/"
cp "$BOOKINGS_SRC" "$IMPORT_DIR/"
cp "$INVOICES_SRC" "$IMPORT_DIR/"
cp "$ITEMS_SRC" "$IMPORT_DIR/"

echo ""
echo "Imported files into: $IMPORT_DIR"
ls -lah "$IMPORT_DIR"
