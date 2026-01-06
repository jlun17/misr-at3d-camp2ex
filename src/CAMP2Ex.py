import pandas as pd
import numpy as np

FCDP_BIN_NAMES = [f'cbin{i:02d}_fcdp' for i in range(1, 21)]
FCDP_BINS = np.array([0, 1.5, 3.0, 4.5, 6.0, 8.0, 10.0, 12.0, 14.0, 16.0, 18.0, 21.0, 24.0, 27.0, 30.0, 33.0, 36.0, 39.0, 42.0, 46.0, 50.0])
TDS_BIN_NAMES = [f'cbin{i:02d}_2DS' for i in range(1, 61)]
TDS_BINS = np.append(
    np.append(
        np.append(
            np.append(
                np.arange(5, 205, 10), 
                np.arange(205, 505, 20)
            ), 
            np.arange(505, 1005, 50)
        ), 
        np.arange(1005, 2005, 100)
    ), 
    np.arange(2005, 3010, 200)
)

def make_datetime(df, year_default=2019):
    if 'Day_Of_Year' not in df.columns or 'Time_Start' not in df.columns:
        raise KeyError("Need 'Day_Of_Year' and 'Time_Start' columns in dataframe")
    # build date from Day_Of_Year and Year (if present) or default year
    if 'Year' in df.columns:
        year_series = df['Year'].astype(int)
        origin = pd.to_datetime(year_series.astype(str) + '-01-01')
        dates = origin + pd.to_timedelta(df['Day_Of_Year'].astype(int) - 1, unit='D')
    else:
        origin = pd.Timestamp(f'{year_default}-01-01')
        dates = origin + pd.to_timedelta(df['Day_Of_Year'].astype(int) - 1, unit='D')

    # parse Time_Start: try numeric seconds, otherwise parse as timedelta string (HH:MM:SS)
    try:
        time_delta = pd.to_timedelta(df['Time_Start'].astype(float), unit='s')
    except Exception:
        time_delta = pd.to_timedelta(df['Time_Start'])

    df['datetime'] = dates + time_delta
    return df

def load_bulk(bulk_props_file, nav_file, CP_Type_accept=[1,3]):
    """Parse and merge the CAMP2Ex SPEC bulk properties and the navigation files.

    Parameters
    ----------
    bulk_props_file : str
        File name of the file containing cloud bulk properties. 
        Should be in .itc format.
    nav_file : str
        File name of the file containing the P3 navigation data.
        Should be in .itc format.
    CP_Type_accept : list
        Cloud pass flags to consider cloudy. 
        Cloud pass types (from the CloudBulkProps documentation):
            1 = "Cloud" High Concentration of small particles 
                (WC>0.1g/m3 for scatter probes in 1-50um range), 
            2 = "Precip" High Concentration of HVPS Particles (N>100/s), 
            3 = "Scud" Cloud Flag >0
    
    Returns
    -------
    p3 : pd.Dataframe
        Dataset with the bulk properties merged with the navigation data.
        Volume extinction coefficient is also calculated. Cloud passes are segmented
    """
    bulk_props = pd.read_csv(bulk_props_file, skiprows=37, header=0)#, index_col=0)
    nav = pd.read_csv(nav_file, skiprows=73, header=0)#, index_col=0)
    p3 = pd.merge(nav, bulk_props, on='Time_Start')
    p3 = make_datetime(p3, year_default=2019)
    p3 = p3.set_index('datetime')
    rho_l = 1e6 # g m^-3
    p3['ext_km'] = (3*p3['LWC_gm3']) / (2 * rho_l * 1e-9 * p3['Reff_um']) # km^-1

    p3['cloud_pass'] = -1
    cloud_pass = 1
    inCloud = False
    for row in p3.itertuples():
        if(not inCloud):
            if(row.CP_Type in CP_Type_accept):
                inCloud = True
                p3.at[row.Index, 'cloud_pass'] = cloud_pass
        else:
            if(row.CP_Type not in CP_Type_accept):
                inCloud = False
                cloud_pass += 1
            else:
                p3.at[row.Index, 'cloud_pass'] = cloud_pass
    return p3

