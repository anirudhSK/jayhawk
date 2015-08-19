#! /usr/bin/python

import sys
import subprocess
source_file = sys.argv[1]
random_seed = sys.argv[2]

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

# Generate output fields in impl
output_fields_in_impl = []
for field in spec_to_impl_mapping:
  output_fields_in_impl += [spec_to_impl_mapping[field]];

# Compile spec.so and impl.so
sp = subprocess.Popen(["domino", source_file, "banzai_binary"], stdout = open("./spec.so", "w"), stderr = open("/dev/null", "w"))
sp.communicate()

sp = subprocess.Popen(["domino", source_file, "if_converter,strength_reducer,expr_flattener,expr_propagater,stateful_flanks,ssa,banzai_binary"], stdout = open("./impl.so", "w"), stderr = open("/dev/null", "w"))
sp.communicate()

# Run spec.so on banzai
sp = subprocess.Popen(["banzai", "./spec.so", random_seed, ",".join(fields), ",".join(fields)], stderr = subprocess.PIPE, stdout = open("/dev/null", "w"));
out, err = sp.communicate()

# Read err into a hash table, one for each variable in fields
spec_output = dict();
for field in fields:
  spec_output[field] = []
records = err.splitlines()
for record in records:
  [name, value] = record.split()
  spec_output[name] += [value]

# Run impl.so on banzai

sp = subprocess.Popen(["banzai", "./impl.so", random_seed, ",".join(fields), ",".join(output_fields_in_impl)], stderr = subprocess.PIPE, stdout = open("/dev/null", "w"));
out, err = sp.communicate()

# Read err into a hash table, one for each variable in output_fields_in_impl
impl_output = dict();
for field in output_fields_in_impl:
  impl_output[field] = []
records = err.splitlines()
for record in records:
  [name, value] = record.split()
  impl_output[name] += [value]

# Compare spec_output with impl_output
for input_field in fields:
  output_field = spec_to_impl_mapping[input_field]
  print "input_field ", input_field, "output_field", output_field
  print spec_output[input_field]
  print impl_output[output_field]
