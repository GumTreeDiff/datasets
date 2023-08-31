# Diff datasets

A collection of diff datasets. It contains:

- [GitHub Java](https://github.com/GumTreeDiff/datasets/tree/main/gh-java) is a Java dataset containing 1000 commits from 10 popular projects.
  [GitHub Python](https://github.com/GumTreeDiff/datasets/tree/main/gh-python) is a Python dataset containing 1000 commits from 10 popular projects.
- [Defects4J](https://github.com/GumTreeDiff/datasets/tree/main/defects4j) is a Java dataset of bug fixes used in the program repair community.
- [BugsInPy](https://github.com/GumTreeDiff/datasets/tree/main/bugsinpy)  is a Python dataset of bug fixes used in the program repair community.

The layout of these datasets is the following: the `before` folders contain the files before modification, and the `after` folders contain the files after. Inside the `before` and `after` folders, there is one folder per commit whose name is the same in the `before` and `after` folders. The [unparsable](https://github.com/GumTreeDiff/datasets/tree/main/unparsable) folder contains the commits from the previous datasets for which we could not parse one of the files.

The Python scripts used to produce the datasets are also provided.
