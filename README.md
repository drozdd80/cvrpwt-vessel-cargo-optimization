# Introduction 
Creating an optimization solution for Capacitated Vehicle Routing Problem with Time Windows (CVRPWT) using ortools.

Model delivers list of items from provided locations to designated platforms using available vessels traveling in straight lines. Vessels can start at different locations and deliver items within the provided time windows. Only 1 vessel is allowed to stay at a platform at a time. Each vessel has her weight capacity constrain which cannot be exceeded. Optimizer searches for the most efficient solution by total voyage time across all vessels combined including travel, loading/unloading and mooring within the provided search time.

# How to use:

## How to run the optimizer
1. Create conda environment `conda env create -f env.yaml`
2. Activate conda environment `conda activate optimizer`
3. Run `python main.py -d data_source`
    - data_source: name of a subfolder in data with reading modules for a specific set of data. Use 'sample' for sample data example. 
    - `python main.py` will run optimizer of the default set of data. Currently it is 'sample'

4. Solution file is getting saved to `data/output/solution.csv`

## How to add a new data source

1. Create a new folder `data/input/<new_data_source>/`
2. Add read.py in `data/input/<new_data_source>/`. It should contain 3 functions:
    1. locations()
    2. demands()
    3. vessels()

Each function returns DataFrame or GeoDataFrame with required and optional columns. Check **Reference** for the list of columns and their descriptions

3. Optionally add config.py in `data/input/<new_data_source>/config.py`. Populate it with modified properties from `optimizer/config.py` which need to be changed for the new_data_source optimization. Particularly PICKUP_LOCATION_DEFAULT need to match name of a location from locations().

4. Add empty file `data/input/<new_data_source>/__init__.py`. Needed for tests. See https://github.com/pytest-dev/pytest/issues/702

## How to run optimizer on a different data source

1. Verify that properties in `data/input/<new_data_source>/config.py` are set correctly. Values in `optimizer/config.py` are getting overwritten by `data/<new_data_source>/config.py` in they overlap.
2. Run `python main.py -d new_data_source`. 
    - `-d new_data_source` (optional): name of a subfolder in data with reading modules for a specific set of data. Use 'sample' for sample data. If `-d` is not passed, optimizer will run DEFAULT_DATA_SOURCE data source specified in main.py

## How to test

1. Compare current solution with previous commit
Run `bash tests/solution_verification.sh -r -i -d <data_source>` to compare solution.csv with the solution file from previous commit.
Uses solution files saved in `data/output/logs`. Compares current solution file with last file from second to last commit (assumes that it was done right before committing).

`bash tests/solution_verification.sh -b` to compare solution.csv with current commit temporarily stashing all the files

optional arguments:
- `-r`: run optimizer before comparing the outputs
- `-b`: run optimizer with files stashed, unstashed, compare the outputs.
- `-i`: if there is a difference between solution files, ipython is getting opened with dataframes of both files and their comparison loaded
- `-d <data_source>`: passes name of the <data_source> subfolder to the optimizer

2. Run optimizer test on sample data and validation solution.csv with expected_solution.csv
Run `python -m pytest tests/test.py`

3. add pre-commit hook `.pre-commit-config.yaml` by running `pre-commit install`. It will ruff formatter and tests before every commit and abord if something fails.

To manually run pre-commit before committing run `pre-commit run --all-files`

See: https://pre-commit.com/#usage

## How to update expected_solution.csv
Run `python main.py -d <data_source> -u`

# Reference:

## python main.py
| Argument                          | Definition
|-----------------------------------|------------------------------------
| -d, --data_source <dir_name>      | specify data source directory name
| -s, --no_save_solution            | if passed, solution is not saved to output/solution.csv
| -l, --no_log_solution             | if passed, solution is not saved to output/logs/
| -u, --update_expected_solution    | update(rewrite) expected_solution.csv with current solution. Use it if solution.csv is supposed to change

