"""
Deep binary scan: find the exact offset where STACK_GLOBAL (0x93)
is being hit with a non-string item on the stack.

Strategy: step through the pickle using the low-level opcodes
and simulate the stack to find where a non-str item precedes 0x93.
"""
import pickle
import struct
import io

with open('ml/final cyclone file.pkl', 'rb') as f:
    data = f.read()

# The error: "STACK_GLOBAL requires str" means
# during execution of opcode 0x93 (STACK_GLOBAL),
# the top two items on the stack are NOT both strings.
# This happens when a numpy-embedded nested pickle is being re-played.

# Scan for all occurrences of 0x93 preceded by content that looks like
# it might be inside a raw numpy binary blob (not a proper short string encoding).
# A valid STACK_GLOBAL sequence looks like:
#   \x8c<len><module>\x8c<len><name>\x93
# An invalid one will have 0x93 inside binary data.

print("Scanning for 0x93 byte not preceded by short unicode strings...")
print("Format of valid STACK_GLOBAL: \\x8c<LEN><MODULE_NAME>\\x94\\x8c<LEN><CLASS_NAME>\\x94\\x93")

issues = []
i = 0
while i < len(data):
    if data[i] == 0x93:
        # Look back to see if this looks like a valid STACK_GLOBAL
        # A valid one: 0x8c NN [NN bytes] 0x94 0x8c MM [MM bytes] 0x94 0x93
        # Let's check if the byte preceding this is 0x94 (BINPUT/MEMO push marker)
        prev_byte = data[i-1] if i > 0 else None
        # In valid sequences, the byte just before 0x93 is typically 0x94
        if prev_byte not in (0x94, None):
            context_before = data[max(0,i-30):i]
            context_after = data[i:i+10]
            issues.append((i, prev_byte, context_before, context_after))
    i += 1

print(f"\nFound {len(issues)} suspicious 0x93 occurrences with unexpected preceding byte")
for pos, prev, before, after in issues[:10]:
    print(f"\n  Offset {pos}: prev=0x{prev:02x}")
    print(f"  Before: {before!r}")
    print(f"  After:  {after!r}")
