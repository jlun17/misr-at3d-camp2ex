import at3d
import numpy as np
import pandas as pd

class HBC:
    def __init__(self, periodic_base, open_base):
        truth_file_p = periodic_base + '_syntheticObs.nc'
        ret_file_p = periodic_base + 'em_optimized.nc'
        control_file_p = periodic_base + '_optimized.nc'

        sensor_true_p, solver_true_p, rte_grid_true_p = at3d.util.load_forward_model(truth_file_p)
        sensor_ret_p, solver_ret_p, rte_grid_ret_p = at3d.util.load_forward_model(ret_file_p)
        sensor_control_p, solver_control_p, rte_grid_control_p = at3d.util.load_forward_model(control_file_p)

        assert rte_grid_true_p.identical(rte_grid_ret_p)
        assert rte_grid_true_p.identical(rte_grid_control_p)

        truth_file_o = open_base + '_syntheticObs.nc'
        ret_file_o = open_base + 'em_optimized.nc'
        control_file_o = open_base + '_optimized.nc'

        sensor_true_o, solver_true_o, rte_grid_true_o = at3d.util.load_forward_model(truth_file_o)
        sensor_ret_o, solver_ret_o, rte_grid_ret_o = at3d.util.load_forward_model(ret_file_o)
        sensor_control_o, solver_control_o, rte_grid_control_o = at3d.util.load_forward_model(control_file_o)

        assert rte_grid_true_o.identical(rte_grid_ret_o)
        assert rte_grid_true_o.identical(rte_grid_control_o)
        assert rte_grid_true_o.dims['x'] % 2 == 1
        assert rte_grid_true_o.dims['y'] % 2 == 1

        assert solver_true_p[0.67].medium['cloud'].extinction.identical(solver_true_o[0.67].medium['cloud'].extinction)

        ext = rte_grid_ret_p.copy(deep=True)
        ext['truth'] = solver_true_p[0.67].medium['cloud'].extinction
        ext['control_open'] = solver_control_o[0.67].medium['cloud'].extinction
        ext['control_periodic'] = solver_control_p[0.67].medium['cloud'].extinction
        ext['open'] = solver_ret_o[0.67].medium['cloud'].extinction
        ext['periodic'] = solver_ret_p[0.67].medium['cloud'].extinction

        self.rte_grid = rte_grid_true_p
        self.solver_true = solver_true_p
        self.solver_control_open = solver_control_o
        self.solver_open = solver_ret_o
        self.solver_control_periodic = solver_control_p
        self.solver_periodic = solver_ret_p
        self.sensor_true = sensor_true_p
        self.sensor_control_open = sensor_control_o
        self.sensor_open = sensor_ret_o
        self.sensor_control_periodic = sensor_control_p
        self.sensor_periodic = sensor_ret_p
        self.ext = ext
        self.open_base = open_base
        self.periodic_base = periodic_base

    def calc_stats(self, comparisons, stat_list):
        """
        Calculate arbitrary statistics and return a pd.DataFrame

        Parameters
        ----------
        comparisons : list of tuples
            Names of the retrievals to be compared stored in the self.ext xr.Dataset.
        stat_list : dict
            Key is the stat_name and value contains another dict with key 'fcn' holding the executable.
            The 'fcn' should take r1 and r2 corresponding to the first and second elements of the comparisons tuple.

        Returns
        -------
        df : pd.DataFrame
            Every statistic computed for each target domain size for each comparison.
        """
        T = []
        r1_name = []
        r2_name = []
        stat_name = []
        stat = []

        ix_center = int((self.ext.dims['x'] - 1) / 2)
        iy_center = int((self.ext.dims['y'] - 1) / 2)
        Trange = min(ix_center, iy_center)
        for i in range(Trange):
            tmp_ext = self.ext.isel(x=slice(ix_center-i, ix_center+i+1), y=slice(iy_center-i, iy_center+i+1))
            tmp_T = np.max(tmp_ext.x.data) - np.min(tmp_ext.x.data)
            for tmp_r1_name, tmp_r2_name in comparisons:
                # if(not ((i == Trange - 1) & (('open' in tmp_r1_name) | ('open' in tmp_r2_name)))):
                r1 = tmp_ext[tmp_r1_name].data
                r2 = tmp_ext[tmp_r2_name].data
                for s in stat_list:
                    fcn_stat = stat_list[s]['fcn']
                    stat_name.append(s)
                    T.append(tmp_T)
                    r1_name.append(tmp_r1_name)
                    r2_name.append(tmp_r2_name)
                    stat.append(fcn_stat(r1,r2))

        df = pd.DataFrame({
            'open_source': [self.open_base] * len(T),
            'periodic_source': [self.periodic_base] * len(T),
            'R': [np.max(self.ext.x.data) - np.min(self.ext.x.data)] * len(T),
            'T': T,
            'r1_name': r1_name,
            'r2_name': r2_name,
            'stat_name': stat_name,
            'stat': stat
        })
        df['R-T'] = df['R'] - df['T']
        return df


