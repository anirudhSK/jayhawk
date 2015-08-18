#! /usr/bin/python

import sys
import subprocess
source_file = sys.argv[1]

# Get all renames from SSA
sp = subprocess.Popen(["domino", source_file, "if_converter,strength_reducer,expr_flattener,expr_propagater,stateful_flanks,ssa"], stdout = subprocess.PIPE, stderr=subprocess.PIPE)
out, err = sp.communicate()
renames = err.splitlines()
rename_dict = dict()
for rename in renames :
  [orig, renamed] = rename.split()
  rename_dict[orig] = renamed

# Get all original fields
sp = subprocess.Popen(["domino", source_file, "gen_pkt_fields"], stdout = subprocess.PIPE, stderr = subprocess.PIPE)
out, err = sp.communicate()
fields = out.splitlines()

# Match up fields
# from spec to implementation
spec_to_impl_mapping = dict()
for field in fields:
  if field in rename_dict:
    spec_to_impl_mapping[field] = rename_dict[field]
  else:
    spec_to_impl_mapping[field] = field

# Print out mapping
print spec_to_impl_mapping

# Compile impl.so and spec.so
sp = subprocess.Popen(["domino", source_file, "if_converter,strength_reducer,expr_flattener,expr_propagater,stateful_flanks,ssa,banzai_binary"], stdout = open("./impl.so", "w"), stderr = open("/dev/null", "w"))
sp = subprocess.Popen(["domino", source_file, "banzai_binary"], stdout = open("./spec.so", "w"), stderr = open("/dev/null", "w"))
