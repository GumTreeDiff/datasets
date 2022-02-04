#!/usr/bin/env python3

import sys
import os
import glob
import filecmp
import shutil
import re

def main():
    print("Starting checkout")
    print("Projects : ")
    print(projects())
    for project in projects():
        process(project)

def process(project):
    print("Processing " + project)
    bugs = active_bugs(project)
    print("Found " + str(bugs) + " active bugs")
    for bug in range(1, bugs + 1):
        print("Checking bug " + str(bug))

        bug_buggy_path = out_path + "/buggy/" + project + "/" + str(bug)
        bug_fixed_path = out_path + "/fixed/" + project + "/" + str(bug)

        if os.path.exists(bug_buggy_path) or os.path.exists(bug_fixed_path):
            print("Bug " + str(bug) + " already processed, skipping")
            continue

        code = os.system(b4p_bin + "-info -p " + project + " -i " + str(bug))
        if code != 0:
            print("Bug " + str(bug) + " is deprecated, skipping")
            continue

        os.system("mkdir -p " + bug_buggy_path)
        os.system("mkdir -p " + bug_fixed_path)
        os.system(b4p_bin + "-checkout -p " + project + " -v 0 -i " + str(bug) + " -w " + tmp_path + "/buggy")
        os.system(b4p_bin + "-checkout -p " + project + " -v 1 -i " + str(bug) + " -w " + tmp_path + "/fixed")
        changed_files = compare(tmp_path + "/buggy/" + project, tmp_path + "/fixed/" + project)
        for changed_file in changed_files:
            print("Copying " + str(changed_file))
            buggy_source = changed_file[1]
            buggy_dest = bug_buggy_path + "/" + changed_file[0].replace("/","_")
            shutil.copyfile(buggy_source, buggy_dest)
            fixed_source = changed_file[2]
            fixed_dest = bug_fixed_path + "/" + changed_file[0].replace("/","_")
            shutil.copyfile(fixed_source, fixed_dest)

def active_bugs(project):
    stream = os.popen(b4p_bin + "-info -p " + project + " | grep 'Number of bugs'")
    output = stream.read()
    match = re.search(r'Number of bugs\s+:\s+(\d+)', output.splitlines()[0])
    return int(match.group(1))

def compare(buggy, fixed):
    comparison = []
    for file in glob.glob(buggy + "/**/*.py", recursive = True):
        base = file[len(buggy) + 1:]
        other = fixed + "/" + base
        if os.path.exists(other):
            if filecmp.cmp(file, other) == False:
                comparison.append((base, file, other))
    return comparison

def projects():
    projects = '''sanic
spacy
tornado
youtube-dl
ansible
cookiecutter
httpie
luigi
pandas
scrapy
thefuck
tqdm'''
    return projects.splitlines()

def backup_projects():
    projects = '''PySnooper
black
fastapi
keras
matplotlib
sanic
spacy
tornado
youtube-dl
ansible
cookiecutter
httpie
luigi
pandas
scrapy
thefuck
tqdm'''
    return projects.splitlines()

if __name__ == '__main__':
    b4p_bin = sys.argv[1]
    out_path = sys.argv[2]
    tmp_path = sys.argv[3]
    main()