"""Run tests for the optimizer."""

import doctest
import os
from datetime import datetime

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point


import optimizer.dataset
from optimizer.main import main  # noqa: E402
from optimizer.matrices import (  # noqa: E402
    distance_matrix_with_virtual_locations,
    generate_distance_matrix,
    time_matrix_with_virtual_locations,
)

_path = os.path.dirname(__file__)

CACHE_FILENAME = f"test_solution_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.csv"


@pytest.fixture(scope="module")
def expected_solution_file(
    path: str = _path + "/../data/output/validation/expected_solution.csv",
):
    return pd.read_csv(path)


@pytest.fixture(scope="module")
def sample_solution(dir_path: str = _path + "/../data/output/"):
    """Create temporary solution file with a unique name."""
    main(
        data_source="sample",
        update_expected_solution=False,
        save_solution=True,
        log_solution=False,
        solution_filename=CACHE_FILENAME,
    )
    yield pd.read_csv(dir_path + CACHE_FILENAME)
    # delete temporary file
    if os.path.exists(dir_path + CACHE_FILENAME):
        os.remove(dir_path + CACHE_FILENAME)


def test_doctests():
    results = doctest.testmod(optimizer.dataset)
    assert results.failed == 0


def test_generate_distance_matrix():
    """Test the distance matrix generation."""
    projected_crs = 3857
    depot_name = "Location 1"
    distance_units = 1
    data = {
        "name": ["Location 1", "Location 2", "Location 3"],
        "geometry": [
            Point(0, 0),  # Location 1
            Point(0.027, 0),  # Location 2
            Point(0, 0.036),  # Location 3
        ],
    }
    gdf = gpd.GeoDataFrame(data, crs="EPSG:4326")

    result = generate_distance_matrix(gdf, projected_crs, depot_name, distance_units)

    expected = [
        [0, 0, 3005, 4007],
        [0, 0, 3005, 4007],
        [3005, 3005, 0, 5009],
        [4007, 4007, 5009, 0],
    ]

    assert result == expected, f"Expected {expected}, but got {result}"


def test_distance_matrix_with_virtual_locations():
    """Test the distance matrix creation with virtual locations."""
    data = {
        "locations_mapped": [0, 1, 1, 2, 2, 3, 3],  # Mapping real locations to indices
    }
    distance_matrix = [
        [0, 0, 30, 40],
        [0, 0, 30, 40],
        [30, 30, 0, 50],
        [40, 40, 50, 0],
    ]

    result = distance_matrix_with_virtual_locations(data, distance_matrix)

    expected = [
        [0, 0, 0, 30, 30, 40, 40],
        [0, 0, 0, 30, 30, 40, 40],
        [0, 0, 0, 30, 30, 40, 40],
        [30, 30, 30, 0, 0, 50, 50],
        [30, 30, 30, 0, 0, 50, 50],
        [40, 40, 40, 50, 50, 0, 0],
        [40, 40, 40, 50, 50, 0, 0],
    ]

    assert result == expected, f"Expected {expected}, but got {result}"


def test_time_matrix_with_virtual_locations():
    """Test the time matrix creation with virtual locations."""
    data = {
        "distance_matrix": [
            [0, 0, 0, 10, 30],
            [0, 0, 0, 10, 30],
            [0, 0, 0, 10, 30],
            [10, 10, 10, 0, 25],
            [30, 30, 30, 25, 0],
        ],
        "loading_unloading_time": [0, 30, 20, 20, 30],
        "location_category_map": {
            "depot": "depot",
            "Port 1": "port",
            "Port 2": "port",
            "Platform 1": "platform",
            "Platform 2": "platform",
        },
        "location_name": ["depot", "Port 1", "Port 2", "Platform 1", "Platform 2"],
        "locations_mapped": [0, 1, 1, 2, 3],  # Mapping locations to indices
        "MOORING_TIME_PORT": 120,
        "MOORING_TIME": 10,
        "ends": [0],
    }
    vessel_speed = 2

    result = time_matrix_with_virtual_locations(data, vessel_speed)

    expected = [
        [0, 0, 0, 5, 15],
        [30, 30, 30, 45, 55],
        [20, 20, 20, 35, 45],
        [25, 145, 145, 20, 43],
        [45, 165, 165, 53, 30],
    ]

    assert result == expected, f"Expected {expected}, but got {result}"


def test_sample(sample_solution):
    """Test that solution is getting created and main runs correctly for DO data."""
    assert sample_solution is not None


def test_sample_2():
    """Test that main does not fail on 'sample' data."""
    main(
        data_source="sample_2",
        update_expected_solution=False,
        save_solution=False,
        log_solution=False,
    )


def test_solution_data_sources(sample_solution, expected_solution_file):
    """Compare data source in newly generated solution with expected solution file."""
    expected_source = expected_solution_file["Data Source"].unique()
    current_source = sample_solution["Data Source"].unique()
    assert (
        current_source == expected_source
    ), f"Running wrong data source. Expected {expected_source}, Received: {current_source}"


def test_solution_total_distance(sample_solution, expected_solution_file):
    """Compare total distance in newly generated solution with expected solution file."""
    expected_distance = expected_solution_file.Distance.sum()
    current_distance = sample_solution.Distance.sum()
    assert (
        current_distance == expected_distance
    ), f"Total distance is different. Expected {expected_distance}, Received {current_distance}"


def test_solution_total_time(sample_solution, expected_solution_file):
    """Compare total time in newly generated solution with expected solution file."""
    expected_time = expected_solution_file.Time.sum()
    current_time = sample_solution.Time.sum()
    assert (
        current_time == expected_time
    ), f"Total time is different. Expected {expected_time}, Received {current_time}"


def test_solution(sample_solution, expected_solution_file):
    """Compare newly generated solution with expected solution file."""
    assert sample_solution.equals(expected_solution_file), "Files have differences."


if __name__ == "__main__":
    pytest.main([__file__])
