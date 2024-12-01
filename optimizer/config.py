"""Configuration file with optimizer parameters."""

SOLUTION_TIME_LIMIT_SECONDS = 10
SOLUTION_LIMIT = 10000  # Limit to the number of solutions generated during the search.
MAX_DISTANCE_PER_VEHICLE = 100000000
MAX_WAITING_TIME = 100000  # allow waiting time
MAX_WAITING_TIME_PER_VEHICLE = 100000  # maximum time per vehicle
PENALTY = 100000000  # Penalty for dropping nodes
LOG_SEARCH = True  # Enable logging of the solution searching process

DISTANCE_UNITS_M = 100  # 100m distance units
PICKUP_LOCATION_DEFAULT = "Port"  # name of the location where depot is set
TIME_PER_ITEM_LOADED = 3
TIME_PER_ITEM_UNLOADED = 3
ONE_LIFT = 100  # KG or less. 1 items is at least 1 lift
MOORING_TIME = 10  # extra time it takes for a vessel to unmoor from one location and moor to another location
MOORING_TIME_PORT = 120  # extra time it takes for a vessel to unmoor from one location and moor to port. Added separately to add penalty for vessel revisiting port

PLATFORM_CAPACITY = 1  # number of vessels platforms can handle at the same time
PORT_CAPACITY = 6  # number of vessels ports can handle at the same time

PROJECTED_CRS = 3857  # https://epsg.io/3857
GPS_CRS = 4326  # https://epsg.io/4326

START_TIMESTAMP = "2022-01-01T00:00:00+04:00"
TIME_WINDOW_START = 0  # hours
TIME_WINDOW_END = 24  # hours
