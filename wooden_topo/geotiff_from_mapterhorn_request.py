import marimo

__generated_with = "0.20.4"
app = marimo.App(width="medium")


@app.cell
def _():
    import math
    import io

    import marimo as mo
    import numpy as np
    import plotly.graph_objects as go
    import requests

    from PIL import Image
    from concurrent.futures import ThreadPoolExecutor, as_completed

    return (
        Image,
        ThreadPoolExecutor,
        as_completed,
        go,
        io,
        math,
        mo,
        np,
        requests,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Mapterhorn Topography Mesh

    Downloads Terrarium terrain tiles from Mapterhorn (`tiles.mapterhorn.com`),
    stitches them into an elevation grid, and exports a quad mesh as OBJ.

    Tiles are 512×512 WebP, zoom 0–17.
    **Terrarium encoding:** `elevation = R×256 + G + B/256 − 32768` (metres)
    """)
    return


@app.cell
def _(mo):
    zoom_slider = mo.ui.slider(10, 17, value=16, label="Zoom level (10=coarse … 17=finest)")
    mesh_res_slider = mo.ui.slider(
        50, 800, step=50, value=300,
        label="Output mesh resolution (grid points along longer axis)"
    )
    mo.vstack([
        mo.md("## Parameters"),
        mo.md("**Bounding box (fixed):** min_lon=5.615151, min_lat=50.750133, max_lon=6.113109, max_lat=50.988467"),
        zoom_slider,
        mesh_res_slider,
    ])
    return (zoom_slider,)


@app.cell
def _(math):
    def lon_lat_to_tile(lon, lat, zoom):
        """Slippy-map tile coordinate for a lon/lat point."""
        n = 2 ** zoom
        x = int((lon + 180.0) / 360.0 * n)
        lat_rad = math.radians(lat)
        y = int((1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi) / 2.0 * n)
        return x, y

    def tile_nw_corner(tx, ty, zoom):
        """Longitude/latitude of the NW (top-left) corner of tile (tx, ty)."""
        n = 2 ** zoom
        lon = tx / n * 360.0 - 180.0
        lat = math.degrees(math.atan(math.sinh(math.pi * (1.0 - 2.0 * ty / n))))
        return lon, lat

    return lon_lat_to_tile, tile_nw_corner


@app.cell
def _(Image, io, np, requests):
    def fetch_terrarium_tile(z, x, y):
        """Fetch one Terrarium terrain tile and return a float64 elevation array (512×512, metres)."""
        url = f"https://tiles.mapterhorn.com/{z}/{x}/{y}.webp"
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        img = Image.open(io.BytesIO(resp.content)).convert("RGB")
        rgb = np.array(img, dtype=np.float64)
        return rgb[:, :, 0] * 256.0 + rgb[:, :, 1] + rgb[:, :, 2] / 256.0 - 32768.0

    return (fetch_terrarium_tile,)


@app.cell
def _(
    ThreadPoolExecutor,
    as_completed,
    fetch_terrarium_tile,
    lon_lat_to_tile,
    mo,
    np,
    tile_nw_corner,
    zoom_slider,
):
    MIN_LON, MIN_LAT = 5.615151, 50.750133
    MAX_LON, MAX_LAT = 6.113109, 50.988467
    TILE_SIZE = 512

    zoom = zoom_slider.value

    # Tile ranges — y increases southward in slippy-map convention
    tx0, ty0 = lon_lat_to_tile(MIN_LON, MAX_LAT, zoom)   # NW tile
    tx1, ty1 = lon_lat_to_tile(MAX_LON, MIN_LAT, zoom)   # SE tile

    n_cols = tx1 - tx0 + 1
    n_rows = ty1 - ty0 + 1
    n_tiles = n_cols * n_rows

    with mo.status.spinner(title=f"Downloading {n_cols}×{n_rows} = {n_tiles} tiles\nat zoom {zoom}…"):
        tiles = {}
        with ThreadPoolExecutor(max_workers=16) as executor:
            futures = {
                executor.submit(fetch_terrarium_tile, zoom, tx0 + col, ty0 + row): (row, col)
                for row in range(n_rows)
                for col in range(n_cols)
            }
            for future in as_completed(futures):
                row, col = futures[future]
                tiles[(row, col)] = future.result()

    # Stitch tiles into one big array
    full_grid = np.zeros((n_rows * TILE_SIZE, n_cols * TILE_SIZE), dtype=np.float64)
    for (row, col), data in tiles.items():
        r0, c0 = row * TILE_SIZE, col * TILE_SIZE
        full_grid[r0:r0 + TILE_SIZE, c0:c0 + TILE_SIZE] = data

    # Geographic bounds of the stitched grid
    grid_nw_lon, grid_nw_lat = tile_nw_corner(tx0, ty0, zoom)
    grid_se_lon, grid_se_lat = tile_nw_corner(tx1 + 1, ty1 + 1, zoom)

    mo.md(
        f"Fetched **{n_tiles}** tiles → stitched grid **{full_grid.shape[1]}×{full_grid.shape[0]}** px "
        f"(lon {grid_nw_lon:.4f}→{grid_se_lon:.4f}, lat {grid_nw_lat:.4f}→{grid_se_lat:.4f})"
    )
    return (
        MAX_LAT,
        MAX_LON,
        MIN_LAT,
        MIN_LON,
        full_grid,
        grid_nw_lat,
        grid_nw_lon,
        grid_se_lat,
        grid_se_lon,
        zoom,
    )


@app.cell
def _(
    full_grid,
    grid_nw_lat,
    grid_nw_lon,
    grid_se_lat,
    grid_se_lon,
    math,
    mo,
    zoom,
):
    import rasterio
    from rasterio.transform import from_bounds

    # Convert grid corners from EPSG:4326 to EPSG:3857 (Web Mercator)
    def _lonlat_to_webmercator(lon, lat):
        x = lon * 20037508.34 / 180.0
        lat_rad = math.radians(lat)
        y = math.log(math.tan(math.pi / 4.0 + lat_rad / 2.0)) * 20037508.34 / math.pi
        return x, y

    _nw_x, _nw_y = _lonlat_to_webmercator(grid_nw_lon, grid_nw_lat)
    _se_x, _se_y = _lonlat_to_webmercator(grid_se_lon, grid_se_lat)

    # Rasterio expects (west, south, east, north)
    _transform = from_bounds(_nw_x, _se_y, _se_x, _nw_y, full_grid.shape[1], full_grid.shape[0])

    _geotiff_path = mo.notebook_location() / "terrain_elevation.tif"

    with rasterio.open(
        _geotiff_path,
        "w",
        driver="GTiff",
        height=full_grid.shape[0],
        width=full_grid.shape[1],
        count=1,
        dtype=full_grid.dtype,
        crs="EPSG:3857",
        transform=_transform,
        compress="deflate",
        predictor=3,  # floating-point predictor for better compression
    ) as _dst:
        _dst.write(full_grid, 1)
        _dst.set_band_description(1, "Elevation (m)")
        _dst.update_tags(
            source="Mapterhorn Terrarium tiles",
            units="metres",
            zoom=str(zoom),
        )

    mo.md(
        f"GeoTIFF saved to `{_geotiff_path}` — "
        f"**{full_grid.shape[1]}×{full_grid.shape[0]}** pixels, "
        f"CRS: EPSG:3857, "
    )
    return


@app.cell
def _(full_grid):
    full_grid.shape
    return


@app.cell
def _(
    MAX_LAT,
    MAX_LON,
    MIN_LAT,
    MIN_LON,
    full_grid,
    grid_nw_lat,
    grid_nw_lon,
    grid_se_lat,
    grid_se_lon,
    math,
):
    total_h, total_w = full_grid.shape

    # Map lon/lat → pixel in the stitched grid using Web Mercator
    def _merc(lat_deg):
        return math.log(math.tan(math.pi / 4.0 + math.radians(lat_deg) / 2.0))

    def lon_to_px(lon):
        return (lon - grid_nw_lon) / (grid_se_lon - grid_nw_lon) * total_w

    def lat_to_px(lat):
        frac = (_merc(grid_nw_lat) - _merc(lat)) / (_merc(grid_nw_lat) - _merc(grid_se_lat))
        return frac * total_h

    # Pixel window for the exact bounding box
    px0 = max(0, int(lon_to_px(MIN_LON)))
    px1 = min(total_w, int(lon_to_px(MAX_LON)))
    py0 = max(0, int(lat_to_px(MAX_LAT)))   # north → small row index
    py1 = min(total_h, int(lat_to_px(MIN_LAT)))  # south → large row index

    elevation_full = full_grid[py0:py1, px0:px1]
    return (elevation_full,)


@app.cell
def _(elevation_full):
    elevation_full
    return


@app.cell
def _(MAX_LAT, MAX_LON, MIN_LAT, MIN_LON, elevation, np):
    h, w = elevation.shape
    lat_center = (MIN_LAT + MAX_LAT) / 2.0

    lons = np.linspace(MIN_LON, MAX_LON, w)
    lats = np.linspace(MAX_LAT, MIN_LAT, h)   # row 0 = north

    # Approximate metric coordinates (origin = SW corner)
    m_per_deg_lat = 111_320.0
    m_per_deg_lon = 111_320.0 * np.cos(np.radians(lat_center))

    x_m = (lons - MIN_LON) * m_per_deg_lon               # east →
    y_m = (lats - MIN_LAT) * m_per_deg_lat               # north ↑ (positive = north of MIN_LAT)
    return h, lats, lons, w, x_m, y_m


@app.cell
def _(elevation, go, lats, lons, mo):
    fig = go.Figure(
        data=[
            go.Surface(
                z=elevation,
                x=lons,
                y=lats,
                colorscale="Earth",
                colorbar=dict(title="m"),
                lighting=dict(ambient=0.6, diffuse=0.8, roughness=0.5),
            )
        ]
    )
    fig.update_layout(
        title="Topography — South Limburg / Hautes Fagnes",
        scene=dict(
            xaxis_title="Longitude",
            yaxis_title="Latitude",
            zaxis_title="Elevation (m)",
            aspectmode="manual",
            aspectratio=dict(x=2.0, y=1.5, z=0.25),
        ),
        margin=dict(l=0, r=0, t=40, b=0),
        height=600,
    )
    mo.ui.plotly(fig)
    return


@app.cell
def _(elevation, h, mo, step, w, zoom):
    mo.md(f"""
    ## Mesh statistics

    | Property | Value |
    |---|---|
    | Zoom level | {zoom} |
    | Downsample step | every {step}th pixel |
    | Grid size | {w} × {h} vertices |
    | Quad faces | {(w-1)*(h-1):,} |
    | Elevation min | {elevation.min():.1f} m |
    | Elevation max | {elevation.max():.1f} m |
    | Elevation mean | {elevation.mean():.1f} m |
    """)
    return


@app.cell
def _(elevation):
    elevation
    return


@app.cell
def _(elevation, mo, np, x_m, y_m):
    _h, _w = elevation.shape
    xx, yy = np.meshgrid(x_m, y_m)

    obj_lines = [
        "# Quad mesh from Mapterhorn / Terrarium terrain tiles\n",
        f"# Grid: {_w} x {_h} vertices\n",
        "# Coordinates: X=easting (m), Y=northing (m), Z=elevation (m)\n",
        "# Origin: SW corner of bounding box\n\n",
    ]

    # Vertices
    for _j in range(_h):
        for _i in range(_w):
            obj_lines.append(f"v {xx[_j, _i]:.2f} {yy[_j, _i]:.2f} {elevation[_j, _i]:.2f}\n")

    obj_lines.append("\n")

    # Quad faces (1-indexed, CCW winding viewed from above)
    for _j in range(_h - 1):
        for _i in range(_w - 1):
            v0 = _j * _w + _i + 1
            v1 = _j * _w + (_i + 1) + 1
            v2 = (_j + 1) * _w + (_i + 1) + 1
            v3 = (_j + 1) * _w + _i + 1
            obj_lines.append(f"f {v0} {v1} {v2} {v3}\n")

    _obj_path = "houten_topo/terrain_mesh.obj"
    with open(_obj_path, "w") as _f:
        _f.writelines(obj_lines)

    mo.md(
        f"Mesh saved to `{_obj_path}` — "
        f"**{_h * _w:,}** vertices, **{(_h-1)*(_w-1):,}** quad faces "
        f"({sum(len(l) for l in obj_lines) / 1024:.0f} KB)"
    )
    return


if __name__ == "__main__":
    app.run()
