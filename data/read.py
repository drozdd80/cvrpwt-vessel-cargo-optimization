"""Reading functions."""

import importlib
import types

import geopandas as gpd
import pandas as pd


def _read_source(directory: str) -> types.ModuleType:
    """Import read module from the directory."""
    return importlib.import_module(f".input.{directory}.read", package="data")


def demands(directory: str = "sample") -> pd.DataFrame:
    """Return demand dataframe from directory.

    Required columns:
    =================
    item_name: (str)
    pickup_location: (str)
        Location where item is picked up. It should match one of the locations from locations().name.
        Different case spelling and different special characters are allowed.
    delivery_location: (str)
        Location where item is delivered to. It should match one of the locations from locations().name.
        Different case spelling and different special characters are allowed.
    weight: (int|float|str) Weight of the item. Should be a positive numerical value

    Optional columns:
    ================
    lifts: (int)
        Optional column which shows number of lifts required to load/unload an item.
        Lifts are used to define loading/unloading time.
        If lifts are missing they are getting assigned based on weight using ONE_LIFT property from config.py.
        It calculates how many ONE_LIFTs is required to fit weight of the item.
    """
    read_source = _read_source(directory)
    return read_source.demands()


def locations(directory: str = "sample") -> gpd.GeoDataFrame:
    """Return locations from directory.

    Required columns:
    =================
    name: (str)
        name of the platform/port
    category: (str)
        port or anything else. Used to set different mooring times and different constrains on number of vessel at a location.
        Currently only checks for ports. Platforms are selected as everything else
    geometry: (Geopandas geometry)

    Optional columns:
    ================
    unavailability_times: list(tuple(str|datetime|None))
        lists of pairs of start and end of the unavailability time window. Requires ISO string format or timezone aware datetime or None

    """
    read_source = _read_source(directory)
    return read_source.locations()


def vessels(directory: str = "sample") -> pd.DataFrame:
    """Return vessels from directory.

    Required columns:
    =================
    vessel_name: (str)
        name of the vessel
    vessel_capacity: (int):
        weight in metric tons which vessels
    vessel_speed: (int|float)
        travel speed of the vessel in knots

    Optional columns:
    =================
    vessel_start_location: (str):
        starting location of the vessel. If not passed or invalid, uses default pickup location
    vessel_end_location: (str):
        end location of the vessel. If not passed or invalid, uses default pickup location
    """
    read_source = _read_source(directory)
    return read_source.vessels()
