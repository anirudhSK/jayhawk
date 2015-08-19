#! /usr/bin/python

import sys
import subprocess
source_file = sys.argv[1]
random_seed = int(sys.argv[2])
pipeline_length = 0

# Get all original fields
sp = subprocess.Popen(["domino", source_file, "gen_pkt_fields"], stdout = subprocess.PIPE, stderr = subprocess.PIPE)
out, err = sp.communicate()
fields = out.splitlines()

# Get all renames from SSA
sp = subprocess.Popen(["domino", source_file, "if_converter,strength_reducer,expr_flattener,expr_propagater,stateful_flanks,ssa"], stdout = subprocess.PIPE, stderr=subprocess.PIPE)
out, err = sp.communicate()
lines = err.splitlines()
rename_dict = dict()
for line in lines:
  if (line.startswith("//")):
    [_, orig, renamed] = line.split()
    rename_dict[orig] = renamed

# Print out source file
file_handle = open(source_file, 'r');
print file_handle.read();

# Get number of pipeline stages
sp = subprocess.Popen(["domino", source_file, "if_converter,strength_reducer,expr_flattener,expr_propagater,stateful_flanks,ssa,partitioning"], stdout = subprocess.PIPE, stderr=subprocess.PIPE)
out, err = sp.communicate()
lines = err.splitlines()
for line in lines:
  if (line.startswith("//") and line.endswith("stages")):
    pipeline_length = int(line.split()[1])
assert(pipeline_length > 0)

# Log dot graph to stderr
print >> sys.stderr, err

# Match up fields
# from spec to implementation
spec_to_impl_mapping = dict()
for field in fields:
  if field in rename_dict:
    spec_to_impl_mapping[field] = rename_dict[field]
  else:
    spec_to_impl_mapping[field] = field

# Generate output fields in impl
output_fields_in_impl = []
for field in spec_to_impl_mapping:
  output_fields_in_impl += [spec_to_impl_mapping[field]];

# Compile spec.so and impl.so
sp = subprocess.Popen(["domino", source_file, "banzai_binary"], stdout = open("./spec.so", "w"), stderr = open("/dev/null", "w"))
sp.communicate()

sp = subprocess.Popen(["domino", source_file, "if_converter,strength_reducer,expr_flattener,expr_propagater,stateful_flanks,ssa,partitioning,banzai_binary"], stdout = open("./impl.so", "w"), stderr = open("/dev/null", "w"))
sp.communicate()

# Run spec.so on banzai
sp = subprocess.Popen(["banzai", "./spec.so", str(random_seed), ",".join(fields), ",".join(fields)], stderr = subprocess.PIPE, stdout = open("/dev/null", "w"));
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

sp = subprocess.Popen(["banzai", "./impl.so", str(random_seed), ",".join(fields), ",".join(output_fields_in_impl)], stderr = subprocess.PIPE, stdout = open("/dev/null", "w"));
out, err = sp.communicate()

# Read err into a hash table, one for each variable in output_fields_in_impl
impl_output = dict();
for field in output_fields_in_impl:
  impl_output[field] = []
records = err.splitlines()
for record in records:
  [name, value] = record.split()
  impl_output[name] += [value]

# One file each for spec and impl output
spec_file_out = open("spec.output", "w")
impl_file_out = open("impl.output", "w")

# Compare spec_output with impl_output
for input_field in fields:
  output_field = spec_to_impl_mapping[input_field]
  spec_file_out.write("\n" + input_field + "\n")
  spec_file_out.write("\n".join([str(x) for x in spec_output[input_field][0:len(spec_output[input_field]) - (pipeline_length - 1)]]));
  impl_file_out.write(output_field)
  impl_file_out.write("\n".join([str(x) for x in impl_output[output_field]]));
  if (spec_output[input_field][0:len(spec_output[input_field]) - (pipeline_length - 1)] != impl_output[output_field]):
    print "input_field ", input_field, "and output_field", output_field, " differ in their output sequence"
    print spec_output[input_field][0:len(spec_output[input_field]) - (pipeline_length - 1)]
    print impl_output[output_field]
