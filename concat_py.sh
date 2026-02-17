#!/bin/bash

folder="inventory_app"
output="0000tempfullcode.py"

# Clear or create output file
> "$output"

for f in "$folder"/*.py; do
  [ -e "$f" ] || continue

  filename=$(basename "$f")

  echo "# ---------------------------------------------------------------------------------------------------" >> "$output"
  echo "# ${filename}=================>" >> "$output"
  cat "$f" >> "$output"
  echo -e "\n# ===========================>\n" >> "$output"
done

echo "Done. All .py files from $folder concatenated into $output"

