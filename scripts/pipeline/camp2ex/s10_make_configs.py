"""Write config.yml and run_at3d.sh for each retrieval in job_list_V11.csv.

Usage: python s10_make_configs.py [job_list.csv]

Source: automation/csv2yml.ipynb, cells idx 1, 2, 4.
Conda env: at3d_pure_k9
Changes:
- Paths in the CSV are relative. config_file_name is resolved against PROJECT_ROOT and every other
  path against OUT_ROOT, so the files written hold absolute paths, as the V11 configs do.
- sbatch submission and the git commit are removed; run_pipeline.sh submits the jobs with dependencies.
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


def header(name, p, n, mem, time, email):
    """
    PARAMETERS
    ----------
    name: string
        name of batch job
    p: string
        node - options of 'node', 'seseml', 'sesempi', 'sesebig'
    n: string
        Number of processors needed for the job
    mem: string
        Total RAM required: i.e. '64GB'
    time: string
        Time needed for the job: 'Days-HH:MM:SS'
    email: string
        Email where info about execution is sent
    """
    string = '#!/bin/bash\n\n'
    string += '#SBATCH --job-name={}\n'.format(name)
    string += '#SBATCH -p {}\n'.format(p)
    string += '#SBATCH -n {}\n'.format(n)
    string += '#SBATCH --mem {}\n'.format(mem)
    string += '#SBATCH --time={}\n'.format(time)
    string += '#SBATCH --mail-type=BEGIN\n'
    string += '#SBATCH --mail-type=FAIL\n'
    string += '#SBATCH --mail-type=END\n'
    string += '#SBATCH --mail-user={}\n\n'.format(email)
    return string

def runPython(condaEnv, script, args, output=None):
    string = 'source ~/miniconda3/bin/activate {}\n\n'.format(condaEnv)
    string += 'python {}'.format(script)
    for arg in args:
        string += ' {}'.format(arg)
    if(output != None):
        string += ' > {}'.format(output)
    string += '\n'
    return string

def resolveRestart(restart_iter, config_file):
    stage1_iterations = os.path.dirname(restart_iter)
    string = 'LAST=$(ls {}/iter*.nc | sort | tail -n 1)\n'.format(stage1_iterations)
    string += 'sed -i "s#^restart_iter: .*#restart_iter: $LAST#" {}\n\n'.format(config_file)
    return string

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
        d[p] = str(OUT_ROOT / d[p]) + ('/' if d[p].endswith('/') else '')
    d['config_file_name'] = str(PROJECT_ROOT / d['config_file_name'])
    if(d['restart_iter'].lower() != 'none'):
        d['restart_iter'] = str(OUT_ROOT / d['restart_iter'])

    ## generate yml configs
    os.makedirs(d['out_path'], exist_ok=True)
    assert len(os.listdir(d['out_path'])) == 0, '{} contains stuff already'.format(d['out_path'])
    with open('{}config.yml'.format(d['out_path']), 'w') as file:
        yaml.dump(d, file, sort_keys=False)
        print('Wrote {}config.yml'.format(d['out_path']))

    ## Write shell scripts
    name = os.path.basename(d['out_path'][0:-1])
    args = ['{}config.yml'.format(d['out_path'])]
    logfile = '{}at3d.log'.format(d['out_path'])
    hdr = header(name, 'node', '4', '64GB', '10-00:00:00', 'johntl3@illinois.edu')
    body = runPython(conda_env, at3d_script, args, logfile)
    if(d['restart_iter'].endswith('/LAST')):
        body = resolveRestart(d['restart_iter'], args[0]) + body
    shell_file = '{}run_at3d.sh'.format(d['out_path'])
    writeBatch(hdr+body, shell_file)
