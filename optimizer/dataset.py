"""Functions generating data model for the optimizer."""

import re
import types
from datetime import datetime

import geopandas as gpd
import pandas as pd

from data.read import demands, locations, vessels
from optimizer.matrices import (
    distance_matrix_with_virtual_locations,
    generate_distance_matrix,
    time_matrix_with_virtual_locations,
)


def replace_different_spelling(
    series_target: pd.Series, series_donor: pd.Series
) -> pd.Series:
    """Replace values from one series with another if their normalized versions are the same.

    Examples:
    ========
        >>> import pandas as pd
        >>> import re
        >>> series_target = pd.Series(["AB-1", "Ab:2", "aB 3", "ab4", "AB-5"])
        >>> series_donor = pd.Series(["AB 2", "AB 4", "AB 1", "AB 3"])
        >>> replace_different_spelling(series_target, series_donor)
        0    AB 1
        1    AB 2
        2    AB 3
        3    AB 4
        4    AB-5
        dtype: object

    """

    def normalize_string(s: str) -> str:
        """Normalize a string by making it lowercase and removing special characters."""
        return re.sub(r"\W+", "", s.lower())

    normalized_series_donor = series_donor.apply(normalize_string)

    # Create a mapping from normalized value to original value from series2
    mapping = dict(zip(normalized_series_donor, series_donor))

    # Replace values in series1 with corresponding non-normalized values from series2 based on normalized comparison
    return series_target.apply(lambda x: mapping.get(normalize_string(x), x))


def standardize_spelling_demand_data(
    demand_data: pd.DataFrame, locations: gpd.GeoDataFrame
) -> pd.DataFrame:
    """Replace destination location spellings with spellings from the location dataframe."""
    demand_data.delivery_location = replace_different_spelling(
        demand_data.delivery_location, locations.name
    )
    demand_data.pickup_location = replace_different_spelling(
        demand_data.pickup_location, locations.name
    )
    return demand_data


def loading_unloading_time(data: dict) -> list[int]:
    """Calculate time vessels spend at each node."""
    total_nodes = len(data["demands"])
    loading_unloading_times = []
    for i in range(total_nodes):
        # time multiplier for heavy items. Assume that  vehicle_unload_time is required to load 1 item if it is below ONE_LIFT.
        # Otherwise it takes as much more time as many groups of ONE_LIFT the weight can be split into
        lift_number_load = data["cargo_lifts"][i]
        lift_number_unload = data["cargo_lifts"][i]

        is_loading = data["action"][i] == "loading"  # load at the start of the leg
        is_unloading = (
            data["action"][i] == "unloading"
        )  # unload at the start of the leg

        loading_time = data["TIME_PER_ITEM_LOADED"] * lift_number_load * is_loading
        unloading_time = (
            data["TIME_PER_ITEM_UNLOADED"] * lift_number_unload * is_unloading
        )

        loading_unloading_times.append(loading_time + unloading_time)
    return loading_unloading_times


def time_difference_minutes(time1: str | datetime, time2: str | datetime) -> int:
    """Calculate time difference in minutes between two timestamps."""

    def convert_to_datetime(value: str | datetime) -> datetime:
        """Convert value to datetime if it's not already."""
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            # Try parsing ISO format strings
            return datetime.fromisoformat(value)
        msg = f"Unsupported type for datetime conversion: {type(value)}"
        raise ValueError(msg)

    dt1 = convert_to_datetime(time1)
    dt2 = convert_to_datetime(time2)
    return int((dt2 - dt1).total_seconds() / 60)


def time_from_start(time: str | None, data: dict) -> int:
    """Convert time to time since start in minutes."""
    if pd.notna(time):
        return time_difference_minutes(data["START_TIMESTAMP"], time)
    return None


def add_start_end_locations(
    data: dict, df_vessels: pd.DataFrame, df_locations: pd.DataFrame, kind: str
):
    """Fill data with values for start or end Nodes"""
    node_name = kind + "s"

    for _, row in df_vessels.iterrows():
        # check if vessel starting location is a location from df_locations. Otherwise use depot
        if row[f"vessel_{kind}_location"] in df_locations.name.to_numpy():
            data[node_name].append(len(data["location_name"]))
            data["location_name"].append(row[f"vessel_{kind}_location"])
            data["demands"].append(0)
            data["action"].append(None)
            data["cargoid"].append(None)
            data["item_name"].append(None)
            data["cargo_lifts"].append(0)
        else:
            raise ValueError(f"""
    {row[f'vessel_{kind}_location']} in vessel_{kind}_location is not in a list of valid locations. 
    Expected to see one one these values: 
    {df_locations.name.to_numpy()}
    """)


def add_start_locations(
    data: dict, df_vessels: pd.DataFrame, df_locations: pd.DataFrame
) -> None:
    """Fill data with values for start Nodes"""
    add_start_end_locations(data, df_vessels, df_locations, kind="start")


def add_end_locations(
    data: dict, df_vessels: pd.DataFrame, df_locations: pd.DataFrame
) -> None:
    """Fill data with values for end Nodes"""
    add_start_end_locations(data, df_vessels, df_locations, kind="end")


