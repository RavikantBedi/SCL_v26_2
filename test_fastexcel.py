import polars as pl
import pandas as pd

# Create a dummy excel file
df = pd.DataFrame({"IPAdd": ["192.168.1.1"], "MAC Address": ["00:1A:2B:3C:4D:5E"]})
df.to_excel("dummy.xlsx", index=False)

# Read using polars with fastexcel
pl_df = pl.read_excel("dummy.xlsx", engine="fastexcel")
print("Successfully read using fastexcel:")
print(pl_df)
