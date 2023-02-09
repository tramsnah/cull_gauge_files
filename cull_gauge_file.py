'''
Import text file with pressure gauge data, and convert to Excel.
Because the files can be very very large, they are reduced in size.

Various heuristics are used for this, as well as for the conversion.
- Header (and preamble) lines are guessed. Column headers are not always correctly
  guessed.
- 24:00:00 time is converted to 00:00:00 the next day (python does not automatically do this).
- Changes are captured (since the import does not know what is what, this may not work 100%).
- Day/Month order (this can only be checked if a transition occurs in the input file, 
  e.g. from 06-30 to 07-01).

Can be run from the command line, with the filename as argument.
'''
import sys
import time

import numpy as np
import pandas as pd                                                

def timeme(method):
    '''
    Decorator to time functions. Uncomment print statement
    to get results.
    '''
    def wrapper(*args, **kw):
        start_time = int(round(time.time() * 1000))
        result = method(*args, **kw)
        end_time = int(round(time.time() * 1000))

        #print(method.__name__, ":", end_time - start_time,'ms')
        return result

    return wrapper

@timeme
def _check_dates_dt(ds):
    '''
    Check that the times in the series
    should be monotonously increasing, with not too large gaps (< 1d),
    Returns number of deviations.
    '''
    if (not np.issubdtype(ds.dtype, np.datetime64)):
        return 0

    # Up
    dis = ds+np.timedelta64(1, "D")
    dis = dis.shift(1)
    dck = (dis >= ds)
    dck[0] = True  # because of the shift
    nwrong = (~dck).sum()

    # Down
    dis = ds-np.timedelta64(1, "D")
    dis = dis.shift(1)
    dck = (dis < ds)
    dck[0] = True  # because of the shift
    nwrong += (~dck).sum()

    return nwrong

@timeme
def _try_day_month_swap(ds):
    '''
    Working from the assumption that the times in the series
    should be monotonously increasing, with not too large gaps (< 1d),
    see if swapping month and day gives a more desirable result.

    Returns modified (or the same) series.

    Does nothing if it is not a datetime series.
    '''
    if (not np.issubdtype(ds.dtype, np.datetime64)):
        return ds

    # Swap day/month. Won't work for all (day# > 12), so fill the gaps
    # with the original
    date_as_str = ds.dt.strftime('%d-%m-%y %H:%M:%S.%f')
    date_inv = pd.to_datetime(date_as_str, format='%m-%d-%y %H:%M:%S.%f', errors='coerce')
    date_inv = date_inv.fillna(ds)
    
    # Determine # of issues in as-is series, and in swapped series
    n1 = _check_dates_dt(ds)
    n2 = _check_dates_dt(date_inv)

    # Return the best
    if (n1 == 0 and n2 == 0):
        print("        Cannot distinguish day/month order, kept it the same")
        return ds
    elif (n1 <= n2):
        print("        Kept day/month the same")
        return ds
    else:
        print("        Swapped day/month")
        return date_inv

@timeme
def _convert_to_dt_robust(ds):
    '''
    Convert strings in series ds to datetime.

    The problem is that sometimes midnight is denotes as 24:00.
    Python cannot handle this, so we need to convert it manually.

    Also check we did not inadvertently swap days/months.

    If the input is already datetime64, only the swap check is done.

    Returns modified series.
    '''
    if (np.issubdtype(ds.dtype, np.datetime64)):
        print("        Column", ds.name, "is already date/time, nothing to do")
        return _try_day_month_swap(ds)
    elif (ds.dtype != object):
        print("        Column", ds.name, " is no date/time string")
        return ds
    
    # Check for occurrences of 24:00:00 (we'll add the 1 day later)
    ds = ds.copy()  # So we can modify
    df24 = ds.str.contains("24:00:00")
    n24 = df24.sum()
    ds[df24] = ds[df24].str.replace("24:00:00", "00:00:00")
    if (n24 > 0):
        print("        Column", ds.name, ": corrected", n24, "occurrences of '24:00:00'")
    
    # Convert (or at least try to)
    df_dt = pd.to_datetime(ds, errors='coerce')
    df_fail = df_dt.isnull()
    nfail = df_fail.sum()
    if (nfail > 0):
        print("        Failed to convert", nfail, "points in column", ds.name,
              "to date/time,\n", ds[df_fail])
        return ds
    
    # Now we add te 1 day
    df_dt[df24] += pd.Timedelta(days=1)

    # On the way out, check we did not inadvertently swap day/month
    return _try_day_month_swap(df_dt)

