import pickle, numpy, warnings, joblib, io
warnings.filterwarnings('ignore')

def fix_pkl_bytes(filepath_in, filepath_out):
    with open(filepath_in, 'rb') as f:
        data = f.read()
    # The corruption: '\x8c\x07Pipeline' (module name 'Pipeline', len=7)
    # should be '\x8c\x10sklearn.pipeline' (len=16 = 0x10)
    old = b'\x8c\x07Pipeline'
    new = b'\x8c\x10sklearn.pipeline'
    count = data.count(old)
    print(f'  Found {count} Pipeline references in {filepath_in}')
    patched = data.replace(old, new)
    with open(filepath_out, 'wb') as f:
        f.write(patched)
    return count

print('=== Fixing ocenography final.pkl ===')
fix_pkl_bytes('ml/ocenography final.pkl', 'ml/ocenography_fixed.pkl')
try:
    m = joblib.load('ml/ocenography_fixed.pkl')
    print('  Loaded type:', type(m).__name__)
    if isinstance(m, dict):
        print('  Keys:', list(m.keys()))
        model = m.get('model', None)
        if model and hasattr(model, 'predict'):
            joblib.dump(model, 'ml/ocenography final.pkl', compress=0)
            print('  Saved fixed oceanography model')
        else:
            joblib.dump(m, 'ml/ocenography final.pkl', compress=0)
    elif hasattr(m, 'predict'):
        joblib.dump(m, 'ml/ocenography final.pkl', compress=0)
        print('  Saved fixed oceanography model (direct)')
except Exception as e:
    print('  FAIL:', e)
    import traceback; traceback.print_exc()

print()
print('=== Fixing seaforecast final (1).pkl ===')
fix_pkl_bytes('ml/seaforecast final (1).pkl', 'ml/seaforecast_fixed.pkl')
try:
    m2 = joblib.load('ml/seaforecast_fixed.pkl')
    print('  Loaded type:', type(m2).__name__)
    if isinstance(m2, dict):
        print('  Keys:', list(m2.keys()))
        model = m2.get('model', None)
        if model and hasattr(model, 'predict'):
            joblib.dump(model, 'ml/seaforecast final.pkl', compress=0)
            print('  Saved fixed seaforecast model')
        else:
            joblib.dump(m2, 'ml/seaforecast final.pkl', compress=0)
    elif hasattr(m2, 'predict'):
        joblib.dump(m2, 'ml/seaforecast final.pkl', compress=0)
        print('  Saved fixed seaforecast model (direct)')
except Exception as e:
    print('  FAIL:', e)
    import traceback; traceback.print_exc()
