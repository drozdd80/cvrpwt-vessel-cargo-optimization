"""Functions generating output of the optimizer."""

import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from ortools.constraint_solver import pywrapcp

from optimizer.utils import get_git_commit_info

_path = os.path.dirname(__file__)


def print_solution(
    data: dict,
    manager: pywrapcp.RoutingIndexManager,
    routing: pywrapcp.RoutingModel,
    solution: pywrapcp.Assignment,
) -> None:
    """Prints solution to console, including vehicle loads."""
    print(f"Objective: {solution.ObjectiveValue()}")

    time_dimension = routing.GetDimensionOrDie("Time")
    distance_dimension = routing.GetDimensionOrDie("Distance")
    capacity_dimension = routing.GetDimensionOrDie(
        "Capacity"
    )  # Get the Capacity dimension
    total_time = 0
    total_distance = 0
    dropped_nodes = "Dropped nodes:"

    for node in range(routing.Size()):
        if routing.IsStart(node) or routing.IsEnd(node):
            continue
        if solution.Value(routing.NextVar(node)) == node:
            dropped_nodes += f" {manager.IndexToNode(node)}"

    print(dropped_nodes)

    for vehicle_id in range(data["num_vehicles"]):
        index = routing.Start(vehicle_id)
        vesse_name = data["vessel_name"][vehicle_id]
        plan_output = f"Route for {vesse_name}:\n"

        while not routing.IsEnd(index):
            time_var = time_dimension.CumulVar(index)
            load_var = capacity_dimension.CumulVar(
                index
            )  # Get the cumulative load variable
            distance_var = distance_dimension.CumulVar(index)

            plan_output += (
                f"{manager.IndexToNode(index)}"
                f" Time({solution.Min(time_var)}, {solution.Max(time_var)})"
                f" Load({solution.Value(load_var)})"  # Add current vehicle load
                " -> "
            )

            index = solution.Value(routing.NextVar(index))

        time_var = time_dimension.CumulVar(index)
        plan_output += (
            f"{manager.IndexToNode(index)}"
            f" Time({solution.Min(time_var)}, {solution.Max(time_var)})\n"
        )
        plan_output += f"Time of the route: {solution.Min(time_var)}min\n"

        distance_var = distance_dimension.CumulVar(index)
        plan_output += f"Distance of the route: {solution.Min(distance_var)*(data['DISTANCE_UNITS_M']/1000)} km"
        print(plan_output)

        total_time += solution.Min(time_var)
        total_distance += solution.Min(distance_var) * (data["DISTANCE_UNITS_M"] / 1000)

    print(f"Total time of all routes: {total_time}min")
    print(f"Total distance of all routes: {total_distance} km")


