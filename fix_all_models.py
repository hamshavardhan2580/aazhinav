"""
Test all 3 models and fix the seaforecast 'Pipeline' module issue.
The seaforecast model was saved with a custom local class called Pipeline
instead of sklearn.pipeline.Pipeline. We fix this with a custom Unpickler.
"""
import joblib
import warnings
import pickle
import io
import sys
warnings.filterwarnings('ignore')

print("=== Testing all 3 models with joblib ===\n")

# 1. Cyclone (already fixed via protocol 2 re-save)
try:
    m = joblib.load('ml/final cyclone file.pkl')
    print(f"[OK] Cyclone: {type(m).__name__}, n_estimators={m.n_estimators}, classes={m.classes_}")
except Exception as e:
    print(f"[FAIL] Cyclone: {e}")

# 2. Oceanography
try:
    m2 = joblib.load('ml/ocenography final.pkl')
    print(f"[OK] Oceanography: {type(m2).__name__}")
except Exception as e:
    print(f"[FAIL] Oceanography: {e}")

# 3. Seaforecast - has custom 'Pipeline' module reference
print("\n--- Seaforecast fix attempt ---")

# The model was saved with a class like:
#   import Pipeline as Pipeline (custom file)
# We need to intercept and redirect it to sklearn.pipeline.Pipeline

class SeaForecastUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        # Redirect the custom 'Pipeline' module to sklearn's pipeline
        if module == 'Pipeline' or (module == '__main__' and name == 'Pipeline'):
            from sklearn.pipeline import Pipeline
            return Pipeline
        # Redirect any numpy._core references
        if module.startswith('numpy._core'):
            module = module.replace('numpy._core', 'numpy.core')
        return super().find_class(module, name)

try:
    with open('ml/seaforecast final.pkl', 'rb') as f:
        m3 = SeaForecastUnpickler(f).load()
    print(f"[OK] Seaforecast: {type(m3).__name__}")

    # Re-save using joblib so future loads don't need the custom unpickler
    joblib.dump(m3, 'ml/seaforecast final.pkl', compress=0)
    print("Re-saved seaforecast model with joblib.")

    # Verify
    m3_check = joblib.load('ml/seaforecast final.pkl')
    print(f"Verification: {type(m3_check).__name__} OK")

except Exception as e:
    print(f"[FAIL] Seaforecast: {e}")
    import traceback; traceback.print_exc()
