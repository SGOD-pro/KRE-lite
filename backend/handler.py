import os
from mangum import Mangum

# Setting ENV to "prod" ensures boto3 uses the ambient IAM role
# instead of a local profile, which is correct for AWS Lambda.
os.environ.setdefault("ENV", "prod")

from app.api.main import app

# Mangum wrapper for AWS Lambda API Gateway integration
handler = Mangum(app)
