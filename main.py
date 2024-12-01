"""Creatining an optimization solution for Capacitated Vehicle Routing Problem with Time Windows (CVRPWT) using ortools."""

import argparse

from optimizer.main import main

DEFAULT_DATA_SOURCE = "sample"

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-d",
        "--data_source",
        type=str,
        default=DEFAULT_DATA_SOURCE,
        help="Directory name",
    )
    parser.add_argument(
        "-s",
        "--no_save_solution",
        action="store_false",
        help="Do not save solution file if passed",
    )
    parser.add_argument(
        "-l",
        "--no_log_solution",
        action="store_false",
        help="Do not log solution files in logs",
    )
    parser.add_argument(
        "-u",
        "--update_expected_solution",
        action="store_true",
        help="Update expected solution file",
    )
    arguments = parser.parse_args()
    main(
        data_source=arguments.data_source,
        save_solution=arguments.no_save_solution,
        log_solution=arguments.no_log_solution,
        update_expected_solution=arguments.update_expected_solution,
    )
