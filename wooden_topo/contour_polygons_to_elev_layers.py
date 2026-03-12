import marimo

__generated_with = "0.20.4"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import geopandas as gpd
    from shapely.ops import unary_union

    return gpd, mo, unary_union


@app.cell
def _(gpd, mo):
    data_dir = mo.notebook_location() / "data"
    contour_polygons = gpd.read_file(data_dir / "20m_contour_polygons_of_10x10_dem.gpkg")
    contour_polygons = contour_polygons.iloc[1:-1]
    contour_polygons.drop("geometry", axis=1)
    # contour_polygons.head(3)
    return contour_polygons, data_dir


@app.cell
def _(contour_polygons, unary_union):
    merged_contours = contour_polygons.copy()

    def cumulative_union_at_i(i):
        return unary_union(contour_polygons.geometry.iloc[i:].values)

    merged_contours["geometry"] = [
        cumulative_union_at_i(i) for i in range(len(contour_polygons))
    ]
    merged_contours = merged_contours.set_geometry("geometry")
    return (merged_contours,)


@app.cell
def _(merged_contours):
    merged_contours.drop("geometry", axis=1)
    return


@app.cell
def _(merged_contours):
    merged_contours.geometry.iloc[-5]
    return


@app.cell
def _(contour_polygons):
    contour_polygons.geometry.iloc[0]
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ```python
    from shapely.ops import unary_union

    # Sort by ELEV_MIN descending so we can cumulatively union from highest to lowest
    _sorted_df = contour_polygons.sort_values("ELEV_MIN", ascending=False).reset_index(drop=True)

    # Cumulatively union geometries: for each row, merge with all rows that have higher ELEV_MIN
    _merged_geometries = []
    _cumulative_geom = None

    for idx, row in _sorted_df.iterrows():
        if _cumulative_geom is None:
            _cumulative_geom = row.geometry
        else:
            _cumulative_geom = unary_union([_cumulative_geom, row.geometry])
        _merged_geometries.append(_cumulative_geom)

    merged_contours = _sorted_df.copy()
    merged_contours["geometry"] = _merged_geometries
    merged_contours = gpd.GeoDataFrame(merged_contours, geometry="geometry", crs=contour_polygons.crs)
    # merged_contours
    ```
    """)
    return


@app.cell
def _(data_dir, merged_contours):
    merged_contours.to_file(data_dir / "20m_contour_layers.gpkg", driver="GPKG", layer="20m_contour_layers")
    return


if __name__ == "__main__":
    app.run()
