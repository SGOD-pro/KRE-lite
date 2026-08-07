import os
import sys
import types
from pathlib import Path

# Ensure current directory is in sys.path
TASK_ROOT = Path(__file__).resolve().parent
if str(TASK_ROOT) not in sys.path:
    sys.path.insert(0, str(TASK_ROOT))

# When deployed with CodeUri: app, the task root contains the modules (api, ingest, query, shared)
# Map 'app' to TASK_ROOT so absolute imports like `from app.xxx import yyy` work seamlessly.
try:
    import app
except ImportError:
    app_module = types.ModuleType("app")
    app_module.__path__ = [str(TASK_ROOT)]
    sys.modules["app"] = app_module

# Setting ENV to "prod" ensures boto3 uses the ambient IAM role
# instead of a local profile, which is correct for AWS Lambda.
os.environ.setdefault("ENV", "prod")

from mangum import Mangum
from app.api.main import app as fastapi_app

# Mangum wrapper for AWS Lambda API Gateway integration
handler = Mangum(fastapi_app)
