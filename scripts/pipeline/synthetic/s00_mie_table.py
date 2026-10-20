"""Water Mie table for the synthetic observations, saved so each gen_synthetic_obs job loads it.

Source: the get_mono_table call in gen_synthetic_obs_stochastic.py. There it had
relative_dir='../mie_tables', so the table was loaded from that directory or computed on every run.
Conda env: at3d_pure_k9
Output: data/synthetic/mie_tables/mie_table_0.67.nc
"""
from pathlib import Path
import os
import at3d

PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUT_ROOT = Path(os.environ.get('OUT_ROOT', PROJECT_ROOT))

wavelen = 0.67
mie_table = at3d.mie.get_mono_table('Water',(wavelen, wavelen),
                                    max_integration_radius=200.0,
                                    minimum_effective_radius=0.5,
                                    relative_dir=None,
                                    verbose=False)
(OUT_ROOT / 'data' / 'synthetic' / 'mie_tables').mkdir(parents=True, exist_ok=True)
mie_table.to_netcdf(OUT_ROOT / 'data' / 'synthetic' / 'mie_tables' / 'mie_table_0.67.nc')
