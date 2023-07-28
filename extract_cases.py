#!/usr/bin/env python3

import sys
import pandas as pd
import subprocess

def extract_cases(cases_file, output_folder):
    files = pd.read_csv(cases_file)
    for _, row in files.iterrows():
        output_file = output_folder + "/" + row["before"].replace("/", "_") + "_opt.html"
        print(build_command(row["before"], row["after"]))
        with open(output_file, 'w') as output_file_handle:
            process = subprocess.Popen(build_command(row["before"], row["after"]), stdout=output_file_handle)
            process.wait()
        output_file = output_folder + "/" + row["before"].replace("/", "_") + "_simple.html"
        with open(output_file, 'w') as output_file_handle:
            process = subprocess.Popen(build_command(row["before"], row["after"], matcher="gumtree-simple"), stdout=output_file_handle)
            process.wait()

def build_command(before, after, matcher=None):
    command = ["gumtree", "htmldiff", before, after]
    if matcher != None:
        command += ["-m", matcher]
    if before.startswith("bugsinpy") or before.startswith("gh-python"):
        command += ["-g", "python-treesitter"]
    return command

if __name__ == '__main__':
    cases_file = sys.argv[1]
    output_folder = sys.argv[2]
    print(cases_file)
    print(output_folder)
    extract_cases(cases_file, output_folder)