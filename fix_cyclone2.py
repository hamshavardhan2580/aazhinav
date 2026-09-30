"""
Fix for final cyclone file.pkl
The model was saved with sklearn 1.6.1 using Python 3.11 on a system
where numpy's internal binary representation used protocol 5 binary arrays.
Python 3.13 hits 0x93 bytes inside those binary blobs as STACK_GLOBAL opcodes.

Solution: Use a custom Unpickler that intercepts numpy array reconstruction
and redirects module lookups properly.
"""
import pickle
import io
import warnings
warnings.filterwarnings('ignore')

# Step 1: Try loading with a custom unpickler that handles renamed modules
class FixedUnpickler(pickle.Unpickler):
    MODULE_RENAMES = {
        'numpy._core.multiarray': 'numpy.core.multiarray',
        'numpy._core._multiarray_umath': 'numpy.core._multiarray_umath',
        'numpy._core': 'numpy.core',
    }

    def find_class(self, module, name):
        module = self.MODULE_RENAMES.get(module, module)
        return super().find_class(module, name)

def load_fixed(fileobj):
    return FixedUnpickler(fileobj, encoding='bytes').load()

with open('ml/final cyclone file.pkl', 'rb') as f:
    data = f.read()

# The root cause: this pickle contains nested pickles for numpy arrays
# (via numpy's __reduce__ protocol). These nested pickles contain raw
# binary float64 data where 0x93 appears naturally.
# 
# Python 3.13 changed pickle.loads to be stricter about STACK_GLOBAL.
# The actual fix: we need to replace 'numpy._core' references first,
# then load using the FixedUnpickler.

# Patch known module name changes:
patches = [
    (b'\x8c\x16numpy._core.multiarray', b'\x8c\x16numpy.core.multiarray'),
]

for old, new in patches:
    if old in data:
        data = data.replace(old, new)
        print(f"Patched: {old!r}")

try:
    buf = io.BytesIO(data)
    model = load_fixed(buf)
    print(f"SUCCESS! Loaded: {type(model)}")
    print(f"  n_estimators: {model.n_estimators}")
    print(f"  classes_: {model.classes_}")

    # Re-save with protocol 2 (safe, works across Python versions)
    with open('ml/final cyclone file.pkl', 'wb') as f:
        pickle.dump(model, f, protocol=2)
    print("\nRe-saved with pickle protocol 2 (maximum compatibility).")

    # Quick verification
    with open('ml/final cyclone file.pkl', 'rb') as f:
        m2 = pickle.load(f)
    print(f"Verification OK: {type(m2)}")

except Exception as e:
    print(f"FAILED: {e}")
    import traceback
    traceback.print_exc()
