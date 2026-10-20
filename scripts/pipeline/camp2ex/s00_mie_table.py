"""Water Mie table used by every CAMP2Ex retrieval.

Source: src/main/run_at3d.py, the get_mono_table call and the commented-out save line below it.
Conda env: at3d_pure_k9
Output: mie_tables/red_mie_table.nc
Changes: output path is OUT_ROOT-relative; relative_dir=None so the table is computed rather than
         loaded from an existing mie_tables/ directory.
"""
from pathlib import Path
import os
import at3d

PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUT_ROOT = Path(os.environ.get('OUT_ROOT', PROJECT_ROOT))

wavelength = 0.67
mie_mono_table = at3d.mie.get_mono_table(
    'Water',
    (wavelength, wavelength),
    max_integration_radius=65.0,
    minimum_effective_radius=5.5,
    relative_dir=None,
    verbose=False
)
(OUT_ROOT / 'mie_tables').mkdir(parents=True, exist_ok=True)
mie_mono_table.to_netcdf(OUT_ROOT / 'mie_tables' / 'red_mie_table.nc')
