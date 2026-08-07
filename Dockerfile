FROM public.ecr.aws/lambda/python:3.12

# Copy requirements from backend directory
COPY backend/requirements.txt ${LAMBDA_TASK_ROOT}/requirements.txt
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt

# Copy backend/app and handler
COPY backend/app ${LAMBDA_TASK_ROOT}/app
COPY backend/handler.py ${LAMBDA_TASK_ROOT}/handler.py

# Set the CMD to the mangum handler for Lambda
CMD ["handler.handler"]
