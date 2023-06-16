"""
Script written by Kristopher Nolte as part of the ESIDA project om the 03.05.2022.
Reads a meta file in form of a csv file and transform the information into
markdown file for each parameter.
"""

import os
import re
import pathlib
import numpy as np
import pandas as pd

#Load the meta csv files and saves temporarily as dataframe
path = pathlib.Path(__file__).parent.resolve()
df_dtype = pd.read_csv(path / "DB_Meta_Sheet - Documentation.csv")
df_dqual = pd.read_csv(path / "DB_Meta_Sheet - Metadata.csv")

def make_md_link(text):
    """ Transform URLs/DOIs in HTML to Markdown links. """
    if pd.isna(text):
        return text

    # links
    # Regex: https://gist.github.com/gruber/8891611
    link = re.compile(r'(?i)\b((?:https?:(?:/{1,3}|[a-z0-9%])|[a-z0-9.\-]+[.](?:com|net|org|edu|gov|mil|aero|asia|biz|cat|coop|info|int|jobs|mobi|museum|name|post|pro|tel|travel|xxx|ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|dd|de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|Ja|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|yu|za|zm|zw)/)(?:[^\s()<>{}\[\]]+|\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\))+(?:\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\)|[^\s`!()\[\]{};:\'".,<>?«»“”‘’])|(?:(?<!@)[a-z0-9]+(?:[.\-][a-z0-9]+)*[.](?:com|net|org|edu|gov|mil|aero|asia|biz|cat|coop|info|int|jobs|mobi|museum|name|post|pro|tel|travel|xxx|ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|dd|de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|Ja|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|yu|za|zm|zw)\b/?(?!@)))')
    text = re.sub(link, r'[\1](\1)', text)

    # DOIs
    # only if cells starts with DOI! to no catch dois in urls that are already links
    # Regex: https://www.crossref.org/blog/dois-and-matching-regular-expressions/
    doi = re.compile(r'^(10.\d{4,9}/[-._;()/:a-zA-Z0-9]+)')
    text = re.sub(doi, r'[\1](https://doi.org/\1)', text)

    return text

df_dtype['Link to Source'] = df_dtype['Link to Source'].apply(make_md_link)

df_dqual['Identifier'] = df_dqual['Identifier'].apply(make_md_link)
df_dqual['Citation']   = df_dqual['Citation'].apply(make_md_link)
df_dqual['Rights']     = df_dqual['Rights'].apply(make_md_link)

def check_for_match():
    """ Checks if both list have identical entry. Raises Error if not else
    returns the list of abbreviations """
    abbrev1 = df_dtype["Abbreviation"]
    abbrev2 = df_dqual["Abbreviation"]

    if len(list(set(abbrev1) - set(abbrev2))) != 0:
        print(list(set(abbrev1) - set(abbrev2)))
        raise ValueError(f'Data type information and data quality information do not match.')
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
    with open(path / f"{abbrev}.md", 'w') as f:
        f.write("## Data type and processing information \n\n")
        f.write(dtype_info)
        f.write("\n\n## Metadata information \n\n")
        f.write(dqual_info)
        f.close()

def main():

    # remove all currently available md files so, deleted
    # data layer md files don't stay in the folder
    for file in os.listdir(path):
        if file.endswith(".md"):
            os.remove(path / file)

    # genreate new files
    abbrev_list = check_for_match()
    for i, abbrev in enumerate(abbrev_list):
        dtype_info, dqual_info = documentation(abbrev, i)
        write_md(abbrev, dtype_info, dqual_info)

if __name__ == "__main__":
    main()
