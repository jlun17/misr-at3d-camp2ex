"""Write config.yml and run_at3d.sh for each retrieval in job_list_V11.csv.

Usage: python s10_make_configs.py [job_list.csv]

Source: automation/csv2yml.ipynb, cells idx 1, 2, 4.
Conda env: at3d_pure_k9
Changes:
- Paths in the CSV are relative. config_file_name is relative to PROJECT_ROOT and every other path to
  OUT_ROOT. Paths that fall inside PROJECT_ROOT are written relative to it (src/utils/util.py:load_config
  prepends PROJECT_ROOT); others, e.g. under a separate --out-root, are written absolute.
- sbatch submission and the git commit are removed; run_pipeline.sh submits the jobs with dependencies.
- The job header drops the partition and mail options (sbatch takes them from SBATCH_PARTITION,
  SBATCH_MAIL_USER, ...), and conda is activated from $CONDA_BASE (default `conda info --base`).
- A restart_iter ending in /LAST is resolved when the job starts to the last iterations/iter*.nc of the
  stage-1 run. The original restarts used iter030, which was that run's last iterate.
"""
import csv
import yaml
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUT_ROOT = Path(os.environ.get('OUT_ROOT', PROJECT_ROOT))

def csv_to_dict(filename):
    """Converts a CSV file to a list of dictionaries."""
    with open(filename, 'r') as file:
        reader = csv.DictReader(file)
        return list(reader)


def header(name, n, mem, time):
    """
    PARAMETERS
    ----------
    name: string
        name of batch job
    n: string
        Number of processors needed for the job
    mem: string
        Total RAM required: i.e. '64GB'
    time: string
        Time needed for the job: 'Days-HH:MM:SS'
    """
    string = '#!/bin/bash\n\n'
    string += '#SBATCH --job-name={}\n'.format(name)
    string += '#SBATCH -n {}\n'.format(n)
    string += '#SBATCH --mem {}\n'.format(mem)
    string += '#SBATCH --time={}\n\n'.format(time)
    return string

def runPython(condaEnv, script, args, output=None):
    string = 'source "${{CONDA_BASE:-$(conda info --base)}}/bin/activate" {}\n\n'.format(condaEnv)
    string += 'python {}'.format(script)
    for arg in args:
        string += ' {}'.format(arg)
    if(output != None):
        string += ' > {}'.format(output)
    string += '\n'
    return string

def resolveRestart(restart_iter, config_file):
    stage1_iterations = os.path.dirname(restart_iter)
    string = 'LAST=$(cd {} && ls {}/iter*.nc | sort | tail -n 1)\n'.format(PROJECT_ROOT, stage1_iterations)
    string += 'sed -i "s#^restart_iter: .*#restart_iter: $LAST#" {}\n\n'.format(config_file)
    return string

def config_path(path):
    """Relative to PROJECT_ROOT when inside it (load_config prepends PROJECT_ROOT), else absolute."""
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)

def writeBatch(string, outFile):
    with open(outFile, 'w') as text_file:
        text_file.write(string)
        print('Wrote {}'.format(outFile))

## Load CSV
csv_file = sys.argv[1] if len(sys.argv) > 1 else PROJECT_ROOT / 'scripts' / 'pipeline' / 'camp2ex' / 'job_list_V11.csv'
config = csv_to_dict(csv_file)

floats = ['surface_wind_speed', 'a', 'b', 'error_cov_sf']
paths = ['out_path', 'obs_file', 'rte_grid_file', 'background_scatterers_file', 'cloud_volume_mask_file']
conda_env = 'at3d_pure_k9'
at3d_script = PROJECT_ROOT / 'src' / 'main' / 'run_at3d.py'
for d in config:
    for f in floats:
        d[f] = float(d[f])
    for p in paths:
        d[p] = config_path(OUT_ROOT / d[p]) + ('/' if d[p].endswith('/') else '')
    if(d['restart_iter'].lower() != 'none'):
        d['restart_iter'] = config_path(OUT_ROOT / d['restart_iter'])

    out_path = str(PROJECT_ROOT / d['out_path']) + '/'

    ## generate yml configs
    os.makedirs(out_path, exist_ok=True)
    assert len(os.listdir(out_path)) == 0, '{} contains stuff already'.format(out_path)
    with open('{}config.yml'.format(out_path), 'w') as file:
        yaml.dump(d, file, sort_keys=False)
        print('Wrote {}config.yml'.format(out_path))

    ## Write shell scripts
    name = os.path.basename(out_path[0:-1])
    args = ['{}config.yml'.format(out_path)]
    logfile = '{}at3d.log'.format(out_path)
    hdr = header(name, '4', '64GB', '10-00:00:00')
    body = runPython(conda_env, at3d_script, args, logfile)
    if(d['restart_iter'].endswith('/LAST')):
        body = resolveRestart(d['restart_iter'], args[0]) + body
    shell_file = '{}run_at3d.sh'.format(out_path)
    writeBatch(hdr+body, shell_file)