@timeme
def _check_datetime_cols(df):
    '''
    Convert strings in all columns of dataframe df to datetime (if possible).

    1) The problem is that sometimes midnight is denotes as 24:00.
       Python cannot handle this, so we need to convert it manually.
    2) Sometimes date & time end up in different (subsequent) columns. 
       Merge them if this is the case.
    3) Check day/month order, if data allows, working from the assumption
       that the time series should be monotonous, with small (< 1d) steps.

    Implementation is sub-optimal. Some checks may be done multiple times.

    Returns (modified) df
    '''
    cols = df.columns
    to_drop = None
    c_prev = None
    for i, c in enumerate(cols):
        ds = _convert_to_dt_robust(df[c])
        if (i > 0 and
                np.issubdtype(ds.dtype, np.datetime64) and
                np.issubdtype(df[c_prev].dtype, np.datetime64)):
            print("        Merging date/time columns", c_prev, "and", c)

            # At this stage we (can) assume c_prev is a date column, and c is
            # a time column. Sticking them together as strings, and reparsing
            # is sometimes very slow. Therefore we convert the time column to a
            # timedelta, then add it to the date.
            #eee = df[c_prev][0]
            d0 = pd.to_datetime("00:00:00")
            ds -= d0
            df[c_prev] += ds
            #fff = df[c_prev][0]
            #ggg = df[c][0]

            #date_as_str = df.iloc[:, i-1].dt.strftime('%d-%b-%y')
            #if (np.issubdtype(df[c].dtype, np.datetime64)):
            #    time_as_str = df.iloc[:, i].dt.strftime('%H:%M:%S.%f')
            #else:
            #    time_as_str = df[c]
            #
            #date_time = date_as_str + " " + time_as_str
            #df_dt = _convert_to_dt_robust(date_time)
            #
            #df[c_prev] = df_dt
            to_drop = i # Later drop the now redundant time column
        else:
            df[c] = ds
        c_prev = c
    
    if (to_drop is not None):
        df.drop(cols[to_drop], axis=1, inplace=True)

    return df

@timeme
def _cull_on_column(ds, dn = 1, ncull = 100):
    '''
    Return a bool array to be used for selection, based on column c in dataframe df
    In principle one in ncull is selected.
    If the column is numerical, try to capture changes (both steps and deviations from linear).
    '''
    # Not a float format, just one in ncull
    if (ds.dtype != np.float64):
        keep = (ds.index % ncull == 0)
        print("        1 in 100")
        return keep

    # Put series in a dataframe, so we can manipulate more easily
    df = pd.DataFrame()
    df["data"] = ds
    
    # Base grid
    df["keep"] = (df.index % ncull ==0)
    df["keep"].values[0] = True
    df["keep"].values[-1] = True
    
    # Create cumulative absolute change.
    # Look to changes dn on either side of point
    df["dp"] = np.abs((ds.shift(-dn) - ds.shift(dn))/(2*dn)).fillna(0)
    df["cum_dp"] = df["dp"].cumsum()
    
    # Figure out values at current grid points
    df["cum_keep"] = np.nan
    df.loc[(df["keep"]), "cum_keep"] = df.loc[(df["keep"]), "cum_dp"]
    
    # Work out cumulative change since each grid point
    df["cum_keep"] = df["cum_keep"].fillna(method="ffill")
    df["d_cum_keep"] = df["cum_dp"] - df["cum_keep"]
    
    # Cumulative spacing we will look for
    dcum = df["cum_dp"].values[-1] * ncull/len(df)

    # Constant value column?
    if (dcum == 0):
        return df["keep"]

    print("        delta <", dcum)

    # Add points at this cumulative spacing
    df["i_d_cum_keep"] = (df["d_cum_keep"]/dcum).astype(int)
    df["d_i_d_cum_keep"] = df["i_d_cum_keep"] - df["i_d_cum_keep"].shift()
    df["keep"] |= (df["d_i_d_cum_keep"]>0)
    
    # If count too low, don't end up with nothing
    pmax = min(100*(1-1/len(df)), 99.9)

    # Finally, check curvature. 
    # Copy points at current selection, then interpolate
    for i in range(5): # To avoid eternal loop
        df["p_filt"] = np.nan
        df.loc[(df["keep"]), "p_filt"] = df.loc[(df["keep"]), "data"]
        df["p_filt"] = df["p_filt"].interpolate()

        # Difference between actual and linear interpolation
        df["dp_filt"] = np.abs(ds - df["p_filt"])
        if (df["dp_filt"].max() < dcum):
            break

        # Where is it too large?
        dp2 = np.percentile(df["dp_filt"], pmax)

        # Include those
        df["keep"] |= (df["dp_filt"] > dp2)
    
    # Return the reduced frame
    return df["keep"]

