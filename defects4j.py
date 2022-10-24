#!/usr/bin/env python3

import sys
import os
import glob
import filecmp
import shutil

BEFORE_FOLDER_NAME = "before"
AFTER_FOLDER_NAME = "after"

def main():
    print("Starting checkout")
    print("Projects : ")
    print(projects())
    for project in projects():
        process(project)

def process(project):
    print(f"Processing {project}")
    bugs = active_bugs(project)
    for bug in bugs:
        print(f"Checking bug {str(bug)}")

        bug_before_path = f"{out_path}/{BEFORE_FOLDER_NAME}/{project}/{str(bug)}"
        bug_after_path = f"{out_path}/{AFTER_FOLDER_NAME}/{project}/{str(bug)}"

        if os.path.exists(bug_before_path) or os.path.exists(bug_after_path):
            print(f"Bug {str(bug)} already processed, skipping")
            continue

        code = os.system(f"{d4j_bin} info -p {project} -b {str(bug)}")
        if code != 0:
            print(f"Bug {str(bug)} is deprecated, skipping")
            continue

        os.system(f"mkdir -p {bug_before_path}")
        os.system(f"mkdir -p {bug_after_path}")
        os.system(f"{d4j_bin} checkout -p {project} -v{str(bug)}b -w {tmp_path}/{BEFORE_FOLDER_NAME}")
        os.system(f"{d4j_bin} checkout -p {project} -v{str(bug)}f -w {tmp_path}/{AFTER_FOLDER_NAME}")
        changed_files = compare(f"{tmp_path}/{BEFORE_FOLDER_NAME}", f"{tmp_path}/{AFTER_FOLDER_NAME}")
        for changed_file in changed_files:
            print(f"Copying {str(changed_file)}")
            before_source = changed_file[1]
            before_dest = f"{bug_before_path}/{changed_file[0].replace('/','_')}"
            shutil.copyfile(before_source, before_dest)
            after_source = changed_file[2]
            after_dest = f"{bug_after_path}/{changed_file[0].replace('/','_')}"
            shutil.copyfile(after_source, after_dest)
    sys.exit(0)

def active_bugs(project):
    stream = os.popen(f"{d4j_bin} bids -p {project}")
    output = stream.read()
    return output.splitlines()

def compare(before, after):
    comparison = []
    for file in glob.glob(f"{before}/**/*.java", recursive = True):
        base = file[len(before) + 1:]
        other = f"{after}/{base}"

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