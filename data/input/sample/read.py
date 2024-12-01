"""Reading functions for 'sample' data source."""

import geopandas as gpd
import pandas as pd

from data.input.sample import projections


def demands() -> pd.DataFrame:
    """Sample data with items, their weight, origin and destination."""
    data = {
        "item_name": [
            "Item 1",
            "Item 2",
            "Item 3",
            "Item 4",
            "Item 5",
            "Item 6",
            "Item 7",
            "Item 8",
            "Item 9",
            "Item 10",
        ],
        "pickup_location": ["Port"] * 9 + ["one"],
        "delivery_location": [
            "one",
            "one",
            "one",
            "one",
            "one",
            "two",
            "one",
            "one",
            "two",
            "three",
        ],
        "weight": [140, 130, 100, 1, 1, 1, 1, 1, 1, 122],
    }

    return pd.DataFrame(data)


def locations() -> gpd.GeoDataFrame:
    """Sample data with location properties."""
    data = {
        "name": ["Port", "one", "two", "three"],
        "Latitude": [35.0, 34.5, 34.8, 35.2],
        "Longitude": [10.0, 11.0, 9.5, 10.5],
        "category": ["port", "platform", "platform", "platform"],
        "unavailability_times": [
            [(None, "2022-01-01T06:00:00+04:00")],
            [("2022-01-01T12:00:00+04:00", "2022-01-01T13:00:00+04:00")],
            [
                ("2022-01-01T10:00:00+04:00", "2022-01-01T12:00:00+04:00"),
                ("2022-01-01T00:00:00+04:00", "2022-01-01T20:00:00+04:00"),
            ],
            [],
        ],
    }
    df = pd.DataFrame(data)

    # add geometries for the coordinates
    gdf: gpd.GeoDataFrame = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df["Longitude"], df["Latitude"]),
        crs=projections.gps,
    )  # type: ignore
    return gdf


def vessels() -> pd.DataFrame:
    """Sample data with vessel properties."""
    data = {
        "vessel_name": ["Vessel1", "Vessel2", "Vessel3"],
        "vessel_capacity": [200, 250, 200],
        "vessel_start_location": ["Port", "Port", "Port"],
        "vessel_end_location": ["Port", "Port", "Port"],
        "vessel_speed": [7.9, 8, 8.1],
    }
    return pd.DataFrame(data)
