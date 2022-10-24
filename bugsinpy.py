#!/usr/bin/env python3

import sys
import os
import glob
import filecmp
import shutil
import re

BEFORE_FOLDER_NAME = "before"
AFTER_FOLDER_NAME = "after"

def main():
    print("Starting checkout")
    print("Projects : ")
    print(projects())
    for project in projects():
        process(project)

def process(project):
    print("Processing " + project)
    bugs = active_bugs(project)
    print(f"Found {str(bugs)} active bugs")
    for bug in range(1, bugs + 1):
        print(f"Checking bug {str(bug)}")

        bug_before_path = f"{out_path}/{BEFORE_FOLDER_NAME}/{project}"/"{str(bug)}"
        bug_after_path = f"{out_path}/{AFTER_FOLDER_NAME}/{project}"/"{str(bug)}"

        if os.path.exists(bug_before_path) or os.path.exists(bug_after_path):
            print(f"Bug {str(bug)} already processed, skipping")
            continue

        code = os.system(f"{b4p_bin}-info -p {project} -i {str(bug)}")
        if code != 0:
            print(f"Bug {str(bug)} is deprecated, skipping")
            continue

        os.system(f"mkdir -p {bug_before_path}")
        os.system(f"mkdir -p {bug_after_path}")
        os.system(f"{b4p_bin}-checkout -p {project} -v 0 -i {str(bug)} -w {tmp_path} /{BEFORE_FOLDER_NAME}")
        os.system(f"{b4p_bin}-checkout -p {project} -v 1 -i {str(bug)} -w {tmp_path} /{AFTER_FOLDER_NAME}")
        changed_files = compare(f"{tmp_path}/{BEFORE_FOLDER_NAME}/{project}", f"{tmp_path}/{AFTER_FOLDER_NAME}/{project}")
        for changed_file in changed_files:
            print(f"Copying {str(changed_file)}")
            before_source = changed_file[1]
            before_dest = f"{bug_before_path}/{changed_file[0].replace('/','_')}"
            shutil.copyfile(before_source, before_dest)
            after_source = changed_file[2]
            after_dest = f"{bug_after_path}/{changed_file[0].replace('/','_')}"
            shutil.copyfile(after_source, after_dest)

def active_bugs(project):
    stream = os.popen(f"{b4p_bin}-info -p {project} | grep 'Number of bugs'")
    output = stream.read()
    match = re.search(r'Number of bugs\s+:\s+(\d+)', output.splitlines()[0])
    return int(match.group(1))

def compare(before, after):
    comparison = []
    for file in glob.glob(f"{BEFORE_FOLDER_NAME}/**/*.py", recursive = True):
        base = file[len(before) + 1:]
        other = f"{after}/{base}"
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