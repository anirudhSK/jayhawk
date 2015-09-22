#! /usr/bin/python

# Imports
import sys
import subprocess

# Recursively chase renames
# In the recursive case, we simply add the result because the function already
# returns a list. In the non-recursive base case, we need a [var] to make it a list
def get_final_renames(originals, rename_dict):
  renames = []
  for var in originals:
    if (var not in rename_dict):
      renames += [var]
    else:
      renames += get_final_renames(rename_dict[var], rename_dict)
  return renames

# Program wrapper
# Takes a command line of program arguements,
# executes it, and prints something out whether it succeeds or fails
def program_wrapper(program, t_stdout = subprocess.PIPE, t_stderr = subprocess.PIPE):
  sp = subprocess.Popen(program, stdout = t_stdout, stderr = t_stderr)
  out, err = sp.communicate()
  if (sp.returncode != 0):
    print " ".join(program), " failed (non-zero return code) with stdout:"
    print out
    print "stderr:"
    print err
    sys.exit(sp.returncode)
  else :
    print " ".join(program), " completed with return code of zero"
    return (out, err)

# Command line arguments
source_file = sys.argv[1]
random_seed = int(sys.argv[2])
pipeline_length = 0
num_ticks = int(sys.argv[3])

# Get all original fields from spec/source
out, err = program_wrapper(["domino", source_file, "gen_used_fields"])
original_fields = out.splitlines()

# List out all passes
frontend_passes = "int_type_checker,desugar_comp_asgn,if_converter,algebra_simplify,array_validator,stateful_flanks,ssa";
midend_passes   = "expr_propagater" # Move things that require SSA here like dead code elimination, CSE, constant propagation
backend_passes  = "expr_flattener,cse,partitioning" # Move the pass that checks if the atoms can be squeezed into the hardware

# Get all renames from SSA
# All lines in stderr start with //
# to ensure it's treated as a comment for .dot output
out, err = program_wrapper(["domino", source_file, frontend_passes + "," + midend_passes])
lines = err.splitlines()
rename_dict = dict()
for line in lines:
  if (line.startswith("//")):
    [_, orig, renamed] = line.split()
    if (orig in rename_dict):
      rename_dict[orig] += [renamed]
    else:
      rename_dict[orig] = [renamed]

# Get surviving packet fields are CSE
out,  err = program_wrapper(["domino", source_file, frontend_passes + "," + midend_passes + "," + "expr_flattener,cse,gen_used_fields"])
surviving_fields = out.splitlines()
for orig in rename_dict:
  # Remove any field from rename_dict,
  # which isn't in surviving_fields
  fields_to_remove = []
  for field in rename_dict[orig]:
    if field not in surviving_fields:
      fields_to_remove += [field]
  for field in fields_to_remove:
    rename_dict[orig].remove(field)

# Print out source file to stdout
print open(source_file, 'r').read();

# Get number of pipeline stages, (written by partitioning pass)
out, err = program_wrapper(["domino", source_file, frontend_passes + "," + midend_passes + "," + backend_passes])
lines = err.splitlines()
for line in lines:
  if (line.startswith("//") and line.endswith("stages")):
    pipeline_length = int(line.split()[1])
assert(pipeline_length > 0)
assert(num_ticks > pipeline_length)

# Print out dot graph to stderr
print >> sys.stderr, err

# Match up fields from spec to implementation
spec_to_impl_mapping = dict()
for field in original_fields:
  spec_to_impl_mapping[field] = get_final_renames([field], rename_dict);

# Generate output fields in impl
# (the ones we need to check for),
# based on spec_to_impl_mapping
output_fields_in_impl = []
for field in spec_to_impl_mapping:
  output_fields_in_impl += spec_to_impl_mapping[field];

# Compile to spec.so and to impl.so
program_wrapper(["domino", source_file, "banzai_binary"],
                t_stdout = open("./spec.so", "w"),
                t_stderr = subprocess.PIPE)
program_wrapper(["domino", source_file, frontend_passes + "," + midend_passes + "," + backend_passes + ",banzai_binary"],
                t_stdout = open("./impl.so", "w"),
                t_stderr = subprocess.PIPE)

# Run spec.so on banzai
out, err = program_wrapper(["banzai", "./spec.so", str(random_seed), ",".join(original_fields), ",".join(original_fields), str(num_ticks)]);

# Read err into a hash table, one for each variable in fields
spec_output = dict();
for field in original_fields:
  spec_output[field] = []
records = err.splitlines()
for record in records:
  [name, value] = record.split()
  spec_output[name] += [value]

# Run impl.so on banzai
out,err = program_wrapper(["banzai", "./impl.so", str(random_seed), ",".join(original_fields), ",".join(output_fields_in_impl), str(num_ticks)]);

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
for input_field in original_fields:
  # Get equivalent fields
  output_fields = spec_to_impl_mapping[input_field]
  for output_field in output_fields:
    spec_file_out.write("\n" + input_field + "\n")
    spec_file_out.write("\n".join([str(x) for x in spec_output[input_field][0:len(spec_output[input_field]) - (pipeline_length - 1)]]));
    impl_file_out.write("\n" + output_field + "\n")
    impl_file_out.write("\n".join([str(x) for x in impl_output[output_field]]));
    if (spec_output[input_field][0:len(spec_output[input_field]) - (pipeline_length - 1)] != impl_output[output_field]):
      print "ERROR!!!: input_field ", input_field, "and output_field", output_field, " differ in their output sequence"
      sys.exit(1)
print "spec and implementation match"