def create_solution_dataframe(
    data: dict,
    manager: pywrapcp.RoutingIndexManager,
    routing: pywrapcp.RoutingModel,
    assignment: pywrapcp.Assignment,
    data_source: str,
) -> pd.DataFrame:
    """Create a leg based solution dataframe."""
    # Initialize a list to store data for DataFrame
    all_legs = []

    for vehicle_id in range(data["num_vehicles"]):
        index = routing.Start(vehicle_id)
        previous_index = None
        leg_number = 0

        while not routing.IsEnd(index):
            node_index = manager.IndexToNode(index)
            if previous_index is not None:
                prev_node_index = manager.IndexToNode(previous_index)

                # Vehicle details
                vehicle_name = data["vessel_name"][vehicle_id]

                # Ports and quantities
                loading_port = data["location_name"][prev_node_index]  # leg_start
                discharging_port = data["location_name"][node_index]  # leg_end
                quantity_loaded = max(0, data["demands"][prev_node_index])
                quantity_unloaded = -min(0, data["demands"][prev_node_index])

                loaded = bool(data["action"][prev_node_index] == "loading")
                unloaded = bool(data["action"][prev_node_index] == "unloading")

                # Retrieve cargo and item details
                unloaded_cargo_id = (
                    data["cargoid"][prev_node_index] if unloaded else None
                )
                loaded_cargo_id = data["cargoid"][prev_node_index] if loaded else None

                unloaded_item_name = (
                    data["item_name"][prev_node_index] if unloaded else None
                )
                loaded_item_name = (
                    data["item_name"][prev_node_index] if loaded else None
                )

                # Time dimensions
                time_dimension = routing.GetDimensionOrDie("Time")
                arrival_time = assignment.Value(time_dimension.CumulVar(previous_index))
                departure_time = assignment.Value(time_dimension.CumulVar(index))

                # Time spent
                time_spent = departure_time - arrival_time  # Time in minutes

                # Distance calculation
                distance_dimension = routing.GetDimensionOrDie("Distance")
                previous_distance = assignment.Value(
                    distance_dimension.CumulVar(previous_index)
                )
                current_distance = assignment.Value(distance_dimension.CumulVar(index))
                distance_travelled = (
                    (current_distance - previous_distance)
                    * data["DISTANCE_UNITS_M"]
                    / 1000
                )

                # Cargo lifts
                loading_cargo_lifts = (
                    data["cargo_lifts"][prev_node_index] if loaded else None
                )
                unloading_cargo_lifts = (
                    data["cargo_lifts"][prev_node_index] if unloaded else None
                )

                # pickup deliveries
                node_pickup_delivery = [
                    [i, j]
                    for i, j in data["pickups_deliveries"]
                    if (prev_node_index == i) | (prev_node_index == j)
                ]
                if loaded_item_name or unloaded_item_name:
                    pickup_location = data["location_name"][node_pickup_delivery[0][0]]
                    delivery_location = data["location_name"][
                        node_pickup_delivery[0][1]
                    ]
                else:
                    pickup_location = None
                    delivery_location = None

                action = data["action"][prev_node_index]

                # Create a dictionary for the leg and append to the list
                leg_data = {
                    "Current Node Index": prev_node_index,
                    "Next Node Index": node_index,
                    "Action Start Node": action,
                    "Loaded Cargo id": loaded_cargo_id,
                    "Unloaded Cargo Id": unloaded_cargo_id,
                    "Loaded Item Name": loaded_item_name,
                    "Unloaded Item Name": unloaded_item_name,
                    "Vessel": vehicle_name,
                    "Leg": leg_number,
                    "Current Node Location": loading_port,
                    "Next Node Location": discharging_port,
                    "Weight Loaded": quantity_loaded,
                    "Weight Unloaded": quantity_unloaded,
                    "Current Node Time": arrival_time,
                    "Next Node Time": departure_time,
                    "Pickup Location": pickup_location,
                    "Delivery Location": delivery_location,
                    "Loaded Cargo Lifts": loading_cargo_lifts,
                    "Unloaded Cargo Lifts": unloading_cargo_lifts,
                    "Distance": distance_travelled,
                    "Time": time_spent,
                    "Data Source": data_source,
                }
                all_legs.append(leg_data)

                leg_number += 1

            previous_index = index
            index = assignment.Value(routing.NextVar(index))

        # Process the final leg back to the depot
        if previous_index is not None:
            end_index = routing.End(vehicle_id)
            node_index = manager.IndexToNode(end_index)
            prev_node_index = manager.IndexToNode(previous_index)

            # Vehicle details
            vehicle_name = data["vessel_name"][vehicle_id]

            # Ports and quantities
            loading_port = data["location_name"][prev_node_index]  # leg_start
            discharging_port = data["location_name"][node_index]  # leg_end
            quantity_loaded = max(0, data["demands"][prev_node_index])
            quantity_unloaded = -min(0, data["demands"][prev_node_index])

            loaded = bool(data["action"][prev_node_index] == "loading")
            unloaded = bool(data["action"][prev_node_index] == "unloading")

            # Retrieve cargo and item details
            unloaded_cargo_id = data["cargoid"][prev_node_index] if unloaded else None
            loaded_cargo_id = data["cargoid"][prev_node_index] if loaded else None

            unloaded_item_name = (
                data["item_name"][prev_node_index] if unloaded else None
            )
            loaded_item_name = data["item_name"][prev_node_index] if loaded else None

            # Time dimensions
            time_dimension = routing.GetDimensionOrDie("Time")
            arrival_time = assignment.Value(time_dimension.CumulVar(previous_index))
            departure_time = assignment.Value(time_dimension.CumulVar(index))

            # Distance calculation
            distance_dimension = routing.GetDimensionOrDie("Distance")
            previous_distance = assignment.Value(
                distance_dimension.CumulVar(previous_index)
            )
            current_distance = assignment.Value(distance_dimension.CumulVar(index))

            time_spent = 0
            distance_travelled = 0

            route_cost = routing.GetArcCostForVehicle(previous_index, index, vehicle_id)

            # only count time and distance if the route was part of the solution
            if route_cost:
                time_spent = departure_time - arrival_time  # Time in minutes
                distance_travelled = (
                    (current_distance - previous_distance)
                    * data["DISTANCE_UNITS_M"]
                    / 1000
                )  # distance in km

            # Cargo lifts
            loading_cargo_lifts = (
                data["cargo_lifts"][prev_node_index] if loaded else None
            )
            unloading_cargo_lifts = (
                data["cargo_lifts"][prev_node_index] if unloaded else None
            )

            # pickup deliveries
            node_pickup_delivery = [
                [i, j]
                for i, j in data["pickups_deliveries"]
                if (prev_node_index == i) | (prev_node_index == j)
            ]
            if loaded_item_name or unloaded_item_name:
                pickup_location = data["location_name"][node_pickup_delivery[0][0]]
                delivery_location = data["location_name"][node_pickup_delivery[0][1]]
            else:
                pickup_location = None
                delivery_location = None

            action = data["action"][prev_node_index]

            # Create a dictionary for the final leg and append to the list
            leg_data = {
                "Current Node Index": prev_node_index,
                "Next Node Index": node_index,
                "Action Start Node": action,
                "Loaded Cargo id": loaded_cargo_id,
                "Unloaded Cargo Id": unloaded_cargo_id,
                "Loaded Item Name": loaded_item_name,
                "Unloaded Item Name": unloaded_item_name,
                "Vessel": vehicle_name,
                "Leg": leg_number,
                "Current Node Location": loading_port,
                "Next Node Location": discharging_port,
                "Weight Loaded": quantity_loaded,
                "Weight Unloaded": quantity_unloaded,
                "Current Node Time": arrival_time,
                "Next Node Time": departure_time,
                "Pickup Location": pickup_location,
                "Delivery Location": delivery_location,
                "Loaded Cargo Lifts": loading_cargo_lifts,
                "Unloaded Cargo Lifts": unloading_cargo_lifts,
                "Distance": distance_travelled,
                "Time": time_spent,
                "Data Source": data_source,
            }
            all_legs.append(leg_data)

    # Convert list of dicts into a DataFrame
    return pd.DataFrame(all_legs)