GROUP_COLS = ['open_source', 'periodic_source', 'R', 'T', 'R-T', 'stat_name']

def add_adjusted_stats(df: pd.DataFrame):
    """
    For every group of matching (open_source, periodic_source, R, T, R-T, stat_name),
    find experiment/control pairs among rows where r2_name == 'truth':
        r1_name == X              -> experiment
        r1_name == 'control_' + X -> control
    and add a new row:
        r1_name   = experiment's r1_name (X)
        r2_name   = control's r1_name ('control_' + X)
        stat_name = 'adjusted ' + stat_name
        stat      = experiment.stat - control.stat
    Other identifying columns are copied from the experiment row.

    Returns
    -------
    result : pd.DataFrame
        Original df with new adjusted rows appended.
    report : list[str]
        Collected warning messages (missing pairs, duplicates, etc.)
    """
    report = []

    truth_mask = df['r2_name'] == 'truth'
    truth_df = df[truth_mask].copy()

    def base_name(name):
        return name[len('control_'):] if name.startswith('control_') else name

    truth_df['_base'] = truth_df['r1_name'].apply(base_name)
    truth_df['_is_control'] = truth_df['r1_name'].str.startswith('control_')

    new_rows = []

    for key, group in truth_df.groupby(GROUP_COLS + ['_base'], dropna=False):
        exp_rows = group[~group['_is_control']]
        ctrl_rows = group[group['_is_control']]

        if len(exp_rows) == 0 and len(ctrl_rows) == 0:
            continue
        if len(exp_rows) == 0:
            report.append(
                f"No experiment row found for group {key} "
                f"(control r1_name='{ctrl_rows.iloc[0]['r1_name']}'). Skipping."
            )
            continue
        if len(ctrl_rows) == 0:
            report.append(
                f"No control row found for group {key} "
                f"(experiment r1_name='{exp_rows.iloc[0]['r1_name']}'). Skipping."
            )
            continue
        if len(exp_rows) > 1 or len(ctrl_rows) > 1:
            report.append(
                f"Multiple experiment/control rows found for group {key}; "
                f"expected exactly one of each. Using the first of each."
            )

        exp_row = exp_rows.iloc[0]
        ctrl_row = ctrl_rows.iloc[0]

        new_row = exp_row.drop(labels=['_base', '_is_control']).copy()
        new_row['r1_name'] = exp_row['r1_name']
        new_row['r2_name'] = ctrl_row['r1_name']
        new_row['stat_name'] = 'adjusted ' + exp_row['stat_name']
        new_row['stat'] = exp_row['stat'] - ctrl_row['stat']

        new_rows.append(new_row)

    if new_rows:
        new_df = pd.DataFrame(new_rows)
        result = pd.concat([df, new_df], ignore_index=True)
    else:
        result = df.copy()

    return result, report