#!/usr/bin/env python3

import sys
import os
import glob
import filecmp
import shutil

def main():
    print("Starting checkout")
    print("Projects : ")
    print(projects())
    for project in projects():
        process(project)

def process(project):
    print("Processing " + project)
    bugs = active_bugs(project)
    for bug in bugs:
        print("Checking bug " + str(bug))

        bug_buggy_path = out_path + "/buggy/" + project + "/" + str(bug)
        bug_fixed_path = out_path + "/fixed/" + project + "/" + str(bug)

        if os.path.exists(bug_buggy_path) or os.path.exists(bug_fixed_path):
            print("Bug " + str(bug) + " already processed, skipping")
            continue

        code = os.system(d4j_bin + " info -p " + project + " -b " + str(bug))
        if code != 0:
            print("Bug " + str(bug) + " is deprecated, skipping")
            continue

        os.system("mkdir -p " + bug_buggy_path)
        os.system("mkdir -p " + bug_fixed_path)
        os.system(d4j_bin + " checkout -p " + project + " -v" + str(bug) + "b -w " + tmp_path + "/buggy")
        os.system(d4j_bin + " checkout -p " + project + " -v" + str(bug) + "f -w " + tmp_path + "/fixed")
        changed_files = compare(tmp_path + "/buggy", tmp_path + "/fixed")
        for changed_file in changed_files:
            print("Copying " + str(changed_file))
            buggy_source = changed_file[1]
            buggy_dest = bug_buggy_path + "/" + changed_file[0].replace("/","_")
            shutil.copyfile(buggy_source, buggy_dest)
            fixed_source = changed_file[2]
            fixed_dest = bug_fixed_path + "/" + changed_file[0].replace("/","_")
            shutil.copyfile(fixed_source, fixed_dest)
    sys.exit(0)

def active_bugs(project):
    stream = os.popen(d4j_bin + " bids -p " + project)
    output = stream.read()
    return output.splitlines()

def compare(buggy, fixed):
    comparison = []
    for file in glob.glob(buggy + "/**/*.java", recursive = True):
        base = file[len(buggy) + 1:]
        other = fixed + "/" + base

        if os.path.exists(other):
            if filecmp.cmp(file, other) == False:
                comparison.append((base, file, other))
    return comparison

def projects():
    projects = '''Chart
Cli
Closure
Codec
Collections
Compress
Csv
Gson
JacksonCore
JacksonDatabind
JacksonXml
Jsoup
JxPath
Lang
Math
Mockito
Time'''
    return projects.splitlines()

if __name__ == '__main__':
    d4j_bin = sys.argv[1]
    out_path = sys.argv[2]
    tmp_path = sys.argv[3]
    main()