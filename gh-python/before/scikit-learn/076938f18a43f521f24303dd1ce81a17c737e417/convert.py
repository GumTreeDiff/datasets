#! /usr/bin/env python
# Last Change: Sun Jul 01 07:00 PM 2007 J

# This script generates a python file from the txt data
import time
import csv

dataname = 'iris.data'
f = open(dataname, 'r')
a = csv.reader(f)
el = [i for i in a]
# Remove last value corresponding to empty line in data file
el.remove(el[-1])
assert len(el) == 150

sl = [i[0] for i in el]
sw = [i[1] for i in el]
pl = [i[2] for i in el]
pw = [i[3] for i in el]
cl = [i[4] for i in el]

dcl = dict([(i, []) for i in cl])
for i in range(len(cl)):
    dcl[cl[i]].append(i)

# Write the data in oldfaitful.py
a = open("iris.py", "w")
a.write('# Autogenerated by convert.py at %s\n\n' % 
        time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime()))

def dump_var(var, varname):
    a.write(varname + " = ")
    a.write(str(var))
    a.write("\n\n")

dump_var(sl, 'SL')
dump_var(sw, 'SW')
dump_var(pl, 'PL')
dump_var(pw, 'PW')
dump_var(dcl, 'CLI')
