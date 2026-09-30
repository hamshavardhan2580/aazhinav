import pickle
import re

# Strategy: patch the pickle bytes before loading
# STACK_GLOBAL requires both items on the stack to be strings.
# A known cause is a custom/renamed class stored incorrectly.
# We scan for the problematic STACK_GLOBAL opcode (0x93)
# and see what's immediately before it.

STACK_GLOBAL = b'\x93'  # opcode 147

with open('ml/final cyclone file.pkl', 'rb') as f:
    data = f.read()

print(f"File size: {len(data)} bytes")

# Find all STACK_GLOBAL positions
positions = [i for i, b in enumerate(data) if b == 0x93]
print(f"Total STACK_GLOBAL opcodes: {len(positions)}")

# Show context around each STACK_GLOBAL
for pos in positions[:30]:
    snippet = data[max(0, pos-60):pos+10]
    print(f"\n--- At offset {pos} ---")
    print(repr(snippet))
