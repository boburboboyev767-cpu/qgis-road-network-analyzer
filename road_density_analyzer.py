"""
QGIS Urban Road Network & Hexagon Density Analyzer
Calculates road segment lengths and spatial density within hexagonal grids
using OpenStreetMap (QuickOSM) vector layers.
"""

from qgis.core import (
    QgsProject,
    QgsProcessingFeedback,
    QgsField,
    edit
)
from PyQt5.QtCore import QVariant
import processing


def calculate_hex_road_density(road_layer_name: str, hex_layer_name: str):
    """
    Intersects road network with a hexagon grid and computes road density (km/km^2).
    """
    project = QgsProject.instance()
    road_layers = project.mapLayersByName(road_layer_name)
    hex_layers = project.mapLayersByName(hex_layer_name)

    if not road_layers or not hex_layers:
        raise ValueError("Road layer or Hexagon grid layer not found in the active QGIS project.")

    road_layer = road_layers[0]
    hex_layer = hex_layers[0]
    feedback = QgsProcessingFeedback()

    # Calculate total road length intersecting each hexagon cell
    result = processing.run(
        "native:sumlinelengths",
        {
            "POLYGONS": hex_layer,
            "LINES": road_layer,
            "LEN_FIELD": "road_len_m",
            "COUNT_FIELD": "seg_count",
            "OUTPUT": "memory:"
        },
        feedback=feedback
    )

    output_layer = result["OUTPUT"]

    # Add road density field (km of road per sq km)
    provider = output_layer.dataProvider()
    provider.addAttributes([QgsField("density_km2", QVariant.Double)])
    output_layer.updateFields()

    idx_len = output_layer.fields().indexOf("road_len_m")
    idx_den = output_layer.fields().indexOf("density_km2")

    with edit(output_layer):
        for feature in output_layer.getFeatures():
            geom_area_km2 = feature.geometry().area() / 1_000_000.0
            road_len_km = (feature[idx_len] or 0.0) / 1000.0
            density = round(road_len_km / geom_area_km2, 3) if geom_area_km2 > 0 else 0.0
            feature[idx_den] = density
            output_layer.updateFeature(feature)

    project.addMapLayer(output_layer)
    return output_layer
