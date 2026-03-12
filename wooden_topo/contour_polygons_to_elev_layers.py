import marimo

__generated_with = "0.20.4"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import geopandas as gpd
    import shapely
    from shapely import Polygon, MultiPolygon
    from shapely.ops import unary_union

    return MultiPolygon, Polygon, gpd, mo, shapely


@app.cell
def _(gpd, mo):
    data_dir = mo.notebook_location() / "data"
    contour_polygons = gpd.read_file(
        data_dir / "20m_contour_polygons_of_5x5_dem.gpkg"
        # data_dir / "20m_contour_polygons_of_10x10_dem.gpkg"
    )

    # Union first and last layers
    vaalse_berg = contour_polygons.tail(1)
    _first_two = contour_polygons.head(2)
    _last_two = contour_polygons.tail(2)
    _first_last_polygons = gpd.GeoDataFrame(
        {
            "ID": [_first_two["ID"].max(), _last_two["ID"].min()],
            "ELEV_MIN": [
                _first_two["ELEV_MIN"].min(),
                _last_two["ELEV_MIN"].min(),
            ],
            "ELEV_MAX": [
                _first_two["ELEV_MAX"].max(),
                _last_two["ELEV_MAX"].max(),
            ],
            "geometry": [_first_two.union_all(), _last_two.union_all()],
        },
        crs=contour_polygons.crs,
    )
    contour_polygons = gpd.pd.concat(
        [_first_last_polygons, contour_polygons.iloc[2:-2].copy()],
    ).sort_values(by="ELEV_MIN", ignore_index=True)

    # Display
    contour_polygons.tail(3)
    return contour_polygons, data_dir


@app.cell
def _(mo):
    min_area = mo.ui.slider(start=10_000, stop=200_000, step=10_000, value=100_000, label="Min. area size (m2)")
    min_area
    return (min_area,)


@app.cell
def _(clean_multipolygon, contour_polygons, min_area):
    clean_multipolygon(contour_polygons.iloc[6].geometry, min_area.value)
    return


@app.cell
def _(clean_multipolygon, contour_polygons, min_area):
    clean_contour_polys = contour_polygons.copy()
    clean_contour_polys["geometry"] = clean_contour_polys.geometry.apply(
        lambda g: clean_multipolygon(g, min_area.value)
    )

    clean_contour_polys.tail(3).explore()
    return (clean_contour_polys,)


@app.cell
def _(mo):
    merge_polygons = mo.ui.run_button(label="Press to merge contour polygons into topo layers")
    merge_polygons
    return (merge_polygons,)


@app.cell
def _(clean_contour_polys, gpd, merge_polygons):
    if merge_polygons.value:
        topo_layers = []
        for idx, row in clean_contour_polys.iterrows():
            cumul = clean_contour_polys.iloc[idx:]
            topo_layers.append(
                {
                    "ID": row["ID"],
                    "ELEV_MIN": cumul["ELEV_MIN"].min(),
                    "ELEV_MAX": cumul["ELEV_MAX"].max(),
                    "geometry": cumul.union_all(),
                }
            )
    
        topo_layers = gpd.GeoDataFrame(topo_layers, crs=clean_contour_polys.crs)
    return (topo_layers,)


@app.cell
def _(mo, topo_layers):
    viz_layer = mo.ui.radio(
        {f"{v:.0f}": i for i, v in enumerate(topo_layers["ELEV_MIN"])},
        value="60",
        label="Show area with elevations above:",
    )
    viz_layer
    return (viz_layer,)


@app.cell
def _(topo_layers, viz_layer):
    i = viz_layer.value
    topo_layers.iloc[i:i+1].explore()
    return


@app.cell
def _(data_dir, topo_layers):
    topo_layers.to_file(data_dir / "20m_topo_layers.gpkg", driver="GPKG", layer="20m_topo_layers")
    return


@app.cell
def _(data_dir, topo_layers):
    topo_layers.to_file(data_dir / "20m_topo_layers.geojson", driver="GEOJSON")
    return


@app.cell
def _(MultiPolygon, Polygon, shapely):
    def clean_multipolygon(
        multi_polygon: shapely.MultiPolygon, minimum_area: float
    ) -> shapely.MultiPolygon:
        cleaned_polygons = []
        for poly in multi_polygon.geoms:
            # Skip small polygons
            if poly.area < minimum_area:
                continue

            # Filter holes
            new_holes = []
            for ring in poly.interiors:
                hole = Polygon(ring)
                if hole.area >= minimum_area:
                    new_holes.append(ring.coords)

            cleaned_polygons.append(Polygon(poly.exterior.coords, new_holes))
        
        return MultiPolygon(cleaned_polygons)

    return (clean_multipolygon,)


if __name__ == "__main__":
    app.run()
