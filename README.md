# Cited-or-Silent 🤫

An enterprise-grade hybrid RAG application powered by **Amazon Bedrock (Titan & Nova)**, **Qdrant**, and **MongoDB**. It enforces strict factual grounding by actively refusing to hallucinate answers that aren't backed by the provided PDFs.

## Architecture 🏛️

- **Frontend**: React + Vite + Zustand + Shadcn UI (TailwindCSS)
- **Backend**: FastAPI (Python 3.11)
- **Storage**: AWS S3 (Raw Documents) + MongoDB Atlas (Chunks & Metadata)
- **Vector Database**: Qdrant Cloud
- **AI Models**: Amazon Bedrock Titan Text Embeddings v2 & Amazon Nova Pro v1
- **Deployment**: AWS SAM Lambda (Backend) & Vercel (Frontend)

---

## 🚀 Getting Started Locally

### 1. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
cp .env.example .env
```
Fill out the `.env` file with your AWS credentials (or ensure you have the `aws` CLI configured with a default profile), MongoDB URI, and Qdrant endpoint/key.

Start the API:
```bash
python -m uvicorn app.api.main:app --host 0.0.0.0 --port 8000
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Navigate to `http://localhost:5173`.

---

## 🧪 Testing

### Backend Unit & Integration Tests (Pytest)
```bash
cd backend
pytest -v
```

### Frontend E2E Tests (Playwright)
Ensure the backend is running on port 8000 and the frontend on port 5173.
```bash
cd frontend
npx playwright install
npx playwright test
```

---

## ☁️ Continuous Deployment (CI/CD)

The project includes GitHub Actions workflows for automated testing and deployment.

### Backend (AWS SAM)
The backend is packaged using Mangum and deployed to AWS Lambda via SAM. 
To deploy manually:
```bash
sam build
sam deploy --guided
```
**GitHub Actions**: Ensure `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and `S3_SAM_DEPLOY_BUCKET` are set as repository secrets to enable automated deployment via `.github/workflows/deploy.yml`.

### Frontend (Vercel)
The frontend is deployed to Vercel.
**GitHub Actions**: Set `VERCEL_TOKEN`, `VERCEL_ORG_ID`, and `VERCEL_PROJECT_ID` as repository secrets for automated deployment.
