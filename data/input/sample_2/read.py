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
        "pickup_location": ["Port"] * 10,
        "delivery_location": ["one"] * 10,
        "weight": [50, 50, 50, 50, 50, 50, 50, 50, 50, 50],
    }

    return pd.DataFrame(data)


def locations() -> gpd.GeoDataFrame:
    """Sample data with location properties."""
    data = {
        "name": ["Port", "one"],
        "Latitude": [35.0, 34.1],
        "Longitude": [10.0, 10.1],
        "category": ["port", "platform"],
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
        "vessel_capacity": [200, 200, 200],
        "vessel_speed": [7.9, 8, 8.1],
    }
    return pd.DataFrame(data)
