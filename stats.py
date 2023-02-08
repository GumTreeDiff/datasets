#!/usr/bin/env python3
import sys
import pandas as pd
from io import StringIO
import glob
import subprocess

def compute_stats(dataset, extension):
    all_lines = pd.DataFrame()
    for before_file in glob.glob(f"{dataset}/before/**/*." + extension, recursive = True):
        after_file = f"{dataset}/after" + before_file[len(f"{dataset}/before"):]
        ps = subprocess.Popen(('diff', '-u', before_file, after_file), stdout=subprocess.PIPE)
        output = subprocess.check_output(('diffstat', '-t'), stdin=ps.stdout)
        ps.wait()
        csv_string = StringIO(output.decode('UTF-8'))
        line  = pd.read_csv(csv_string, sep=",")
        line["FILENAME"] = before_file
        if all_lines.empty:
            all_lines = line
        else:
            all_lines = pd.concat([all_lines, line], ignore_index=True)
    all_lines.to_csv(f"{dataset}.csv", index=False)

if __name__ == '__main__':
    dataset = sys.argv[1]
    extension = sys.argv[2]
    compute_stats(dataset, extension)