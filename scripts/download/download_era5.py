"""Download the ERA5 files the pipeline reads (PIPELINE.md, "Pipeline inputs") from the Copernicus Climate
Data Store, and check their contents against ERA5.fingerprints.json.

Usage:
    python scripts/download/download_era5.py [--out-dir DIR]        (default: <repo>/data/raw/era5)
    python scripts/download/download_era5.py --write-fingerprints   (record the files in --out-dir)

Requirements:
- A CDS account, with the ERA5 licence accepted and the API key in ~/.cdsapirc
  (https://cds.climate.copernicus.eu/how-to-api).
- The `cdsapi` package (pip install cdsapi), plus numpy and netCDF4. cdsapi is only needed when a file is
  actually downloaded, so files that are already present can be checked without it.

Checking: CDS files are not byte-identical between retrievals, because the netCDF conversion writes the
retrieval time and a temporary path into the `history` attribute. Each file is therefore checked by
content instead: ERA5.fingerprints.json holds a SHA-256 of every variable's values (and of its units
attribute) in the files used for the manuscript. A file already present with matching contents is
skipped; a download that does not match is kept as <name>.part and reported.

Files:
- ERA5_surface_CAMP2Ex_RF17_wide_extra.nc: single levels, 2019-10-02 00-04 UTC (read by
  camp2ex/s04_era5_atmosphere.py: 2 m temperature and surface pressure).
- ERA5_upper_CAMP2Ex_RF17_wide.nc: 37 pressure levels, same times (read by s04: geopotential and
  temperature).

Grid: both files are on a 0.25 deg grid anchored at 21.4 N, 118 E (latitudes 21.4, 21.15, ..., 17.4;
longitudes 118, ..., 123), not on ERA5's native grid. The CDS reproduces it only with area
[21.4, 118, 17.4, 123] and an explicit grid of 0.25 deg; both downloads then match the manuscript files
exactly (tested 2026-10-21). The requests recorded with the files, with area [21.5, 118, 17.25, 123]
(surface) and [21.5, 118, 17, 123] (pressure levels) and no grid, now return native-grid points instead
(21.5, 21.25, ...), and with area [21.4, 118, 17.4, 123] alone the CDS snaps to native points inside it.
"""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import netCDF4
import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
FINGERPRINTS = SCRIPT_DIR / 'ERA5.fingerprints.json'

# File name -> (CDS dataset, request). The surface request is the one used for the manuscript.
REQUESTS = {
    'ERA5_surface_CAMP2Ex_RF17_wide_extra.nc': (
        'reanalysis-era5-single-levels',
        {
            'product_type': ['reanalysis'],
            'variable': [
                '10m_u_component_of_wind',
                '10m_v_component_of_wind',
                '2m_dewpoint_temperature',
                '2m_temperature',
                'mean_sea_level_pressure',
                'sea_surface_temperature',
                'surface_pressure',
                '100m_u_component_of_wind',
                '100m_v_component_of_wind',
            ],
            'year': ['2019'],
            'month': ['10'],
            'day': ['02'],
            'time': ['00:00', '01:00', '02:00', '03:00', '04:00'],
            'data_format': 'netcdf',
            'download_format': 'unarchived',
            'area': [21.4, 118, 17.4, 123],
            'grid': ['0.25', '0.25'],
        },
    ),
    'ERA5_upper_CAMP2Ex_RF17_wide.nc': (
        'reanalysis-era5-pressure-levels',
        {
            'product_type': ['reanalysis'],
            'variable': [
                'divergence',
                'fraction_of_cloud_cover',
                'geopotential',
                'ozone_mass_mixing_ratio',
                'potential_vorticity',
                'relative_humidity',
                'specific_cloud_ice_water_content',
                'specific_cloud_liquid_water_content',
                'specific_humidity',
                'specific_rain_water_content',
                'specific_snow_water_content',
                'temperature',
                'u_component_of_wind',
                'v_component_of_wind',
                'vertical_velocity',
                'vorticity',
            ],
            'year': ['2019'],
            'month': ['10'],
            'day': ['02'],
            'time': ['00:00', '01:00', '02:00', '03:00', '04:00'],
            'pressure_level': [
                '1', '2', '3', '5', '7', '10', '20', '30', '50', '70', '100', '125', '150', '175',
                '200', '225', '250', '300', '350', '400', '450', '500', '550', '600', '650', '700',
                '750', '775', '800', '825', '850', '875', '900', '925', '950', '975', '1000',
            ],
            'data_format': 'netcdf',
            'download_format': 'unarchived',
            'area': [21.4, 118, 17.4, 123],
            'grid': ['0.25', '0.25'],
        },
    ),
}
FILES = list(REQUESTS)


