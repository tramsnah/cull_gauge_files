import numpy as np
import pandas as pd

#####################################################################################

# Parameters
filename="ONEDYAS_L11-15_TQPR_1755.cli"
# filename="tiny_test.cli" # Test
comment="#"
columns=["Date/Time", "Pressure [bara]", "Temperature [degC]"]
sep='\t'
ncull=100 # Base: every 100th points
#ncull=3 # Test
dp_max=0.01 # Keep points more than 0.01 bar apart
outfile = "out.xlsx"

#####################################################################################

# Read the thing
df = pd.read_csv(filename, sep=sep, comment=comment, names=columns, header=0)

# Get every 100th row
df["Keep"] = (df.index % ncull == 0)

# Check pressure differential. Keep points more than 0.01 bar apart
df["dp"] = np.abs(df["Pressure [bara]"] - df["Pressure [bara]"].shift(1))
df["dp2"] = df["dp"].shift(-1)
df["Keep"] = df["Keep"] | (df["dp"]> dp_max) | (df["dp2"]> dp_max) # on either side of the divide!

# Do the cull
df2 = df[df["Keep"]]
df2 = df2[columns]

# Export
#print(df) # Test
#print(df2) # Test
df2.to_excel(outfile)