# conda env 'vis2_clone'
from pathlib import Path
import sys
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from src.Retrieval import Retrieval

EXPERIMENT = PROJECT_ROOT / 'experiments' / 'CAMP2Ex_RF17' / 'V08' / 'default'
TAU1D = EXPERIMENT / 'tau_1D'
r = Retrieval(EXPERIMENT)
r.load_retrieval()

tausA = np.linspace(0, 4.75, 20)
tausB = np.logspace(np.log10(5), 2, 40)
taus = np.append(tausA, tausB)
wavelength = 0.67
cb = 0.4
ct = 1.1
LUT_outfile = TAU1D / 'LUT_1Dtau_400_1100.nc'
r.generate_1D_LUT(wavelength, taus, cb, ct, LUT_outfile)
outfile = TAU1D / 'tau1D_400_1100.nc'
r.retrieve_1D_tau(outfile)