def calc_Re(N, bins):
    """Calculate the effective radius of the particle size distribution.
    
    Parameters
    ----------
    N : np.array
        Number concentration normalized by bin width. Array length (nPSDs, nBins).
    bins : np.array
        DIAMETER bin edges. Array with length nBins + 1.

    Returns
    -------
    Re : np.array
        Effective radius of the PSD. Array with length (nPSDs). 
        Units will be the same as bins.
    """
    n = N * np.diff(bins) # number concentration
    bin_center = (bins[:-1] + bins[1:]) / 2
    r = bin_center / 2 # bin center radius
    Re = np.sum(n * r**3, axis=-1) / np.sum(n * r**2, axis=-1)
    return Re

## BROKEN: DO NOT USE UNLESS FIXED
## Need to pay attention to shapes of the arrays.
## The problem is doing the r-Re calculation.
# def calc_Ve(N, bins):
#     Re = calc_Re(N, bins)
#     n = N * np.diff(bins) # number concentration
#     bin_center = (bins[:-1] + bins[1:]) / 2
#     r = bin_center / 2 # bin center radius
#     Ve = np.sum((r-Re)**2 * r**2 * n, axis=-1) / (Re**2 * np.sum(r**2 * n, axis=-1))
#     return Ve

def calc_LWC(N, bins):
    """Calculate the liquid water content assuming spherical particles.
    
    Parameters
    ----------
    N : np.array
        Number concentration [#/liter/um] normalized by bin width. Array length (nPSDs, nBins).
    bins : np.array
        DIAMETER [um] bin edges. Array with length nBins + 1.

    Returns
    -------
    LWC_gm3 : np.array
        Liquid water content [g m^-3]. Array with length (nPSDs).
    """
    rho_l_gm3 = 1e6 # g m^-3
    n_L = N * np.diff(bins)
    n_m3 = n_L * 1000
    bin_center = (bins[:-1] + bins[1:]) / 2
    r_um = bin_center / 2 # bin center radius
    r_m = r_um * 1e-6
    LWC_gm3 = rho_l_gm3 * (4/3) * np.pi * np.sum(n_m3 * r_m**3, axis=-1)
    return LWC_gm3

def calc_N(N, bins):
    """Calculate the total number concentration.
    
    Parameters
    ----------
    N : np.array
        Number concentration normalized by bin width. Array length (nPSDs, nBins).
    bins : np.array
        DIAMETER [um] bin edges. Array with length nBins + 1.

    Returns
    -------
    N_total : np.array
        Total number concentration. Units will be consistent with N.
        Array with length (nPSDs).
    """
    N_total = np.sum(N * np.diff(bins), axis=-1)
    return N_total

def combine_PSD(N1, bins1, N2, bins2, breakpoint):
    """Merge two particle size distributions.
    
    Take left of breakpoint from #1 and right from #2.

    Parameters
    ----------
    N1 : np.array
        Number concentration normalized by bin width. Array length (nPSDs, nBins1).
    bins1 : np.array
        DIAMETER bin edges. Array with length nBins1 + 1.
    N2 : np.array
        Number concentration normalized by bin width. Array length (nPSDs, nBins2).
    bins2 : np.array
        DIAMETER bin edges. Array with length nBins2 + 1.
    breakpoint : float
        diameter to split the size distributions.
    
    Returns
    -------
    N : np.array
        Number concentration normalized by bin width. Array length (nPSDs, nBins).
    bins : np.array
        DIAMETER bin edges. Array with length nBins + 1
    """
    bins = np.append(np.append(bins1[bins1 < breakpoint], breakpoint), bins2[bins2 > breakpoint])
    N = np.append(N1[..., (bins1 < breakpoint)[:-1]], N2[..., (bins2 > breakpoint)[1:]], axis=-1)
    return N, bins