## config.py
|Property                       | Definition
|-------------------------------|------------------
|SOLUTION_TIME_LIMIT_SECONDS    | Limit in seconds to the time spent : in the search.
|SOLUTION_LIMIT                 | Limit to the number of solutions generated during the search.
|DISTANCE_UNITS_M               | Units in meters to which distance is rounded to and converted (Eases calculations when DISTANCE_UNITS_M is set to a bigger value)
|MAX_DISTANCE_PER_VEHICLE       | vehicle maximum travel distance in DISTANCE_UNITS_M units (required when adding a distance dimension)
|MAX_WAITING_TIME               | allow waiting time (required when adding a time dimension)
|MAX_WAITING_TIME_PER_VEHICLE   | maximum time per vehicle (required when adding a time dimension)
|PENALTY                        | Penalty for dropping nodes
|LOG_SEARCH                     | Enable logging of the solution searching process
|PICKUP_LOCATION_DEFAULT        | name of the location where depot is set. All the vessels start from there
|ONE_LIFT                       | How many KG stands for 1 lift. Used when lifts are not defined
|TIME_PER_ITEM_LOADED           | Time in minutes to load 1 lift 
|TIME_PER_ITEM_UNLOADED         | Time in minutes to unload 1 lift 
|MOORING_TIME                   | Extra time it takes for a vessel to unmoor from one location and moor to another location (except ports and depot)
|MOORING_TIME_PORT              | Extra time it takes for a vessel to unmoor from one location and moor to port. Added separately to add penalty for vessel revisiting port
|PLATFORM_CAPACITY              | Number of vessels platforms can handle at the same time
|PORT_CAPACITY                  | Number of vessels ports can handle at the same time
|PROJECTED_CRS                  | Projected CRS for calculating distances. Example: https://epsg.io/3857
|GPS_CRS                        | Default GPS CRS (currently not used)
|START_TIMESTAMP                | Timestamp of the optimization start in ISO string format with specified timezone
|TIME_WINDOW_START              | Time of routing start for all vessels (including loading/unloading items)
|TIME_WINDOW_END                | Cut off time before which all loading/unloading and traveling is completed (except traveling from the last platform to depot)

## read.py

required functions in data/input/<DATA_SOURCE>/read.py

### 1. locations()

Required columns:

| column name   | type                  | description
|---------------|-----------------------|-------------
| name          | str                   | name of the platform/port
| category      | str                   | port or anything else. Used to set different mooring times and different constrains on number of vessel at a location. Currently only checks for ports. Platforms are selected as everything else
| geometry      | Geopandas geometry    | geometry of the location build based on the location coordinates

Optional columns:

| column name           | type                              | description
|-----------------------|-----------------------------------|-------------
| unavailability_times  | list(tuple(str datetime None))    | lists of pairs of start and end of the unavailability time windows. Requires ISO string format or timezone aware datetime or None

### 2. demands()

Required columns:

| column name       | type                  | description
|-------------------|-----------------------|-------------
| item_name         | str                   | 
| pickup_location   | str                   | Location where item is picked up. It should match one of the locations from locations().name. Different case spelling and different special characters are allowed.
| delivery_location | str                   | Location where item is delivered to. It should match one of the locations from locations().name. Different case spelling and different special characters are allowed.
| weight            | int float str         | Weight of the item. Should be a positive numerical value
    

Optional columns:

| column name       | type                  | description
|-------------------|-----------------------|-------------
| lifts             | int                   | Optional column which shows number of lifts required to load/unload an item. Lifts are used to define loading/unloading time. If lifts are missing they are getting assigned based on weight using ONE_LIFT property from config.py.  It calculates how many ONE_LIFTs is required to fit weight of the item.        
    

### 3. vessels()

Required columns:

| column name       | type                  | description
|-------------------|-----------------------|-------------
| vessel_name       | str                   | name of the vessel
| vessel_capacity   | int                   | weight in metric tons which vessels 
| vessel_speed      | int float             | travel speed of the vessel in knots

Optional columns:

| column name           | type                  | description
|-----------------------|-----------------------|-------------
| vessel_start_location | str                   | starting location of the vessel. If not passed or invalid, uses default pickup location
| vessel_end_location   | str                   | end location of the vessel. If not passed or invalid, uses default pickup location

## Output

### solution.csv

| column name           | type                  | description
|-----------------------|-----------------------|----------------------------
| Start Node Index      | int                   | Index of the current node
| End Node Index        | int                   | Index of the next node
| Action Start Node     | str None              | Action (loading or unloading) at current node. Only 1 action can happen at a node
| Loaded Cargo id       | int None              | Index of the unloaded item from the demand data 
| Unloaded Cargo Id     | int None              | Index of the loaded item from the demand data
| Loaded Item Name      | str None              | 
| Unloaded Item Name    | str None              |
| Vessel                | str                   | Name of the vessel
| Leg                   | int                   | Leg number for the vessel route. Order of the particular route
| Leg Start Location    | str                   | Current node location
| Leg End Location      | str                   | Next node location
| Weight Loaded         | int                   |
| Weight Unloaded       | int                   | 
| Leg Start Time        | int                   | Arrival time to the current node
| Leg End Time          | int                   | Arrival time to the next node
| Pickup Location       | str None              | Pickup location for the item which is processed at current node
| Delivery Location     | str None              | Delivery location for the item which is processed at current node
| Loaded Cargo Lifts    | int None              | Number of lifts loaded at current node
| Unloaded Cargo Lifts  | int None              | Number of lifts unloaded at current node
| Distance              | int                   | Distance between current node and the next node
| Time                  | int                   | Time between arrival to the current node and arrival to the next node. Loading, unloading at the current node and mooring from current node and to the next node have time included into this value.
| Data Source           | str                   | Name of a data subfolder with data used for this optimizer run

