import os
import tempfile

# Point the app at a throwaway DB before any app module reads config.
os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="floortile-test-")
