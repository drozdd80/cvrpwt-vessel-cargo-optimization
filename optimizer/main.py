"""Optimizer for Capacitated Vehicle Routing Problem with Time Windows (CVRPWT) using ortools.

Locations are split into separate vitrtual locations for each item pickup and delivery.
Additionally adding constrain that 2 vessel cannot be at the same location at the same time.

See:
    - https://developers.google.com/optimization/routing/vrp
"""

import importlib
import os

from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from optimizer import config
from optimizer.dataset import create_data_model
from optimizer.features import (
    add_time_windows_constrains,
    create_demand_callback,
    create_distance_callback,
    create_time_callback,
    location_visit_constrains,
    pickups_and_deliveries,
)
from optimizer.output import generate_output

_path = os.path.dirname(__file__)

# ANSI escape codes for yellow
YELLOW = "\033[33m"
RESET = "\033[0m"


def main(
    data_source: str = "sample",
    solution_filename: str = "solution.csv",
    save_solution: bool = True,
    log_solution: bool = True,
    update_expected_solution: bool = False,
) -> None:
    """Solve CVRPTW.

    Parameters
    ----------
    data_source: str
        name of a subfolder in data with reading modules for a specific set of data

    solution_filename: str
        solution file name saved in data/output/

    save_solution: bool
        Whether the solution.csv file and logs are generated

    log_solution: bool
        Whether the solution files are logged in output/logs

    update_expected_solution: bool
        Whether the validation/expected_solution.csv file is updated

    """
    # update config with values from config for a specific data source
    try:
        module = importlib.import_module(f".input.{data_source}.config", package="data")
        config.__dict__.update(module.__dict__)
    except ModuleNotFoundError:
        print(
            f"{YELLOW}data.input.{data_source}.config module does not exist. Using optimizer.config.py without setting changes specific to {data_source}{RESET}"
        )

    # Instantiate the data problem.
    data = create_data_model(data_source, config)

    # Create the routing index manager.
    manager = pywrapcp.RoutingIndexManager(
        len(data["distance_matrix"]),
        data["num_vehicles"],
        data["starts"],
        data["ends"],
    )

    # Create Routing Model.
    routing = pywrapcp.RoutingModel(manager)
    # Create and register a transit callback.
    distance_callback_instance = create_distance_callback(manager, data)

    distance_callback_index = routing.RegisterTransitCallback(
        distance_callback_instance
    )

    # Add Distance constraint.
    dimension_name = "Distance"
    routing.AddDimension(
        distance_callback_index,
        0,  # no slack
        data["MAX_DISTANCE_PER_VEHICLE"],  # vehicle maximum travel distance
        True,  # start cumul to zero
        dimension_name,
    )
    distance_dimension = routing.GetDimensionOrDie(dimension_name)

    # define time callback for each of the vessels
    transit_callback_indices = []
    for vessel_index, _ in enumerate(data["vessel_name"]):
        time_callback_instance = create_time_callback(manager, data, vessel_index)
        transit_callback_index = routing.RegisterTransitCallback(time_callback_instance)
        transit_callback_indices.append(transit_callback_index)

    # Define cost of each arc for each vessel.
    for vessel_index, _ in enumerate(data["vessel_name"]):
        routing.SetArcCostEvaluatorOfVehicle(
            transit_callback_indices[vessel_index], vessel_index
        )

    # Add Time Windows constraint.
    time = "Time"
    routing.AddDimensionWithVehicleTransits(
        transit_callback_indices,
        data["MAX_WAITING_TIME"],  # allow waiting time
        data["MAX_WAITING_TIME_PER_VEHICLE"],  # maximum time per vehicle
        False,  # Don't force start cumul to zero.
        time,
    )
    time_dimension = routing.GetDimensionOrDie(time)

    demand_callback_instance = create_demand_callback(manager, data)

    demand_callback_index = routing.RegisterUnaryTransitCallback(
        demand_callback_instance
    )

    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index,
        0,  # null capacity slack
        data["vehicle_capacities"],  # vehicle maximum capacities
        True,  # start cumul to zero
        "Capacity",
    )

    add_time_windows_constrains(manager, routing, time_dimension, data)

    # add constrains on depot and location visits by multiple vessels at the same time
    location_visit_constrains(data, time_dimension, routing, manager)

    pickups_and_deliveries(manager, routing, distance_dimension, data)

    # Allow to drop nodes.
    for node in range(1, len(data["distance_matrix"])):
        index = manager.NodeToIndex(node)
        # exclude end nodes: https://github.com/google/or-tools/issues/1350
        if index >= 0:
            routing.AddDisjunction([index], config.PENALTY)

    # Setting first solution heuristic.
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.time_limit.seconds = data["SOLUTION_TIME_LIMIT_SECONDS"]
    search_parameters.solution_limit = data["SOLUTION_LIMIT"]
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.AUTOMATIC
    )  # pylint: disable=no-member
    search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    search_parameters.log_search = data["LOG_SEARCH"]

    # Solve the problem.
    solution = routing.SolveWithParameters(search_parameters)

    return generate_output(
        data=data,
        manager=manager,
        routing=routing,
        solution=solution,
        data_source=data_source,
        save_solution=save_solution,
        log_solution=log_solution,
        update_expected_solution=update_expected_solution,
        solution_filename=solution_filename,
    )


if __name__ == "__main__":
    main()
