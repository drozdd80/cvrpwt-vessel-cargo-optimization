# Test Module

`python -m pytest tests/test.py`

run tests that optimizer works for existing data sources.

Check that solution file is the same as expected_solution file.

To update expected_solution file run optimizer with `-u` argument `python main.py -u`

# Test scripts

## Compare current solution with previous commit
Run `bash tests/solution_verification.sh -r -i -d <data_source>` to compare solution.csv with the solution file from previous commit.
Uses solution files saved in `data/output/logs`. Compares current solution file with last file from second to last commit (assumes that it was done right before committing).

`bash tests/solution_verification.sh -b` to compare solution.csv with current commit temporarily stashing all the files

optional arguments:
- `-r`: run optimizer before comparing the outputs
- `-b`: run optimizer with files stashed, unstashed, compare the outputs.
- `-i`: if there is a difference between solution files, ipython is getting opened with dataframes of both files and their comparison loaded
- `-d <data_source>`: passes name of the <data_source> subfolder to the optimizer