def create_data_model(data_source: str, config: types.ModuleType) -> dict:
    """Store the data for the problem."""
    data = {}

    # add config global variables to data dictionary
    data.update({k: v for k, v in vars(config).items() if not k.startswith("__")})

    # load data
    df_locations = locations(data_source)
    df_demands = (
        demands(data_source)
        .assign(weight=lambda x: x.weight.astype(int))
        .pipe(standardize_spelling_demand_data, df_locations)
    )
    df_vessels = vessels(data_source)

    data["num_vehicles"] = len(df_vessels)  # number of vessel used in optimization
    data["vessel_name"] = list(df_vessels["vessel_name"])
    data["vehicle_capacities"] = list(df_vessels["vessel_capacity"])
    data["vessel_speed"] = [
        s * (1852 / data["DISTANCE_UNITS_M"]) / 60 for s in df_vessels["vessel_speed"]
    ]  # kt in 100 m/min units

    data["is_depot"] = not (
        ("vessel_start_location" in df_vessels.columns)
        & ("vessel_end_location" in df_vessels.columns)
    )

    # Depot is the first node (index 0)
    data["demands"] = []
    data["pickups_deliveries"] = []
    data["location_name"] = []
    data["action"] = []  # None, loading or unloading
    data["cargoid"] = []
    data["item_name"] = []
    data["cargo_lifts"] = []

    if data["is_depot"]:
        # weights of the items. Negative weight means that item needs to be unloaded here, positive means loaded. Needed for capacity constrains
        data["demands"] = [0]
        data["pickups_deliveries"] = []
        data["location_name"] = ["depot"]
        data["action"] = [None]  # None, loading or unloading
        data["cargoid"] = [None]
        data["item_name"] = [None]
        data["cargo_lifts"] = [0]
        data["depot"] = 0

    data["starts"] = []
    data["ends"] = []

    # add starting locations
    if "vessel_start_location" in df_vessels.columns:
        add_start_locations(data, df_vessels, df_locations)
    else:
        data["starts"] = [data["depot"]] * data["num_vehicles"]

    # add end locations
    if "vessel_end_location" in df_vessels.columns:
        add_end_locations(data, df_vessels, df_locations)
    else:
        data["ends"] = [data["depot"]] * data["num_vehicles"]

    # add item based node properties
    for i, row in df_demands.iterrows():
        data["demands"].extend(
            [row["weight"], -row["weight"]]
        )  # adding item loading and unloading in order
        data["location_name"].extend([row["pickup_location"], row["delivery_location"]])
        data["action"].extend(["loading", "unloading"])
        data["cargoid"].extend([str(i), str(i)])
        data["item_name"].extend([row["item_name"], row["item_name"]])

        # when lifts are not assigned, use weight to add artificial lifts based on weight
        weight_lifts = int(
            (abs(row["weight"]) + data["ONE_LIFT"] - 1) // data["ONE_LIFT"]
        )
        if "lifts" in df_demands.columns:
            lifts = weight_lifts if pd.isna(row["lifts"]) else row["lifts"]
        else:
            lifts = weight_lifts

        data["cargo_lifts"].extend([int(lifts), int(lifts)])

    # pickups and deliveries
    for index in range(len(data["demands"])):
        if data["demands"][index] > 0:
            data["pickups_deliveries"].append([index, index + 1])

    # add depot only if it is used
    depot_list = ["depot"] if data["is_depot"] else []

    # saving list of locations in order and mapping them to their indices for matching with time and distance matrix data
    data["location_list"] = depot_list + df_locations["name"].tolist()
    data["location_category"] = depot_list + df_locations["category"].tolist()
    data["location_map"] = {v: i for i, v in enumerate(data["location_list"])}
    data["location_category_map"] = {
        v: data["location_category"][i] for i, v in enumerate(data["location_list"])
    }
    data["locations_mapped"] = [
        data["location_map"][loc] for loc in data["location_name"]
    ]

    total_nodes = len(data["demands"])  # Virtual nodes (items) + depot

    data["loading_unloading_time"] = loading_unloading_time(data)

    # distance matrix between real locations + depot
    distance_between_locations = generate_distance_matrix(
        df_locations,
        projected_crs=data["PROJECTED_CRS"],
        depot_location_name=data["PICKUP_LOCATION_DEFAULT"],
        distance_units=data["DISTANCE_UNITS_M"],
    )

    # distance matrix between nodes where for each item there are 2 nodes: loading node and unloading node. + start and end locations
    data["distance_matrix"] = distance_matrix_with_virtual_locations(
        data, distance_between_locations
    )

    # add time matrix for each vessel
    data["time_matrix"] = []
    for vessel_speed in data["vessel_speed"]:
        data["time_matrix"].append(
            time_matrix_with_virtual_locations(data, vessel_speed)
        )

    data["time_windows"] = [
        (data["TIME_WINDOW_START"] * 60, data["TIME_WINDOW_END"] * 60)
    ] * total_nodes  # All locations open for delivery anytime.
    if "unavailability_times" in df_locations.columns:
        data["unavailability_times"] = [[]]
        # unavailability_times as list of lists of tuples of times (start and end of unavailability interval) in minutes from START_TIMESTAMP
        unavailability_times_locations = (
            df_locations["unavailability_times"]
            .apply(
                lambda x: [
                    (time_from_start(ss[0], data), time_from_start(ss[1], data))
                    for ss in x
                ]
                if len(x) > 0
                else []
            )
            .to_numpy()
        )
        # map unavailability_times_locations to virtual locations
        data["unavailability_times"].extend(
            [
                unavailability_times_locations[loc - int(data["is_depot"])]
                for loc in data["locations_mapped"]
                if data["location_category"][loc] != "depot"
            ]
        )
    return data
