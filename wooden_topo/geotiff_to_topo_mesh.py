import marimo

__generated_with = "0.20.4"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import pyvista as pv

    return mo, pv


@app.cell
def _(mo, pv):
    data_dir = mo.notebook_location() / "data"

    dem_tif_path = data_dir / "zuid_limburg_4m_dem.tif"
    dem_reader = pv.get_reader(dem_tif_path)

    topo_mesh_path = data_dir / "zuid_limburg_4m_topo_mesh.ply"
    return dem_reader, topo_mesh_path


@app.cell
def _(dem_reader):
    dem_raster_imdata = dem_reader.read()
    dem_raster_imdata
    return (dem_raster_imdata,)


@app.cell
def _(dem_raster_imdata):
    # I want to directly go from ImageData to quad mesh PolyData
    # Stuff that doesn't work
    quad_mesh2 = dem_raster_imdata.compute_surface()
    quad_mesh2 = dem_raster_imdata.extract_surface(algorithm="geometry", scalars="Tiff Scalars")
    quad_mesh2 = dem_raster_imdata.slice(0).elevation()
    return


@app.cell
def _(dem_raster_imdata, pv):
    # Convert ImageData to a quad mesh with elevation from Tiff Scalars
    _points = dem_raster_imdata.points.copy()
    _scalars = dem_raster_imdata["Tiff Scalars"]
    _points[:, 2] = _scalars

    _dem_grid = pv.StructuredGrid()
    _dem_grid.points = _points
    _dem_grid.dimensions = dem_raster_imdata.dimensions
    _dem_grid["elevation"] = _scalars
    quad_mesh = _dem_grid.extract_surface(algorithm="geometry")
    quad_mesh
    return (quad_mesh,)


@app.cell
def _(mo):
    plot_button = mo.ui.run_button(label="Press to plot pyvista data")
    export_mesh_button = mo.ui.run_button(label="Press to export PLY mesh")
    mo.hstack([plot_button, export_mesh_button], justify="start")
    return export_mesh_button, plot_button


@app.cell
def _(export_mesh_button, mo, quad_mesh, topo_mesh_path):
    if export_mesh_button.value:
        quad_mesh.save(topo_mesh_path, binary=True)
        mo.md(f"Exported mesh to `{_output_path}` ({_surface_mesh.n_points} points, {_surface_mesh.n_cells} faces)")
    return


@app.cell
def _(plot_button, quad_mesh):
    if plot_button.value:
        quad_mesh.plot()
    return


if __name__ == "__main__":
    app.run()
