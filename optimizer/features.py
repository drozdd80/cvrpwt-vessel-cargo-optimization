"""Functions generating optimizer features and constrains."""

from typing import Callable

from ortools.constraint_solver import pywrapcp

###############
## callbacks ##
###############


def create_distance_callback(
    manager: pywrapcp.RoutingIndexManager, data: dict
) -> Callable:
    """Create a callback function to calculate the distance between two nodes."""

    def distance_callback(from_index: int, to_index: int) -> int:
        """Return the distance between the two nodes."""
        # Convert from routing variable Index to distance matrix NodeIndex.
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return data["distance_matrix"][from_node][to_node]

    return distance_callback


def create_time_callback(
    manager: pywrapcp.RoutingIndexManager, data: dict, vessel_index: int
) -> Callable:
    """Create a callback function to calculate the time between two nodes."""

    def time_callback(from_index: int, to_index: int) -> int:
        """Return the time between the two nodes."""
        # Convert from routing variable Index to time matrix NodeIndex.
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return data["time_matrix"][vessel_index][from_node][to_node]

    return time_callback


def create_demand_callback(
    manager: pywrapcp.RoutingIndexManager, data: dict
) -> Callable:
    """Create a callback function returning demand of the node."""

    def demand_callback(from_index: int) -> int:
        """Return the demand of the node."""
        # Convert from routing variable Index to demands NodeIndex.
        from_node = manager.IndexToNode(from_index)
        if from_node in data["starts"]:
            return 0  # start nodes have no demand
        return data["demands"][from_node]

    return demand_callback


################
## constrains ##
################


def pickups_and_deliveries(
    manager: pywrapcp.RoutingIndexManager,
    routing: pywrapcp.RoutingModel,
    distance_dimension: pywrapcp.RoutingDimension,
    data: dict,
) -> None:
    """Define pickup and delivery requests.

    See: https://developers.google.com/optimization/routing/pickup_delivery.
    """
    for request in data["pickups_deliveries"]:
        pickup_index = manager.NodeToIndex(request[0])
        delivery_index = manager.NodeToIndex(request[1])
        routing.AddPickupAndDelivery(pickup_index, delivery_index)
        routing.solver().Add(
            routing.VehicleVar(pickup_index) == routing.VehicleVar(delivery_index),
        )
        routing.solver().Add(
            distance_dimension.CumulVar(pickup_index)
            <= distance_dimension.CumulVar(delivery_index),
        )


def add_unavailability_times(
    data: dict,
    location_idx: int,
    index: int,
    time_dimension: pywrapcp.RoutingDimension,
) -> None:
    """Add unavailablity intervals to time windows."""
    if "unavailability_times" in data:
        # loop through unvailaility time windows
        for start_utw, end_utw in data["unavailability_times"][location_idx]:
            if start_utw is not None and end_utw is not None:
                # location is unavaibale from start of unvailaility interval - time for loading/unloading till the end
                time_dimension.CumulVar(index).RemoveInterval(
                    start_utw - data["loading_unloading_time"][location_idx], end_utw
                )
            # if only end of unavailability interval defined then assume that location is unavailable from the start
            elif start_utw is None and end_utw is not None:
                time_dimension.CumulVar(index).RemoveInterval(
                    data["TIME_WINDOW_START"], end_utw
                )
            # if only start of unavailability interval defined then assume that location is unavailable till the end
            elif start_utw is not None and end_utw is None:
                time_dimension.CumulVar(index).RemoveInterval(
                    start_utw - data["loading_unloading_time"][location_idx],
                    data["TIME_WINDOW_END"],
                )


def add_time_windows_constrains(
    manager: pywrapcp.RoutingIndexManager,
    routing: pywrapcp.RoutingModel,
    time_dimension: pywrapcp.RoutingDimension,
    data: dict,
) -> None:
    """See: https://developers.google.com/optimization/routing/vrptw."""
    # Add time window constraints for each location except depot.
    for location_idx, time_window in enumerate(data["time_windows"]):
        index = manager.NodeToIndex(location_idx)
        if index <= 0:
            continue

        time_dimension.CumulVar(index).SetRange(time_window[0], time_window[1])

        # add constrain for each virtual location when it cannot be visited
        add_unavailability_times(
            data,
            location_idx,
            index,
            time_dimension,
        )

    # Add time window constraints for each vehicle start node.
    for vehicle_id in range(data["num_vehicles"]):
        index = routing.Start(vehicle_id)
        start_node = data["starts"][vehicle_id]
        end_node = data["ends"][vehicle_id]

        time_dimension.CumulVar(index).SetRange(
            data["time_windows"][start_node][0],
            data["time_windows"][end_node][1],
        )

    # Instantiate route start and end times to produce feasible times.
    for i in range(data["num_vehicles"]):
        routing.AddVariableMinimizedByFinalizer(
            time_dimension.CumulVar(routing.Start(i))
        )
        routing.AddVariableMinimizedByFinalizer(time_dimension.CumulVar(routing.End(i)))


def location_visit_constrains(
    data: dict,
    time_dimension: pywrapcp.RoutingDimension,
    routing: pywrapcp.RoutingModel,
    manager: pywrapcp.RoutingIndexManager,
) -> None:
    """Add constrains on number of vessels visiting the same location at the same time.

    Also adds constrain on depot separately

    See: https://developers.google.com/optimization/routing/cvrptw_resources
    """
    solver = routing.solver()
    intervals = {}
    # loop through list of real locations
    for i, gr in enumerate(data["location_list"]):
        intervals[gr] = []
        # assigning intervals to ports and platforms. Used to add constrains on number of vessels in a location at a given time
        if gr != "depot":
            # loop through each virtual location in real location.
            for loc, value in enumerate(data["locations_mapped"]):
                if (
                    value == i
                ):  # TODO: loop through the correct subset of locatons instead if checking that the correct is selected
                    node_ind = manager.NodeToIndex(loc)
                    # exclude end nodes: https://github.com/google/or-tools/issues/1350

                    if node_ind >= 0:
                        interval = solver.FixedDurationIntervalVar(
                            time_dimension.CumulVar(node_ind),
                            data["loading_unloading_time"][loc],
                            str(gr),
                        )
                        intervals[gr].append(interval)

    for i, gr in enumerate(data["location_list"]):
        # add the same constrain for every virtual location in real location.
        loc_usage = [1 for _ in range(len(intervals[gr]))]
        if gr == "depot":
            pass
        elif data["location_category"][i] == "port":
            # constrain that sum of active visits of virt locations in intervals cannot exceed data["PLATFORM_CAPACITY"]
            solver.Add(
                solver.Cumulative(
                    intervals[gr], loc_usage, data["PORT_CAPACITY"], str(gr)
                ),
            )
        else:
            # constrain that sum of active visits of virt locations in intervals cannot exceed data["PLATFORM_CAPACITY"]
            solver.Add(
                solver.Cumulative(
                    intervals[gr], loc_usage, data["PLATFORM_CAPACITY"], str(gr)
                ),
            )
