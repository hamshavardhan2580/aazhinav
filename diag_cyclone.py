"""
Precisely diagnose STACK_GLOBAL error by catching exact position.
"""
import pickle
import pickletools
import io

with open('ml/final cyclone file.pkl', 'rb') as f:
    data = f.read()

# Use pickletools to disassemble and find the exact problematic opcode
buf = io.BytesIO(data)

# Step through opcodes to find the exact STACK_GLOBAL that fails
from pickletools import genops
try:
    for opcode, arg, pos in genops(data):
        pass
    print("pickletools: No error - all opcodes OK")
except Exception as e:
    print(f"pickletools error at: {e}")

# Now try a custom unpickler to catch exactly what module is missing
import sys

class DiagnosticUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        try:
            return super().find_class(module, name)
        except (ModuleNotFoundError, AttributeError) as e:
            print(f"  MISSING: module={module!r}, name={name!r} -> {e}")
            raise

try:
    buf = io.BytesIO(data)
    obj = DiagnosticUnpickler(buf).load()
    print("SUCCESS - model loaded!")
except Exception as e:
    print(f"Final error: {e}")