def _cull_data(df, ncull=100):
    '''
    Return a dataframe with reduced # of rows.
    In principle one in ncull rows. is selected.
    For numerical columns, try to capture changes.
    If ncull==1, nothing is done.
    '''
    if (ncull <= 1):
        return df

    keep = None
    for c in df.columns:
        print("    culling column ", c)
        lkeep = _cull_on_column(df[c], ncull=ncull)
        if (keep is None):
            keep = lkeep
        keep |= lkeep
    
    df_culled = df[keep]
    return df_culled

def _read_file(filename, codec, nskiprows, nrows=None, header=None):
    '''
    Helper function to pandas.read_csv, with a (mostly) fixed set of argyments
    '''
    #xtraargs={"delim_whitespace": True}
    xtraargs = {"sep": None}

    df = pd.read_csv(filename, header=header, skiprows=nskiprows, nrows=nrows, 
                encoding=codec, infer_datetime_format=True,
                engine='python', parse_dates=[0], skipinitialspace=True,
                **xtraargs)
    return df

def _find_codec(filename, npeekrows=20):
    '''
    Peek into the file, and try a few codecs to figure the right one.
    '''
    utf_codecs = list()
    utf_codecs.append("utf-8")
    utf_codecs.append("ANSI")
    utf_codecs.append("utf-16")
    utf_codecs.append("utf-32")
    utf_codecs.append("iso8859_15")
    utf_codecs.append("ascii")
    iunicode = 0

    the_codec = None
    while (the_codec is None):
        try:
            with open(filename, 'r', encoding=utf_codecs[iunicode]) as f: # 'r' = read
                for i_line, line in enumerate(f):
                    #print(line, line)
                    if (i_line >= npeekrows):
                        break
            the_codec = utf_codecs[iunicode]        
        except UnicodeDecodeError:
            # try agaun with different unicode
            iunicode += 1

    return the_codec

def _find_number_preamble_lines(filename, utf_codec, nskiprows=20):
    '''
    Peek into the file, figure out how many (unstructured) pre-amble
    lines there are, and how manu column header lines that we can make
    sense of.

    We assume the maximum header size is nskiprows lines.
    So if we skip the first nskiprows lines, we should get a glimpse of
    what the file looks like (in terms of # of columns).
    Count down until we either get a parser error or the number
    of columns changes.
    
    returns nskiprows, nheader
    '''
    ncols = -1
    ctype = None
    nheader = 0
    while (nskiprows>0):
        df = None
        try:
            #print("Testing input...")
            df = _read_file(filename, utf_codec, nskiprows=nskiprows, nrows=10)

            #print(nskiprows,df.shape[1])
            if (ncols == -1):
                ncols = df.shape[1]
            elif (ncols != df.shape[1]):
                #print("Column# change @ ", nskiprows)
                break
            if (ctype is None):
                ctype = df[ncols-1].dtype
            elif (ctype != df[ncols-1].dtype):
                nheader += 1
                #break
                
        except pd.errors.ParserError:
            #print("Parserfailure @ ", nskiprows)
            break

        # Try one line less
        nskiprows -= 1

    # Now we know when things fall apart...
    nskiprows += 1

    return nskiprows, nheader