# Assumptions
- pickup and delivery locations in demands() is a subset of locations in locations().name. Slight spelling difference such as different cases and additional or different special characters in demands() and locations() are allowed 
- Distances are calculated in integers of DISTANCE_UNITS_M units
- Depot is added to distance matrix at a node with the same coordinates as PICKUP_LOCATION_DEFAULT
- All numerical data passed into ortools uses integer type 
- All the vessels in vessels().name are available for a voyage
- Vessels start from vessels().starting_location if value is passed and matches one of the locations in locations().name, otherwise uses PICKUP_LOCATION_DEFAULT location
- Vessel speed is the same throughout the voyage.
- Routes are straight lines on a provided projection (default projection: https://epsg.io/3857)
- For each item 2 virtual nodes are created: Loading node, Unloading node
- loading and unloading actions are added to optimizer as additional time between nodes in time matrix (assigned to the starting node if a leg)
- All the voyage can be split into travel time, loading time, unloading time, mooring time
- vessel waiting time is allowed when platform is unavailable
- vessel MOORING_TIME is added when vessel travels between node of one real location to a node of a different location
- When vessel travels to port from something except depot, it uses a different MOORING_TIME_PORT which is bigger than MOORING_TIME. It is also needed as a penalty to force optimizer to use different vessels instead of reusing the same vessel for all the deliveries.
- loading/unloading times of all the items for a single lift are the same for any item (There can be a difference between loading time and unloading time)
- loading/unloading time of an item depends linearly on the number of lifts
- If lifts are not present, weight is used instead where ONE_LIFT value is used to select which weight stands for 1 lift.
- Vessels cannot carry more weight than their capacity. This is the only vessel capacity constrain
- There cannot be more than PORT_CAPACITY vessels in port at the same time
- There cannot be more than PLATFORM_CAPACITY vessels on platform at the same time
- Route of every vessel starts at starting location or depot and ends at end location or depot
- Vessels can start traveling or loading/unloading at TIME_WINDOW_START
- Last item needs to arrive at the last location (except depot) before TIME_WINDOW_END (item loading/unloading at the last location is not accounted for)
- All the actions and traveling is allowed at all times between TIME_WINDOW_START and TIME_WINDOW_END (except traveling back to depot and loading/unloading the last location)
- Vessels cannot arrive or load/unload cargo during platform/port unavailability time windows
- Vessels do not have unavailability time windows
- Vessels visit the last location before TIME_WINDOW_END but they can travel to depot or end location from the last platform exceeding TIME_WINDOW_END time
- Time is used as optimization cost. Solution is optimized by time.
- If solution is not getting found, optimizer drops some nodes.
- First solution strategy is defined automatically
- After the first solution is found ortools run guided local search either for SOLUTION_TIME_LIMIT_SECONDS or until SOLUTION_LIMIT solutions is generated
- Generated solution.csv file shows legs between 2 nodes. 1 row is 1 leg.

# Explanation:

## Data sources and preprocessing

First step is create a data model. We use 3 main inputs: 
1. locations()
GeoDataFrame of all platforms and ports with their names, categories and geometries.


2. demands()
Pandas Dataframe of items to be delivered. 


3. vessels()
Pandas dataframe of vessels and their parameters

Additional inputs are defined in config.py. 
There is a package config which have default properties of optimizer and location of data source by using same of the subfolder in data.

properties specific to a particular set of data can be defined in `data/input/<dir_name>/config.py`


## Data model
All the values we use are saved in a dictionary `data`. Some of them are passed into optimizer, others are used for calculation purposes. It is just a way to store all the required variables.

Due to constrain of the ortools only 1 vessel can visit any location and can do it only once. So regular approach does not allow to solve the packaging problem. To overcome it we create 2 virtual nodes for each item: virtual node for pickup location and virtual node for delivery location. Additionally ortools require have a separate depot for the vessels for vessels to start and end their routes (or these could be different virtual starting locations). So for n items we create 2n+1 nodes. We added staring locations, so vessels start in different start location virtual nodes (v additional nodes where v is number of vessels). 

Nodes are generated in a set order. We start with vessel starting and end locations or depot if start/end location is not defined and for every item first we add node for loading the item, then node for unloading it. 

Demands is a directional variable. It is used to add weight during an item pickup and decrease after it is unloaded

**Important note:** Numerical data passed into ortools MUST be integers. demands, distances, etc. If floats passed the module which uses these values will return 0 values no matter which values are passed and the output will be scuffed. There are no errors raised. Difficult to debug.

## Time and Distance Matrices

Matrices are generated in a 2 step process.
### 1. Generate distance matrix between real locations (with an addition of depot as a temporary solution). 
Use geopandas for that. Distances are calculated as straight lines between locations on a given projection. They are calculated in DISTANCE_UNITS_M units (100m by default) and converted to integers (ortools work with integers). Bigger integer values are more complicated to calculate a result.

### 2. Generate distance matrix between virtual nodes 
We call a virtual node a node of item delivery or item pickup. One of 2n+v+1 (loading + unloading of each item, starting locations for each vessel and depot) nodes. Using a mapping between virtual nodes and real locations we map distances between real locations calculated in previous step to pairs of corresponding virtual locations.

### 3. Generate time matrices for each of the vessels. 
Time depends on speed, so matrices are different for different vessels.

Time is generated based on distance. It has 4 parts:
- travel time: distance divided by vessel speed
- looading/unloading time: time it takes to load or unload items. It is node based and does not depend on the destination node
- mooring time: Additional time spent when mooring/unmooring to a different location. Also serves as a penalty for the optimizer to avoid visiting the same location twice without a need for that. Same for port. Without increased mooring time for ports (2 hours) all the rooting was getting completed by a single vessel revisiting the port multiple times. With addition of MOORING_TIME_PORT set to 2 hours optimizer uses all the vessels available in the tested data.

## Optimizer initialization and features

Optimizer is initialized using number of nodes, number of vessels and depot index (or indices of start and end nodes for each vessel). It creates manager

Then we create a routing model.
In the model we create dimensions for distance, time, capacity with max constrain for each of them (only capacity is a real used constrain here), allowing slack time (waiting outside in certain scenarios) and their callbacks.

We use time callbacks to define our Cost. This is what we optimize.
`routing.SetArcCostEvaluatorOfVehicle(transit_callback_indices[vessel_index], vessel_index)`

## Constrains

Next step is implementation of additional constrains. Capacity constrains are implemented at the step of adding capacity dimension. We add 3 additional constrains:
- time window constrains
- pickup and delivery
- location visit constrains

### 1. time window constrains

- Using time cumulitive variable for each virtual location set range when it is valid.
    - additionally for each virtual location we remove an interval from the start of unavailability time window minus time it takes to load/unload items at that node to end of the unavailability time window
- Do the same but for starting node of each vessel. (currently without unavailability intervals)
- Initiate start and end time
Ortools guides have an article on that topic. It can be just copied and pasted directly

See: https://developers.google.com/optimization/routing/vrptw

### 2. pickup and delivery

Ortools has a guide and a specific module for adding pickups and deliveries. 

Follow guide here:

See: https://developers.google.com/optimization/routing/pickup_delivery

### 3. location visit constrains. Vessels cannot visit the same location at the same time

This problem is not directly covered in the guides however it has a similar problem for depot. 

First of all we split virtual nodes to platforms and ports and we assume that ports can handle more vessels than platform. 

We loop through a list of real locations, for every virtual location which is a part of real location (node of unloading item 1 at platform 2 when looping through nodes for platform 2 for example) we add a time interval of a certain length for each virtual node using time dimension and save them under real location key in a dictionary.

After we add a cumulitive constrain. For every interval of a node for a given virtual location we set value 1 and add constrain that during the provided intervals. It calculates sum across triggered nodes (by vessel visit) and restricts it to a provided capacity value such as `data["location_capacity"]`. 

As we allow different number of vessels to ports and platforms we use different values for `data["port_capacity"]` and `data["location_capacity"]`

Here is part of docstring of `solver.Cumulative`
```
This constraint forces that, for any integer t, the sum of the demands
corresponding to an interval containing t does not exceed the given
capacity.
```

See: https://developers.google.com/optimization/routing/cvrptw_resources

## Additional features and search parameters

Allowing to drop nodes with a huge penalty. It will allow optimizer to find a solution when feasibility cannot be achieved with given items and constrains

See search parameter options: https://developers.google.com/optimization/routing/routing_options

## Output

Output is printed in 2 ways:

First are the routes displayed in console. They show time of arrival at each node showing a range using slack time, load at each node, total distances and times

The second output is a solution csv file.
The file is generated by looping through nodes in route of each vehicle and based on current node and previous node generating leg based solution (traveling between each pair of nodes). Descriptions of the columns in the file are explained in **Reference**.

The solution file is saved in 2 places.
1. `data/output/solution.csv`
2. `data/output/logs/<commit_timestamp>_<commit_hash>/solution_<commit_timestamp>.csv`
Second file is saved for logging the outputs and comparing across different commits to ease testing during development.

If `python main.py -u` expected solution file is also getting updated in `data/output/validation/expected_solution.csv`

# See:
- [ortools guide](https://developers.google.com/optimization/routing)