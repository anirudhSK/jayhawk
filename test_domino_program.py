#! /usr/bin/python

import sys
import subprocess

source_file = sys.argv[1]
sp = subprocess.Popen(["domino", source_file, "if_converter,strength_reducer,expr_flattener,expr_propagater,stateful_flanks,ssa"], stdout = subprocess.PIPE, stderr=subprocess.PIPE)
out, err = sp.communicate()

print "standard output "
print out

print "standard error "
print err
