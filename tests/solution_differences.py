import sys

import pandas as pd


def compare_csv(file1_path: str, file2_path: str, ipy: str) -> None:
    """Compare if 2 csv file are identical or not.

    Optionally if ipy is 'true' open IPython instance
    with dataframes of the respective csv files loaded as df1 and df2.
    """
    df1 = pd.read_csv(file1_path)
    df2 = pd.read_csv(file2_path)

    # Check if DataFrames are equal
    if df1.equals(df2):
        print(f"Files {file1_path} and {file2_path} are the same.")
    else:
        try:
            # Find differences by comparing DataFrames
            comparison = (
                df1.compare(df2, keep_shape=True, keep_equal=False)
                .dropna(how="all", axis=1)
                .dropna(how="all", axis=0)
            )

            print(comparison)

        except ValueError as e:
            print("File comparison failed")
            print(e)

        # if ipy argument is true enter Ipython when there is difference in files
        if ipy == "true":
            import IPython

            IPython.embed(user_ns={**globals(), **locals()})
        # Exit with a non-zero status code to block the commit
        sys.exit(1)


if __name__ == "__main__":
    # The two file paths are passed as arguments to the script
    if len(sys.argv) != 4:
        print("Invalid number of arguments")
        sys.exit(1)

    file1 = sys.argv[1]
    file2 = sys.argv[2]
    ipy = sys.argv[3]

    # Compare the two CSV files
    compare_csv(file1, file2, ipy)