def load_FCDP_2DS(fcdp_file, tds_file, nav_file, breakpoint=40, resample='1s'):
    # Load navigation file
    nav = pd.read_csv(nav_file, skiprows=73, header=0)
    # Load FCDP file, remove columns, and rename columns
    fcdp = pd.read_csv(fcdp_file, skiprows=78, header=0)
    fcdp = fcdp.drop(['conc', 'ext', 'twc'], axis=1)
    fcdp = fcdp.drop(columns=fcdp.filter(regex=r'nbin', axis=1).columns)
    new_names = {}
    for i in range(1, 22):
        new_names[f'cbin{i:02}'] = f'cbin{i:02}_fcdp'
    fcdp = fcdp.rename(columns=new_names)
    # Load 2DS file, remove columns, and rename columns
    tds = pd.read_csv(tds_file, skiprows=284, header=0)
    tds = tds.drop(['conc', 'ext', 'twc', 'meanDiameter', 'meanVolDiam', 'effectiveDiam', 'totaln'], axis=1)
    tds = tds.drop(columns=tds.filter(regex=r'abin', axis=1).columns)
    tds = tds.drop(columns=tds.filter(regex=r'mbin', axis=1).columns)
    tds = tds.drop(columns=tds.filter(regex=r'nbin', axis=1).columns)
    new_names = {}
    for i in range(1, 62):
        new_names[f'cbin{i:02}'] = f'cbin{i:02}_2DS'
    tds = tds.rename(columns=new_names)
    # Merge datasets and create index
    p3 = pd.merge(nav, tds, on='Time_Start', suffixes=['_nav', '_2DS'])
    p3 = pd.merge(p3, fcdp, on='Time_Start', suffixes=['_2DS', '_fcdp'])
    p3 = make_datetime(p3, year_default=2019)
    p3 = p3.set_index('datetime')
    # Perform resampling by averaging the cbins 
    # and summing the ground speed yielding length
    cbins = p3.filter(regex=r'cbin', axis=1)
    p3[cbins.columns] = cbins.resample(resample).mean()
    p3['Length_m'] = p3['Ground_Speed'].resample(resample).sum()
    # Get the number concentrations
    # fcdp_bin_names = [f'cbin{i:02d}_fcdp' for i in range(1, 21)]
    fcdp_N = p3[FCDP_BIN_NAMES].to_numpy()
    # tds_bin_names = [f'cbin{i:02d}_2DS' for i in range(1, 61)]
    tds_N = p3[TDS_BIN_NAMES].to_numpy()
    # Calculate things
    N, bins = combine_PSD(fcdp_N, FCDP_BINS, tds_N, TDS_BINS, breakpoint)
    p3['Re'] = calc_Re(N, bins)
    # p3['Ve'] = calc_Ve(N, bins)
    p3['LWC_gm3'] = calc_LWC(N, bins)
    p3['N_L'] = calc_N(N, bins)
    rho_l = 1e6 # g m^-3
    p3['ext_km'] = (3*p3['LWC_gm3']) / (2 * rho_l * 1e-9 * p3['Re']) # km^-1
    p3['q_vs_cb'] = 1e-3 * np.max(p3['Mixing_Ratio'])
    p3['Virtual_Temp'] = (p3['Static_Air_Temp'] + 273.15) * (1 + 0.61 * p3['Mixing_Ratio'] * 1e-3)
    p3['ALWC_gm3'] = 1000 * (p3['q_vs_cb'] - 1e-3*p3['Mixing_Ratio']) * ((100 * p3['Static_Pressure']) / (287 * p3['Virtual_Temp']))
    p3['pct_ALWC'] = 100*p3['LWC_gm3'] / p3['ALWC_gm3']
    return p3

def VertLinearRegression(p3, x_var='GPS_Altitude', y_var='Re'):
    from sklearn.linear_model import LinearRegression
    """Produce a linear regression on p3 attributes.

    Parameters
    ----------
    p3 : pd.Dataframe
        Dataset with x_var and y_var columns.
    x_var : str
        Column name for the x regression variable.
    y_var : str
        Column name for the y regression variable.

    Returns
    -------
    slope : float
    intercept : float
        Parameters satisfying the linear regression.
        y = m*x + b
    """
    # Create an instance of the LinearRegression model
    m_cloud = LinearRegression()
    # Fit the model to the data
    m_cloud.fit(p3[x_var].to_numpy().reshape(-1, 1), p3[y_var].to_numpy().reshape(-1, 1))
    slope = m_cloud.coef_[0,0]
    intercept = m_cloud.intercept_[0]
    return slope, intercept