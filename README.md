# Lundstrom2025
Lundstrom et al. (2025) will demonstrate the practical application of AT3D using a case study from CAMP2Ex and observations from MISR.

## Reproducing the manuscript

Figures from the data record (no retrievals rerun):

```bash
envs/create_envs.sh vis2 vis2_clone                           # conda envs used by the figure scripts
tar -xzf LundstromPub2025_data_record.tar.gz -C .             # data record, unpacked in the repo root
scripts/release/verify_data_record.sh                         # check the unpacked files
scripts/download/download_camp2ex.sh                          # CAMP2Ex in situ files for Fig 7
bash scripts/figures/run_figures.sh                           # all figures -> figures/manuscript/
```

- `PIPELINE.md`: rebuild every input file from raw data (`scripts/pipeline/run_pipeline.sh`), and what the
  data record contains.
- `FIGURES.md`: regenerate each figure (`scripts/figures/run_figures.sh`) and trace it to its data.
- `archive/`: code and data not used by any figure, kept at their original relative paths.
