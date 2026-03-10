import marimo

__generated_with = "0.20.4"
app = marimo.App(width="medium")


@app.cell
def _():
    import json
    import pprint

    import marimo as mo

    from pmtiles.reader import Reader, MmapSource

    return MmapSource, Reader, mo, pprint


@app.cell
def _(mo):
    cwd = mo.notebook_location()
    pmtiles = cwd / "6-33-21.pmtiles"
    return (pmtiles,)


@app.cell
def _(MmapSource, Reader, mo, pmtiles, pprint):
    with open(pmtiles, "rb") as f:
        reader = Reader(MmapSource(f))
        header = reader.header()
        pprint.pprint(header)
        metadata = reader.metadata()
        # pprint.pprint(metadata)
    
        _max_zoom = header.get("max_zoom", "N/A")
        _min_zoom = header.get("min_zoom", "N/A")
        _num_tiles = header.get("addressed_tiles_count", "N/A")

    mo.md(f"""
    ### PMTiles Info: `{pmtiles.name}`

    | Property | Value |
    |----------|-------|
    | **Min Zoom** | {_min_zoom} |
    | **Max Zoom** | {_max_zoom} |
    | **Addressed Tiles** | {_num_tiles} |

    The **highest zoom level** in this PMTiles file is **{_max_zoom}**.
    """)
    return


@app.cell
def _(MmapSource, Reader, mo, pmtiles):
    import numpy as np
    from PIL import Image
    import io
    import rasterio
    from rasterio.transform import from_bounds
    from rasterio.crs import CRS
    import math
    import tempfile
    from pathlib import Path

    _target_zoom = 17

    def _lng_lat_to_tile(lng, lat, zoom):
        """Convert lng/lat to tile x/y at given zoom."""
        n = 2 ** zoom
        x = int((lng + 180.0) / 360.0 * n)
        lat_rad = math.radians(lat)
        y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
        return x, y

    def _tile_bounds(z, x, y):
        """Get (west, south, east, north) in EPSG:4326 for a tile."""
        n = 2.0 ** z
        west = x / n * 360.0 - 180.0
        east = (x + 1) / n * 360.0 - 180.0
        north_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
        south_rad = math.atan(math.sinh(math.pi * (1 - 2 * (y + 1) / n)))
        north = math.degrees(north_rad)
        south = math.degrees(south_rad)
        return west, south, east, north

    def _decode_elevation(rgb_array, encoding="terrarium"):
        """Decode RGB-encoded elevation tiles."""
        r = rgb_array[:, :, 0].astype(np.float64)
        g = rgb_array[:, :, 1].astype(np.float64)
        b = rgb_array[:, :, 2].astype(np.float64)
        if encoding == "terrarium":
            return (r * 256.0 + g + b / 256.0) - 32768.0
        else:
            return -10000.0 + ((r * 65536.0 + g * 256.0 + b) * 0.1)

    with open(pmtiles, "rb") as f:
        reader = Reader(MmapSource(f))
        _hdr = reader.header()
        _mtd = reader.metadata()

        _eff_zoom = min(_target_zoom, _hdr.get("max_zoom", 0))

        # Get bounds from header (stored as e7 = degrees * 10^7)
        _min_lon = _hdr.get("min_lon_e7", 0) / 1e7
        _min_lat = _hdr.get("min_lat_e7", 0) / 1e7
        _max_lon = _hdr.get("max_lon_e7", 0) / 1e7
        _max_lat = _hdr.get("max_lat_e7", 0) / 1e7

        # Convert bounds to tile coordinates
        _min_tx, _min_ty = _lng_lat_to_tile(_min_lon, _max_lat, _eff_zoom)
        _max_tx, _max_ty = _lng_lat_to_tile(_max_lon, _min_lat, _eff_zoom)

        _nx = _max_tx - _min_tx + 1
        _ny = _max_ty - _min_ty + 1

        # Detect encoding from metadata
        _encoding = "terrarium"
        if isinstance(_mtd, dict) and "encoding" in _mtd:
            _encoding = _mtd["encoding"]

        # Determine tile size from first available tile
        _tile_size = 256
        _sample = reader.get(_eff_zoom, _min_tx, _min_ty)
        if _sample:
            _img = Image.open(io.BytesIO(_sample))
            _tile_size = _img.size[0]

        # Allocate output array
        _elevation = np.full((_ny * _tile_size, _nx * _tile_size), np.nan, dtype=np.float64)

        _tiles_read = 0
        for _ty in range(_min_ty, _max_ty + 1):
            for _tx in range(_min_tx, _max_tx + 1):
                _tile_data = reader.get(_eff_zoom, _tx, _ty)
                if _tile_data is None:
                    continue
                _img = Image.open(io.BytesIO(_tile_data))
                _rgb = np.array(_img.convert("RGB"))
                _elev_tile = _decode_elevation(_rgb, _encoding)

                _row = (_ty - _min_ty) * _tile_size
                _col = (_tx - _min_tx) * _tile_size
                _elevation[_row:_row + _tile_size, _col:_col + _tile_size] = _elev_tile
                _tiles_read += 1

    # Compute geographic bounds for the full mosaic
    _west, _, _, _north = _tile_bounds(_eff_zoom, _min_tx, _min_ty)
    _, _south, _east, _ = _tile_bounds(_eff_zoom, _max_tx, _max_ty)

    _transform = from_bounds(_west, _south, _east, _north, _elevation.shape[1], _elevation.shape[0])

    # Write to a GeoTIFF
    _output_path = Path(tempfile.gettempdir()) / f"elevation_z{_eff_zoom}.tif"

    with rasterio.open(
        _output_path,
        "w",
        driver="GTiff",
        height=_elevation.shape[0],
        width=_elevation.shape[1],
        count=1,
        dtype="float64",
        crs=CRS.from_epsg(4326),
        transform=_transform,
        nodata=np.nan,
    ) as _dst:
        _dst.write(_elevation, 1)

    # Read back as a rasterio dataset for further use
    elevation_raster = rasterio.open(_output_path)

    mo.md(f"""
    ### Elevation Raster Extracted

    | Property | Value |
    |----------|-------|
    | **Zoom Level** | {_eff_zoom} |
    | **Tiles Read** | {_tiles_read} / {_nx * _ny} |
    | **Grid Size** | {_nx} × {_ny} tiles |
    | **Raster Shape** | {_elevation.shape[1]} × {_elevation.shape[0]} px |
    | **Bounds (W, S, E, N)** | {_west:.6f}, {_south:.6f}, {_east:.6f}, {_north:.6f} |
    | **Encoding** | {_encoding} |
    | **Elevation Range** | {np.nanmin(_elevation):.2f} m – {np.nanmax(_elevation):.2f} m |
    | **Output File** | `{_output_path}` |

    Rasterio dataset stored in `elevation_raster`.
    """)
    return


if __name__ == "__main__":
    app.run()
