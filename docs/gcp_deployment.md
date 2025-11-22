# Google Cloud Platform deployment guide (React + FastAPI + Streamlit)

This recipe walks through deploying the FastAPI API, optional Streamlit dashboard, and React UI on Google Cloud Platform.

## Prerequisites
- `gcloud` CLI initialized with your project (`gcloud init`).
- Project-level billing enabled.
- Docker locally (or use Cloud Build).
- Domain managed in Cloud DNS (or another registrar you can point at Cloud Run/Cloud CDN).

Enable required services:
```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  compute.googleapis.com
```

## 1) Build and push container images to Artifact Registry
Create an Artifact Registry repository (region can be any GCP region you plan to run Cloud Run in):
```bash
export REGION=us-central1
export PROJECT_ID=$(gcloud config get-value project)
export API_REPO=ev-api
export STREAMLIT_REPO=ev-streamlit

gcloud artifacts repositories create $API_REPO \
  --repository-format=docker \
  --location=$REGION \
  --description="EV FastAPI image"

gcloud artifacts repositories create $STREAMLIT_REPO \
  --repository-format=docker \
  --location=$REGION \
  --description="EV Streamlit image"
```

Authenticate Docker to push:
```bash
gcloud auth configure-docker $REGION-docker.pkg.dev
```

Build and push the images using the provided Dockerfiles:
```bash
# FastAPI
API_IMG="$REGION-docker.pkg.dev/$PROJECT_ID/$API_REPO:latest"
docker build -f deploy/aws/Dockerfile.api -t $API_IMG .
docker push $API_IMG

# Streamlit (optional)
STREAMLIT_IMG="$REGION-docker.pkg.dev/$PROJECT_ID/$STREAMLIT_REPO:latest"
docker build -f deploy/aws/Dockerfile.streamlit -t $STREAMLIT_IMG .
docker push $STREAMLIT_IMG
```

> Prefer Cloud Build? Submit with the root `cloudbuild.yaml` so the builder can find the Dockerfiles under `deploy/aws/`:
> ```bash
> gcloud builds submit --config cloudbuild.yaml \
>   --substitutions=_API_IMAGE="$API_IMG",_STREAMLIT_IMAGE="$STREAMLIT_IMG" \
>   .
> ```

## 2) Deploy FastAPI to Cloud Run
Deploy the API container on port 8000 and allow HTTPS ingress:
```bash
export API_SERVICE=ev-api

gcloud run deploy $API_SERVICE \
  --image $API_IMG \
  --platform managed \
  --region $REGION \
  --port 8000 \
  --allow-unauthenticated \
  --set-env-vars "ALLOWED_ORIGINS=*" \
  --cpu 1 --memory 512Mi
```

Notes:
- Use `--no-allow-unauthenticated` plus IAM or IAP if you need a private API.
- Keep the `/ev/*` path prefix when routing from the frontend.
- Health check endpoints: `/` or `/docs`.

## 3) Deploy Streamlit to Cloud Run (optional)
Run Streamlit on port 8501 and expose via a separate URL or behind auth:
```bash
export STREAMLIT_SERVICE=ev-streamlit

gcloud run deploy $STREAMLIT_SERVICE \
  --image $STREAMLIT_IMG \
  --platform managed \
  --region $REGION \
  --port 8501 \
  --allow-unauthenticated \
  --set-env-vars "STREAMLIT_SERVER_BASEURLPATH=/" \
  --cpu 1 --memory 1Gi
```

Tips:
- To place Streamlit behind authentication, deploy with `--no-allow-unauthenticated` and grant a small set of identities, or front it with Identity-Aware Proxy.
- If you want Streamlit under a sub-path, set `STREAMLIT_SERVER_BASEURLPATH` accordingly and adjust your load balancer rule to strip the prefix.

## 4) Host the React build
Two common options:
- **Cloud Storage + Cloud CDN**: build locally (`npm run build`), upload the static files, then front with a Cloud CDN-enabled HTTPS Load Balancer.
  ```bash
  npm run build
  gsutil mb -p $PROJECT_ID -c Standard -l $REGION gs://$PROJECT_ID-react
  gsutil cp -r build/* gs://$PROJECT_ID-react
  # Optionally set cache headers and enable Cloud CDN via the HTTPS Load Balancer UI/Terraform.
  ```
- **Firebase Hosting**: run `firebase init hosting`, deploy with `firebase deploy --only hosting`, and configure the API base URL in your environment.

Set the React app’s API base URL to the Cloud Run URL for FastAPI (or to your custom domain once configured).

## 5) Custom domains and HTTPS
- **Cloud Run mappings**: map `api.yourdomain.com` to the FastAPI service and `dash.yourdomain.com` to Streamlit (if public). The mapping process automatically provisions managed SSL certificates.
- **Global HTTPS Load Balancer (serverless NEG)**: create a load balancer with two backend services pointing to Cloud Run services, add path/host rules (`/ev/*` to FastAPI, host rule for Streamlit), and attach Cloud CDN if desired. Point DNS records to the load balancer’s IP.
- **React static hosting**: use the HTTPS Load Balancer + Cloud CDN for the Cloud Storage bucket or rely on Firebase-managed certs for Firebase Hosting.

## 6) Security and networking
- Restrict invocation with Cloud Run IAM or IAP; add Cloud Armor for WAF/rate limits.
- Keep secrets in Secret Manager and surface them via environment variables if needed.
- Use VPC connectors only if the services must reach private resources; otherwise keep them fully serverless for simplicity.

## 7) Observability and scaling
- Cloud Run autoscaling is enabled by default; tune `--max-instances` and concurrency as needed.
- Logs stream to Cloud Logging; add Cloud Trace/Profiler if you need deeper insight.
- Monitor latency and error rates in Cloud Monitoring and configure alerts for the API endpoints.

## 8) Validation
- Open the Cloud Run URL for FastAPI (or the custom domain) and confirm `/docs` and `/sample-payloads` respond.
- Verify your React app is calling the Cloud Run API at the configured base URL.
- If Streamlit is exposed, load its URL to confirm the dashboard renders.
