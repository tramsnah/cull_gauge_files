import sys
import numpy as np
import pandas as pd
import xlsxwriter

#####################################################################################

# Parameters
comment="#" # Ignore lines starting with this char
ftype=2
stype=2
if (ftype==1):
    columns=["Date/Time", "Pressure [bara]", "Temperature [degC]"]               # Names to use in output (v1)
elif (ftype==2):
    columns=["Date", "Time", "Pressure [bara]", "Temperature [degC]"]               # Names to use in output (v1)
else:
    columns=["Date", "Time", "Elapsed", "Pressure [bara]", "Temperature [degC]"] # Names to use in output (v2)
if (stype==1):
    sep='\t'    # Tab separated
else:
    sep=' '     # Whitespace separated

ncull=100   # Base: keep every 100th point
dp_max=0.03 # In addition, keep points more than 'dp_max' bar apart
#utf_codec="utf-8"
utf_codec="ANSI"

# Can specify date/time format (is faster), but can be empty.
# May be necessary if date format is ambiguous (e.g. is "01-02" Jan 2nd or Feb 1st?).
# (see https://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior)
# E.g.:
formatStr = "%d-%b-%y %H:%M:%S"
formatStr = "%d/%m/%y %H:%M:%S" # e.g. 22/06/30 12:30:10
#formatStr = "" # automatic

# Number of header rows at the start
nskiprows=10

def cull_file(filename):
    outfile = filename + "_out.xlsx"

    #####################################################################################

    # Uncomment for testing
    #filename="tiny_test.cli"
    #ncull=3

    #####################################################################################

    # Read the header
    hlines=[]
    f = open(filename, 'r', encoding=utf_codec) # 'r' = read
    for iLine, line in enumerate(f):
        hlines.append(line)
        if (iLine == nskiprows-1):
            break
    f.close()
    print(hlines)
    
    # Read the data
    print("Reading input...")
    df = pd.read_csv(filename, sep=sep, comment=comment, names=columns, header=0, index_col=False,
                     encoding=utf_codec, skiprows=nskiprows)
    print("    read ", filename)

    print(df)
    
    # Get every 100th row
    df["Keep"] = (df.index % ncull == 0)

    # Check pressure differential. Keep points more than dp_max bar apart.
    # First calculate the pressure as an integer in multiples of  dp_max
    df["pi"] = df["Pressure [bara]"]/dp_max
    df["pi"] = df["pi"].astype('int')
    # Then calculate the difference
    df["dp"] = np.abs(df["pi"] - df["pi"].shift(1))
    df["dp2"] = df["dp"].shift(-1)
    df["Keep"] = df["Keep"] | (df["dp"] >= 1) | (df["dp2"] >= 2) # on either side of the divide, if more than 1 step!

    # Do the cull
    df2 = df[df["Keep"]]
    df2 = df2[columns]
    print("Reduced ", len(df), " to ", len(df2), " columns")

    # Concatenate date/time if separate
    print("Combining date+time....")
    if ("Date" in df2.columns):
        assert("Time" in df2.columns)
        df2["Date/Time"] = df2["Date"] + " " + df2["Time"]
        df2 = df2[df2["Time"] != "24:00:00"] # HACK
        df2.drop(["Date","Time"], inplace=True, axis=1)
        df2 = df2[["Date/Time"] + [c for c in df2 if c not in ['Date/Time']]]
        
    # Make sure the dates are really dates
    print("Converting dates....")
    if (formatStr == ""):
        df2["Date/Time"] = pd.to_datetime(df2["Date/Time"], infer_datetime_format= True)
    else:
        df2["Date/Time"] = pd.to_datetime(df2["Date/Time"], format=formatStr)

    # Show the result
    print(df2) # Test

    # Export
    print("Writing output....")
    writer = pd.ExcelWriter(outfile, engine='xlsxwriter')
    df2.to_excel(writer, sheet_name='Sheet1', startrow = nskiprows, index=False)
    workbook  = writer.book
    worksheet = writer.sheets['Sheet1']
    for iLine, text in enumerate(hlines):
        worksheet.write(iLine, 0, text)
    writer.save()
    print("    written ", outfile)
    

if (__name__ == "__main__"):
    nArg = len(sys.argv)
    if (nArg == 1):
        print ("Utility to cull large gauge files to more manageable proportions")
    else:
        for i,fname in enumerate(sys.argv):
            if (i>0):
                print("Processing ", fname)
                cull_file(fname)
        
    a = input("Press Enter")
