"""
Try loading the cyclone model using joblib which sklearn recommends.
Also try with numpy's pickle compatibility shim.
"""
import warnings
warnings.filterwarnings('ignore')

# Approach 1: joblib (sklearn's recommended serialization)
print("=== Approach 1: joblib.load ===")
try:
    import joblib
    model = joblib.load('ml/final cyclone file.pkl')
    print(f"SUCCESS! Model: {type(model)}")
    print(f"  n_estimators: {model.n_estimators}")
    print(f"  classes_: {model.classes_}")

    # Re-save
    import pickle
    with open('ml/final cyclone file.pkl', 'wb') as f:
        pickle.dump(model, f, protocol=2)
    print("Re-saved with protocol 2.")

    with open('ml/final cyclone file.pkl', 'rb') as f:
        m2 = pickle.load(f)
    print(f"Verification: {type(m2)} OK")

except Exception as e:
    print(f"FAILED: {e}")
    import traceback; traceback.print_exc()

print()

# Approach 2: numpy pickle compat
print("=== Approach 2: numpy.load ===")
try:
    import numpy as np
    model = np.load('ml/final cyclone file.pkl', allow_pickle=True)
    print(f"SUCCESS! {model}")
except Exception as e:
    print(f"FAILED: {e}")
