#!/usr/bin/env python3

import os
import glob
from pydriller import Repository

from bugsinpy import AFTER_FOLDER_NAME, BEFORE_FOLDER_NAME

BEFORE_FOLDER_NAME = "before"
AFTER_FOLDER_NAME = "after"

GH_JAVA_PROJECTS = { 'apache-commons-cli': 'https://github.com/apache/commons-cli.git', 'google-guava': 'https://github.com/google/guava.git', 'ok-http': 'https://github.com/square/okhttp.git', 'h2': 'https://github.com/h2database/h2database.git', 'zaproxy': 'https://github.com/zaproxy/zaproxy.git', 'jabref': 'https://github.com/JabRef/jabref.git', 'elastic-search': 'https://github.com/elastic/elasticsearch.git', 'killbill': 'https://github.com/killbill/killbill.git', 'drool': 'https://github.com/kiegroup/drools.git', 'signal-server': 'https://github.com/signalapp/Signal-Server.git'}
GH_JAVA_PATH = "gh-java"

GH_PYTHON_PROJECTS = {'black': 'https://github.com/psf/black.git', 'scikit-learn': 'https://github.com/scikit-learn/scikit-learn.git', 'wagtail': 'https://github.com/wagtail/wagtail.git', 'home-assitant': 'https://github.com/wagtail/wagtail.git', 'textual': 'https://github.com/Textualize/textual.git', 'pyxel': 'https://github.com/kitao/pyxel.git', 'django': 'https://github.com/django/django.git', 'keras': 'https://github.com/keras-team/keras.git', 'ansible': 'https://github.com/ansible/ansible.git', 'requests': 'https://github.com/psf/requests.git'}
GH_PYTHON_PATH = "gh-python"

def handle_projects(projects, extension, base_dir, max_files=100):
    print(f"Handle {extension} projects in {base_dir}")
    for project in projects:
        already_performed = len(glob.glob(r'' + base_dir + '/before/' + project + '/**/*' + extension, recursive=True))
        if already_performed >= max_files:
            print(f"Already enough files in project {project}")
            continue
        
        print(f"Starting gathering files in {project}")
        gathered_files = 0
        for commit in Repository(projects[project], only_no_merge=True, only_modifications_with_file_types=[extension]).traverse_commits():
            if gathered_files >= max_files:
                break

            for file in commit.modified_files:
                if gathered_files < max_files and file.filename.endswith(extension) and file.source_code_before != None and file.source_code != None:
                    before_dir = f"{base_dir}/{BEFORE_FOLDER_NAME}/{project}/{commit.hash}"
                    after_dir = f"{base_dir}/{AFTER_FOLDER_NAME}/{project}/{commit.hash}"
                    os.makedirs(before_dir, exist_ok=True)
                    os.makedirs(after_dir, exist_ok=True)
                    clean_file_name = file.filename
                    if not (os.path.exists(f"{before_dir}/{clean_file_name}") or os.path.exists(f"{after_dir}/{clean_file_name}")):
                        with open(f"{before_dir}/{clean_file_name}", 'w') as f:
                            f.write(file.source_code_before)
                        with open(f"{after_dir}/{clean_file_name}", 'w') as f:
                            f.write(file.source_code)
                        gathered_files += 1
            print(f"Gathered {str(gathered_files)} in project {project}")

if __name__ == '__main__':
    handle_projects(GH_JAVA_PROJECTS, ".java", GH_JAVA_PATH)
    handle_projects(GH_PYTHON_PROJECTS, ".py", GH_PYTHON_PATH)
