"""Functions for generating Distance and Time matrices."""

import geopandas as gpd
import numpy as np
import pandas as pd


def generate_distance_matrix(
    gdf: gpd.GeoDataFrame,
    projected_crs: int,
    depot_location_name: str,
    distance_units: int,
) -> list[list[int]]:
    """Sample distance matrix between real locations."""
    # depot is added in PICKUP_LOCATION_DEFAULT as a node with the same location

    gdf = gdf.copy()
    depot_row = gdf[gdf.name == depot_location_name]
    gdf = pd.concat([depot_row, gdf], ignore_index=True)
    gdf_projected = gdf.to_crs(epsg=projected_crs)

    # Calculate the distance matrix using the distance method
    return (
        gpd.GeoDataFrame(
            gdf_projected.geometry.apply(
                lambda x: gdf_projected.distance(x)
                / distance_units,  # convert to 100 m
            ).astype(int),
        )
        .to_numpy()
        .tolist()
    )  # when distances are converted to integers they are currently rounded down


def distance_matrix_with_virtual_locations(
    data: dict,
    distance_between_locations: list[list[int]],
) -> list[list[int]]:
    """Create a virtual distance matrix that includes all items and depot.

    It maps distances from real distance matrix to virtual locations for each pair of items.
    Virtual location is created for every loading and unloading action for each item.
    Currently it is assumed that depot is added at the original distance matrix step.
    """
    total_nodes = len(data["locations_mapped"])
    distance_matrix = [[0] * total_nodes for _ in range(total_nodes)]
    for i in range(total_nodes):
        item_location = data["locations_mapped"][i]
        for j in range(i + 1, total_nodes):
            other_item_location = data["locations_mapped"][j]
            distance = distance_between_locations[item_location][other_item_location]

            distance_matrix[i][j] = distance
            distance_matrix[j][i] = distance

    return distance_matrix


def time_matrix_with_virtual_locations(
    data: dict, vessel_speed: int | float
) -> list[list[int]]:
    """Create time matrix for virtual locations.

    Time is calculated between every pair of virtual nodes.
    Time is a sum of travel time, loading time, unloading time, mooring time.
    """
    total_nodes = len(data["distance_matrix"])
    time_matrix = [[0] * total_nodes for _ in range(total_nodes)]
    for i, row in enumerate(data["distance_matrix"]):
        for j, distance in enumerate(row):
            travel_time = distance / vessel_speed

            loading_unloading_time = data["loading_unloading_time"][i]

            # add different mooring time from platform to port
            if (
                (data["location_category_map"][data["location_name"][j]] == "port")
                & (data["location_category_map"][data["location_name"][i]] != "port")
                & (data["location_category_map"][data["location_name"][i]] != "depot")
                & (j not in data["ends"])
            ):
                # add a different penalty when vessel revisits port
                mooring_time = (
                    data["locations_mapped"][i] != data["locations_mapped"][j]
                ) * data["MOORING_TIME_PORT"]
            elif (
                (data["location_category_map"][data["location_name"][i]] == "depot")
                | (data["location_category_map"][data["location_name"][j]] == "depot")
                | (j in data["ends"])
            ):
                mooring_time = 0
            else:
                # time vessel takes moor from first platform and moor to second
                mooring_time = (
                    data["locations_mapped"][i] != data["locations_mapped"][j]
                ) * data["MOORING_TIME"]
            # round time up not to shorten the time. Integers are required for the optimizer.
            time_matrix[i][j] = int(
                np.ceil(travel_time + loading_unloading_time + mooring_time)
            )
    return time_matrix
