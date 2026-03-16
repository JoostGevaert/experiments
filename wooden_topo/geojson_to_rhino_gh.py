"""Convert a GeoJSON file to a Grasshopper data tree with Rhino geometries.

    Each feature's geometry is converted to a branch in the output tree.
    Multi-types and GeometryCollections create an extra branch level per sub-geometry.
    
    Polygons can be returned as a list of closed polylines or as a trimmed
    surface, i.e. planar Brep. The first polyline in the list is the exterior,
    i.e. perimeter of the polygon. Subsequent polylines in the list are the
    interiors, i.e. holes in the polygon. Returning list of closed polylines for
    (multi-)polygona is default, because it's much quicker than returning a
    trimmed surface.

    Args:
        json_path: (str); GeoJSON file path; path to the .geojson or .json file to load
        polygon_to_polylines: (bool); Polygon to Polylines; if True, polygons are returned
            as a list of closed polylines; if False, a trimmed planar Brep is returned for each polygon.

    Returns:
        geometries: (tree); Rhino geometry tree, one branch per feature (or sub-geometry)
        property_keys: (tree); feature property keys, one branch per feature
        property_values: (tree); feature property values, one branch per feature"""

import json

import ghpythonlib.treehelpers as th
import Rhino.Geometry as rg


def _pt(c):
    return rg.Point3d(c[0], c[1], c[2] if len(c) > 2 else 0)


def _polygon_to_brep(coords):
    exterior_curve = rg.PolylineCurve([_pt(c) for c in coords[0]])
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


def _polygon_to_polylines(coords):
    return [rg.PolylineCurve([_pt(c) for c in ring]) for ring in coords]


def geojson_to_rhino_geometry(geom, polygon_to_polylines=True):
    """Convert a GeoJSON geometry to a list (or list of lists) of Rhino geometry.

    Single types (Point, LineString, Polygon) return a flat list with one item,
    placed in branch {i} of the output tree.

    Multi types (MultiPoint, MultiLineString, MultiPolygon) return a list of
    one-item lists, creating an extra branch level {i;j} per sub-geometry.

    When polygon_to_polylines is True, Polygon returns a list of closed polylines
    (one per ring) and MultiPolygon returns a list of such lists per sub-polygon.

    GeometryCollection returns a list of lists, one per contained geometry.
    """
    geom_type = geom["type"]

    if geom_type == "GeometryCollection":
        return [geojson_to_rhino_geometry(g, polygon_to_polylines) for g in geom["geometries"]]

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
        if polygon_to_polylines:
            return _polygon_to_polylines(coords)
        return [_polygon_to_brep(coords)]

    elif geom_type == "MultiPolygon":
        if polygon_to_polylines:
            return [_polygon_to_polylines(poly_coords) for poly_coords in coords]
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
    geometries.append(geojson_to_rhino_geometry(geom, polygon_to_polylines))

    properties = feat["properties"]
    property_keys.append(list(properties.keys()))
    property_values.append(list(properties.values()))

geometries = th.list_to_tree(geometries)
property_keys = th.list_to_tree(property_keys)
property_values = th.list_to_tree(property_values)
