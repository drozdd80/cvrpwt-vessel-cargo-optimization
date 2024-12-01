#!/bin/bash

set -euo pipefail

script_dir="$(cd "$(dirname "$0")" && pwd)"
project_root="$(git rev-parse --show-toplevel)"

OUTPUT_DIR="$project_root/data/output/logs"

SOLUTION_FILE="$project_root/data/output/solution.csv"

RUN_OPTIMIZER=false
ACTIVATE_IPYTHON=false
RUN_BOTH=false
DATA_SOURCE=""

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    -r|--run)
      RUN_OPTIMIZER=true
      shift
      ;;
    -i|--input)
      ACTIVATE_IPYTHON=true
      shift
      ;;
    -b|--run_both)
      RUN_BOTH=true
      shift
      ;;
    -d|--data_source)
      DATA_SOURCE="$2"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done

run_optimizer() {
  local script_path="$1"
  if [ -n "$DATA_SOURCE" ]; then
    python3 "$script_path" -d "$DATA_SOURCE"
  else
    python3 "$script_path"
  fi
}

# If -b flag is set, stash all changes, run optimizer, unstash, and rerun
if $RUN_BOTH || $RUN_OPTIMIZER; then
  echo "test"
  if $RUN_BOTH; then
    # Stash current changes
    echo "Stashing all changes..."
    git stash --include-untracked
    if [ $? -ne 0 ]; then
      echo "Failed to stash changes. Exiting."
      exit 1
    fi
    echo "Running optimizer script after stashing..."
    run_optimizer "$project_root/main.py"
    if [ $? -ne 0 ]; then
      echo "Optimizer failed"
      exit 1
    fi
    # Unstash the changes
    echo "Unstashing changes..."
    git stash pop
    if [ $? -ne 0 ]; then
      echo "Failed to unstash changes. Exiting."
      exit 1
    fi
  fi
  echo "Optimizer script after unstashing..."
  run_optimizer "$project_root/main.py"
  if [ $? -ne 0 ]; then
    echo "Optimizer failed"
    exit 1
  fi
fi

# Check if the solution file exists
if [ ! -f "$SOLUTION_FILE" ]; then
  echo "Solution file $SOLUTION_FILE does not exist."
  exit 1
fi

# Find the biggest folder by name
BIGGEST_FOLDER=$(ls -1 "$OUTPUT_DIR" | sort | tail -n 1 | head -n 1)

# Find the second biggest folder by name
SECOND_BIGGEST_FOLDER=$(ls -1 "$OUTPUT_DIR" | sort | tail -n 2 | head -n 1)

BIGGEST_FOLDER_PATH="$OUTPUT_DIR/$BIGGEST_FOLDER"
# Path to the second biggest folder
SECOND_BIGGEST_FOLDER_PATH="$OUTPUT_DIR/$SECOND_BIGGEST_FOLDER"

if $RUN_BOTH; then
  # Find the CSV file with the biggest filename in the second biggest folder
  BIGGEST_FILE=$(find "$BIGGEST_FOLDER_PATH" -maxdepth 1 -type f -name "*.csv" | sort | tail -n 2 | head -n 1)
else
  # Find the CSV file with the biggest filename in the second biggest folder
  BIGGEST_FILE=$(find "$SECOND_BIGGEST_FOLDER_PATH" -maxdepth 1 -type f -name "*.csv" | sort | tail -n 1)
fi

# Check if the biggest file exists
if [ -z "$BIGGEST_FILE" ]; then
  echo "No CSV files found in the second biggest folder: $SECOND_BIGGEST_FOLDER_PATH"
  exit 1
fi

# Function to compare two files
compare_files() {
  local file1="$1"
  local file2="$2"
  local additional_arg="$3"

  if cmp -s "$file1" "$file2"; then
    echo "Files are the same."
  else
    echo "Files are different."
    # Path to the Python script
    COMPARE_SCRIPT="$script_dir/solution_differences.py"
    # Run the Python script to compare the files
    python3 "$COMPARE_SCRIPT" "$SOLUTION_FILE" "$BIGGEST_FILE" "$additional_arg"
  fi
}

compare_files "$SOLUTION_FILE" "$BIGGEST_FILE" $ACTIVATE_IPYTHON

exit 0