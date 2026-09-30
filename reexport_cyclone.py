"""
Load cyclone model with sklearn 1.6.1 and re-export with protocol 4
so it will be stable across sklearn versions going forward.
"""
import pickle
import warnings
warnings.filterwarnings('ignore')

# Load original
print("Loading original cyclone model with sklearn 1.6.1...")
try:
    with open('ml/final cyclone file.pkl', 'rb') as f:
        model = pickle.load(f)
    print(f"SUCCESS! Model type: {type(model)}")
    print(f"  n_estimators: {model.n_estimators}")
    print(f"  classes: {model.classes_}")

    # Re-save in protocol 4 (compatible with Python 3.8+)
    with open('ml/final cyclone file.pkl', 'wb') as f:
        pickle.dump(model, f, protocol=4)
    print("\nRe-saved as protocol 4 pickle.")

    # Verify the re-saved file
    with open('ml/final cyclone file.pkl', 'rb') as f:
        model2 = pickle.load(f)
    print(f"Verification load: {type(model2)} - OK")

except Exception as e:
    print(f"FAILED: {e}")