def cull_gauge_file(filename, ncull=100, do_export=False):
    '''
    Read a gauge export file, and export in Excel format a smaller version, where
    we try to keep the essential variability.
    A number of issues are heuristically solved:
    1) The codec is iteratively determined.
    2) The header of the file is free format. We figure this out by trial 
       and error. 
    3) In these files, sometimes midnight is denotes as 24:00.
       Python cannot handle this, so we need to convert it manually.
    4) Sometimes date & time end up in different (subsequent) columns. 
       Merge them if this is the case.
    5) heuristically check the inferred day/month order is correct, if 
       not, fix.
    The first part of the file is read multiple times (for the codec and the header)
    Note the column headers are not always recognzed.

    If ncull==1, no culling takes place.

    If do_export==True, the (culled) frame is exported with a filename that is
    derived from the input filename.

    A (culled) dataframe is returned.
    '''
    print("Reading input", filename, "...")

    # Find the codec (e.g. pure ASCII, UTF-8, etc.)
    # And the number of header lines.
    print("    Peeking into input", filename, "...")
    utf_codec = _find_codec(filename)
    nskiprows, nheader = _find_number_preamble_lines(filename, utf_codec)
    print("        codec:", utf_codec, " - # preamble lines:", nskiprows)
    
    # Read the header lins
    hlines = list()
    with open(filename, 'r', encoding=utf_codec)  as f: # 'r' = read
        for i_line, line in enumerate(f):
            hlines.append(line)
            if (i_line == nskiprows-1):
                break
    
    # Now read the data for real. First header lines
    print("    Reading full file", filename, "...")
    read_header = None
    if (nheader > 0):
        read_header = list(range(nheader))

    # Then body
    df = _read_file(filename, utf_codec, nskiprows=nskiprows, nrows=None, header=read_header)
                     
    # Sometimes the value 24:00:00 occurs as a time. This needs to be addressed 
    # 'manually', because Python cannot cope with this. In addition, the first 
    # column can be date, or date+time. In the former case, the 2nd column must be
    # time, the space between date and time being misinterpreted as a separator.
    # So if the first column has no time, check the second column.
    print("    Converting dates etc...")
    df = _check_datetime_cols(df)
                         
    # Now do the cull (if requested)
    if (ncull > 1):
        print("    Reducing length..")
        df_culled = _cull_data(df, ncull=ncull)
        print("    Reduced length from", len(df), "to", len(df_culled))
    else:
        df_culled = df
    
    # Export to excel, bot the data itself, and the header lines
    if (do_export):
        print("    Writing output...")
        outfile = filename + "_out.xlsx"
        writer = pd.ExcelWriter(outfile, engine='xlsxwriter')
        df_culled.to_excel(writer, sheet_name='Sheet1', startrow=nskiprows)
        #workbook  = writer.book
        worksheet = writer.sheets['Sheet1']
        for i_line, text in enumerate(hlines):
            worksheet.write(i_line, 0, text)
        writer.save()
        print("    Written ", outfile)
    print()
    
    return df_culled


if (__name__ == "__main__"):
    n_arg = len(sys.argv)
    if (n_arg == 1):
        print("Utility to cull large gauge files to more manageable proportions")
        print("in the form of an Excel file. Usage:")
        print("    python ", sys.argv[0], " <filename>")
        print("The output Excel file is placed in the same folder as the input file")
        
    else:
        for i, fname in enumerate(sys.argv):
            if (i > 0):
                print("Processing ", fname)
                try:
                    cull_gauge_file(fname, ncull=25, do_export=True)
                except Exception as e:
                    # If an exception occurs, continue, so the user gets feedback
                    print("******************************")
                    print("*** Conversion", fname, "failed: ", str(e))
                    print("******************************")
                print()
    
    # Ask for user confirmation so we can use drag & drop to do the conversion.
    # This opens a new command window which would otherwise disappear after completion.    
    a = input("Press Enter")
