This is the codebase associated with the manuscript titled "The Practical Application of Atmospheric Tomography with 3D Radiative Transfer to the Multi-Angle Imaging SpectroRadiometer".

Goal:
1) Create a data record that contains the processed datasets that underly manuscript figures.
2) Create a software record that generates all data and produces manuscript figures.
3) Each record will be archived on Zenodo.

V11 is the final experimental version with retrieval data located under `/data/keeling/a/johntl3/b/LundstromPub2025/experiments/CAMP2Ex_RF17/V11`.

Manuscript figures are located here:
- Figure 2: `/data/keeling/a/johntl3/b/LundstromPub2025/notebooks/figures/3Dextinction.ipynb`.
- Figure 3: `/data/keeling/a/johntl3/b/LundstromPub2025/notebooks/figures/extinction.ipynb` (cell 15).
- Figure 4: `/data/keeling/a/johntl3/b/LundstromPub2025/notebooks/figures/chi2.ipynb` (cell 6).
- Figure 5: `/data/keeling/a/johntl3/b/LundstromPub2025/notebooks/figures/ForwardSim_VS_Obs_pub.ipynb`.
- Figure 6: `/data/keeling/a/johntl3/b/LundstromPub2025/notebooks/figures/ForwardSim_VS_Obs3.ipynb` (cell 7).
- Figure 7: `/data/keeling/a/johntl3/b/LundstromPub2025/notebooks/figures/CAMP2Ex_insitu_reduced.ipynb`.
- Figure 8: `/data/keeling/a/johntl3/b/Synthetic/analysis/lundstrom2025_figures.ipynb` (cell 11).
- Figure 9: `/data/keeling/a/johntl3/b/LundstromPub2025/notebooks/HBC/hbc2.ipynb` (cell 6).
- Figure 10: `/data/keeling/a/johntl3/b/LundstromPub2025/notebooks/HBC/hbc2.ipynb` (cell 7).
- Figure 11: `/data/keeling/a/johntl3/b/LundstromPub2025/notebooks/figures/extinction.ipynb` (cell 19).
- Figure B1: `/data/keeling/a/johntl3/b/LundstromPub2025/notebooks/surface_parameterization_testing/sufrace_parameterization.ipynb`.

V11 retrievals were ran using the automation script `/data/keeling/a/johntl3/b/LundstromPub2025/automation/csv2yml.ipynb` with the associated V11 config files `/data/keeling/a/johntl3/b/LundstromPub2025/automation/job_lists/CAMP2Ex_RF17_V11{version}.csv` where version is the letters a - g. The config files contain pointers to the input files used in the retrieval.
