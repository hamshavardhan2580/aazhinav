"""
Fix for final cyclone file.pkl
The STACK_GLOBAL error is caused by sklearn 1.6 → 1.9 module renames.
Specifically, numpy._core.multiarray vs numpy.core.multiarray.
We patch the bytes before loading.
"""
import pickle
import re

with open('ml/final cyclone file.pkl', 'rb') as f:
    data = f.read()

print(f"Original file size: {len(data)} bytes")

# Known sklearn/numpy renames across versions
patches = [
    # numpy internal rename in 1.x
    (b'numpy._core.multiarray', b'numpy.core.multiarray'),
    (b'numpy._core._multiarray_umath', b'numpy.core._multiarray_umath'),
    (b'numpy._core', b'numpy.core'),
    # sklearn internal renames
    (b'sklearn.tree._classes', b'sklearn.tree.tree'),
]

patched_data = data
for old, new in patches:
    count = patched_data.count(old)
    if count:
        # Must match length when using length-prefixed SHORT_BINUNICODE
        # Check if lengths differ — if so we need to adjust length bytes too
        if len(old) == len(new):
            patched_data = patched_data.replace(old, new)
            print(f"Patched {count}x: {old!r} -> {new!r}")
        else:
            # Need to adjust the length prefix byte before each occurrence
            # Format: \x8c<length_byte><string>
            while old in patched_data:
                idx = patched_data.index(old)
                # Rewrite the length byte right before the string
                length_byte_idx = idx - 1
                old_len_byte = patched_data[length_byte_idx:length_byte_idx+1]
                new_len_byte = bytes([len(new)])
                patched_data = (
                    patched_data[:length_byte_idx]
                    + new_len_byte
                    + new
                    + patched_data[idx + len(old):]
                )
                print(f"Patched (len-adjusted): {old!r} -> {new!r}")

with open('ml/final cyclone file_fixed.pkl', 'wb') as f:
    f.write(patched_data)

print(f"Fixed file size: {len(patched_data)} bytes")

# Now try loading
import warnings
warnings.filterwarnings('ignore')

try:
    with open('ml/final cyclone file_fixed.pkl', 'rb') as f:
        model = pickle.load(f)
    print(f"\n✅ SUCCESS! Model loaded: {type(model)}")
except Exception as e:
    print(f"\n❌ Still failing: {e}")
