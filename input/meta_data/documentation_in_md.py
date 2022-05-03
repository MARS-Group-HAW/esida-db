"""
Script written by Kristopher Nolte as part of the ESIDA project om the 03.05.2022.
Reads a meta file in form of a csv file and transform the information into
markdown file for each parameter.
"""

import numpy as np
import pandas as pd


#Load the meta csv files and saves temporarily as dataframe
df_dtype = pd.read_csv("DB_Meta_Sheet - Data Type & Processing.csv")
df_dqual = pd.read_csv("DB_Meta_Sheet - Data Quality.csv")

def check_for_match():
    """ Checks if both list have identical entry. Raises Error if not else
    returns the list of abbreviations """
    abbrev1 = df_dtype["Abbreviation"]
    abbrev2 = df_dqual["Abbreviation"]
    if len(list(set(abbrev1) - set(abbrev2))) != 0:
        raise ValueError('Data type information and data quality information do not match!')
    else:
        return abbrev1

def documentation (abbrev, i):
    """ Reads information from the description in the meta dataframe, transforms
    it into a markdown string """
    dtype_info = df_dtype.loc[df_dtype["Abbreviation"] == abbrev].T.rename(columns={i: "Description"}).dropna().to_markdown()
    dqual_info = df_dqual.loc[df_dqual["Abbreviation"] == abbrev].T.rename(columns={i: "Description"}).dropna().to_markdown()
    return dtype_info, dqual_info

def write_md(abbrev, dtype_info, dqual_info):
    """ writes the markdown strings into a markdownfile and saves it """
    with open(".".join([abbrev, "md"]), 'w') as f:
        f.write("## Data type and processing information \n\n")
        f.write(dtype_info)
        f.write("\n\n## Data quality information \n\n")
        f.write(dqual_info)
        f.close()

def main():
    abbrev_list = check_for_match()
    for i, abbrev in enumerate(abbrev_list):
        dtype_info, dqual_info = documentation(abbrev, i)
        write_md(abbrev, dtype_info, dqual_info)

if __name__ == "__main__":
    main()