def fingerprint(path):
    """SHA-256 of each variable's decoded values and units, keyed by variable name."""
    result = {}
    with netCDF4.Dataset(path) as ds:
        for name, var in sorted(ds.variables.items()):
            h = hashlib.sha256()
            values = var[...]
            if values.dtype.kind in 'OSU':
                h.update('\x00'.join(str(v) for v in np.ravel(values)).encode())
            else:
                values = np.ma.filled(np.ma.asarray(values, dtype=values.dtype),
                                      np.nan if values.dtype.kind == 'f' else 0)
                h.update(str(values.shape).encode())
                h.update(np.ascontiguousarray(values).tobytes())
            h.update(str(getattr(var, 'units', '')).encode())
            result[name] = h.hexdigest()
    return result


def mismatches(path, expected):
    """Variables whose fingerprint differs from the expected one (missing or extra ones included)."""
    actual = fingerprint(path)
    return sorted(k for k in set(actual) | set(expected) if actual.get(k) != expected.get(k))


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--out-dir', type=Path, default=PROJECT_ROOT / 'data' / 'raw' / 'era5')
    parser.add_argument('--write-fingerprints', action='store_true',
                        help='record the fingerprints of the files in --out-dir and exit')
    args = parser.parse_args()
    out_dir = args.out_dir.resolve()

    if args.write_fingerprints:
        fingerprints = {f: fingerprint(out_dir / f) for f in FILES}
        FINGERPRINTS.write_text(json.dumps(fingerprints, indent=2, sort_keys=True) + '\n')
        print(f'Wrote {FINGERPRINTS}')
        return 0

    expected = json.loads(FINGERPRINTS.read_text())
    out_dir.mkdir(parents=True, exist_ok=True)
    failed = []
    for name in FILES:
        path = out_dir / name
        if path.exists():
            diff = mismatches(path, expected[name])
            if not diff:
                print(f'present: {name}')
                continue
            print(f'present but different ({", ".join(diff)}): {name}')
        try:
            import cdsapi
        except ImportError:
            print(f'cannot download {name}: the cdsapi package is not installed (pip install cdsapi)')
            failed.append(name)
            continue
        dataset, request = REQUESTS[name]
        part = out_dir / (name + '.part')
        print(f'downloading: {name}')
        try:
            cdsapi.Client().retrieve(dataset, request).download(str(part))
        except Exception as e:
            part.unlink(missing_ok=True)
            print(f'cannot download {name}: {e}')
            print('Check the CDS API key in ~/.cdsapirc and that the ERA5 licence is accepted '
                  '(https://cds.climate.copernicus.eu/how-to-api).')
            failed.append(name)
            continue
        diff = mismatches(part, expected[name])
        if diff:
            print(f'DIFFERENT: {name}: {", ".join(diff)} differ from the manuscript file; kept as {part}')
            failed.append(name)
            continue
        os.replace(part, path)
        print(f'ok: {name}')

    if failed:
        print(f'{len(failed)} file(s) not verified: {", ".join(failed)}')
        return 1
    print(f'All files match {FINGERPRINTS.name}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
