#!/usr/bin/env bash

# Usage: ./rename-plugin.sh oldname newname
# Example: ./rename-plugin.sh example mysuperplugin

set -euo pipefail

OLD_NAME="$1"
NEW_NAME="$2"

# 1. Rename files with OLD_NAME in the filename
find . -type f -name "*${OLD_NAME}*" | while read -r file; do
  dir=$(dirname "$file")
  base=$(basename "$file")
  new_base="${base//$OLD_NAME/$NEW_NAME}"
  new_path="$dir/$new_base"
  mv "$file" "$new_path"
  echo "Renamed file: $file -> $new_path"
done

# 2. Replace occurrences of OLD_NAME in file content
echo "Replacing content inside files..."
find . -type f -print0 | xargs -0 sed -i "s/${OLD_NAME}/${NEW_NAME}/g"

# 3. Rename directories with OLD_NAME in the path (from deepest up)
echo "Renaming directories..."
find . -depth -type d -name "*${OLD_NAME}*" | while read -r dir; do
  parent=$(dirname "$dir")
  base=$(basename "$dir")
  new_base="${base//$OLD_NAME/$NEW_NAME}"
  new_path="$parent/$new_base"
  mv "$dir" "$new_path"
  echo "Renamed directory: $dir -> $new_path"
done

echo "✅ All done."
