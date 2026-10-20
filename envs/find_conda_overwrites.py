"""List lockfile lines for conda packages that were reinstalled over a pip install of the same package.

Usage: <env>/bin/python find_conda_overwrites.py <env prefix> <env>.linux-64.lock.txt

Some envs have two *.dist-info for one package: pip's, and conda's from a later conda install that
overwrote pip's files. The files on disk are conda's (their hashes match conda's RECORD), but
`conda list` and the pip spec still show pip's version. create_envs.sh replays that order:
lockfile, then pip, then a forced reinstall of the lockfile lines printed here.
"""
import base64
import collections
import glob
import hashlib
import os
import sys

prefix, lockfile = sys.argv[1], sys.argv[2]
site_packages = glob.glob(os.path.join(prefix, 'lib', 'python3.*', 'site-packages'))
site_packages = [p for p in site_packages if not os.path.islink(os.path.dirname(p))][0]


def matching_files(dist_info):
    """Fraction of the .py files in RECORD whose sha256 matches the file on disk."""
    ok = total = 0
    for line in open(os.path.join(dist_info, 'RECORD')):
        path, digest = (line.rstrip('\n').split(',') + ['', ''])[:2]
        full = os.path.normpath(os.path.join(site_packages, path))
        if not (digest.startswith('sha256=') and path.endswith('.py') and os.path.exists(full)):
            continue
        total += 1
        actual = base64.urlsafe_b64encode(hashlib.sha256(open(full, 'rb').read()).digest()).rstrip(b'=')
        ok += actual.decode() == digest[7:]
    return ok / total if total else 0.0


dist_infos = collections.defaultdict(list)
for d in glob.glob(os.path.join(site_packages, '*.dist-info')):
    name, version = os.path.basename(d)[:-len('.dist-info')].rsplit('-', 1)
    installer = open(os.path.join(d, 'INSTALLER')).read().strip() if os.path.exists(os.path.join(d, 'INSTALLER')) else ''
    dist_infos[name.lower().replace('_', '-')].append((installer, version, d))

lock_lines = [l.strip() for l in open(lockfile) if l.startswith('http')]
for name, entries in sorted(dist_infos.items()):
    conda = [e for e in entries if e[0] == 'conda']
    pip = [e for e in entries if e[0] == 'pip']
    if not (conda and pip):
        continue
    if matching_files(conda[0][2]) <= matching_files(pip[0][2]):
        continue
    version = conda[0][1]
    candidates = [l for l in lock_lines
                  if any(f'/{n}-{version}-' in l for n in (name, f'{name}-base'))]
    if len(candidates) != 1:
        sys.exit(f'{name} {version}: expected one lockfile line, found {len(candidates)}')
    print(candidates[0])
