import json

import ghpythonlib.treehelpers as th
import Rhino.Geometry as rg


def _pt(c):
    return rg.Point3d(c[0], c[1], c[2] if len(c) > 2 else 0)


def _polygon_to_brep(coords):
    exterior_curve = rg.PolylineCurve([_pt(c) for c in coords[0]], isClosed=True)
    breps = rg.Brep.CreatePlanarBreps([exterior_curve], 0.01)
    if not breps:
        return None
    brep = breps[0]
    for hole in coords[1:]:
        hole_curve = rg.PolylineCurve([_pt(c) for c in hole])
        hole_brep = rg.Brep.CreatePlanarBreps([hole_curve], 0.01)
        if hole_brep:
            diff = rg.Brep.CreateBooleanDifference([brep], hole_brep, 0.01)
            if diff:
                brep = diff[0]
    return brep


def geojson_to_rhino_geometry(geom):
    """Convert a GeoJSON geometry to a list (or list of lists) of Rhino geometry.

    Single types (Point, LineString, Polygon) return a flat list with one item,
    placed in branch {i} of the output tree.

    Multi types (MultiPoint, MultiLineString, MultiPolygon) return a list of
    one-item lists, creating an extra branch level {i;j} per sub-geometry.

    GeometryCollection is skipped (returns empty list).
    """
    geom_type = geom["type"]

    if geom_type == "GeometryCollection":
        return []

    coords = geom["coordinates"]

    if geom_type == "Point":
        return [_pt(coords)]

    elif geom_type == "MultiPoint":
        return [[_pt(c)] for c in coords]

    elif geom_type == "LineString":
        return [rg.PolylineCurve([_pt(c) for c in coords])]

    elif geom_type == "MultiLineString":
        return [[rg.PolylineCurve([_pt(c) for c in line])] for line in coords]

    elif geom_type == "Polygon":
        return [_polygon_to_brep(coords)]

    elif geom_type == "MultiPolygon":
        return [[_polygon_to_brep(poly_coords)] for poly_coords in coords]

    else:
        return []


with open(json_path, "r") as f:
    geojson = json.load(f)

features = geojson["features"]

geometries = []
property_keys = []
property_values = []
for feat in features:
    geom = feat["geometry"]
    geometries.append(geojson_to_rhino_geometry(geom))

    properties = feat["properties"]
    property_keys.append(list(properties.keys()))
    property_values.append(list(properties.values()))

geometries = th.list_to_tree(geometries)
property_keys = th.list_to_tree(property_keys)
property_values = th.list_to_tree(property_values)