def generate_output(
    data: dict,
    manager: pywrapcp.RoutingIndexManager,
    routing: pywrapcp.RoutingModel,
    solution: pywrapcp.Assignment,
    data_source: str,
    save_solution: bool,
    log_solution: bool,
    update_expected_solution: bool,
    solution_filename: str,
) -> None:
    """Generate output of the optimizer.

    1. Print routes to console
    2. Update solution.csv if save_solution is true
    3. Add solution file to logs if save_solution is true
    4. Update validation/expected_solution.csv file if update_expected_solution is true
    """
    if solution:
        # Print solution on console.
        print_solution(data, manager, routing, solution)

        df_solution = create_solution_dataframe(
            data, manager, routing, solution, data_source
        )
        output_dir = _path + "/../data/output"

        if save_solution:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            df_solution.to_csv(output_dir + "/" + solution_filename, index=False)

        if log_solution:
            # save second solution file to logs
            # save logs into subfolders based on commit.
            # To be able to sort commits in order start name of the subfolder with commit timestamp
            commit_hash, commit_date = get_git_commit_info()
            run_time = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")

            output_logs_dir = (
                _path + f"/../data/output/logs/{commit_date}_{commit_hash}"
            )
            filename_logs = f"solution_{run_time}.csv"
            Path(output_logs_dir, exist_ok=True).mkdir(parents=True, exist_ok=True)
            df_solution.to_csv(output_logs_dir + "/" + filename_logs, index=False)

        if update_expected_solution:
            print("Updating expected solution")
            expected_solution_dir = output_dir + "/validation/"
            validation_filename = "expected_solution.csv"
            Path(expected_solution_dir).mkdir(parents=True, exist_ok=True)
            df_solution.to_csv(expected_solution_dir + validation_filename, index=False)

        return df_solution
    else:
        print("No solution found !")
        return None
