"""Namespace that holds commonly used projections defined using pyproj.CRS."""

from pyproj import CRS

projected = CRS(("EPSG", 3857))

gps = CRS(("EPSG", 4326))
"""GPS Projection as chiefly used by Marine Traffic and onboard vessels - https://epsg.io/4326"""
