# AWS deployment guide (React + FastAPI + Streamlit)

Use this recipe to deploy the existing stack on AWS with:
- **React UI** served from S3 + CloudFront (or AWS Amplify).
- **FastAPI** service on ECS Fargate behind an Application Load Balancer (ALB) at `/ev/*`.
- **Optional Streamlit** service on ECS Fargate at a separate subdomain (e.g., `dash.yourdomain.com`).

## Prerequisites
- AWS CLI v2 configured with an account/region.
- Docker installed locally for image builds.
- A registered domain in Route 53 (recommended) plus ACM certificate for HTTPS on CloudFront/ALB.

## 1) Build and push container images to ECR
Create two repositories (API and Streamlit) and push the images built from the provided Dockerfiles.

```bash
export AWS_ACCOUNT_ID="123456789012"
export AWS_REGION="us-east-1"
export API_REPO="ev-financial-model-api"
export STREAMLIT_REPO="ev-financial-model-streamlit"

aws ecr create-repository --repository-name "$API_REPO"
aws ecr create-repository --repository-name "$STREAMLIT_REPO"
aws ecr get-login-password --region "$AWS_REGION" | \
  docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

# Build and push FastAPI
docker build -f deploy/aws/Dockerfile.api -t "$API_REPO" .
docker tag "$API_REPO:latest" "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$API_REPO:latest"
docker push "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$API_REPO:latest"

# Build and push Streamlit
docker build -f deploy/aws/Dockerfile.streamlit -t "$STREAMLIT_REPO" .
docker tag "$STREAMLIT_REPO:latest" "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$STREAMLIT_REPO:latest"
docker push "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$STREAMLIT_REPO:latest"
```

## 2) Host the React build
- Build the React app locally (`npm run build`) and upload the `dist`/`build` output to **S3**.
- Front it with **CloudFront** for HTTPS and caching (origin = the S3 bucket). Configure the default root object to `index.html`.
- Set an **API base URL** in your React app (environment variable) pointing to the ALB domain you create for the FastAPI service (e.g., `https://api.yourdomain.com`).

## 3) Provision ECS Fargate services behind an ALB
1. Create an **ECS cluster** (Fargate).
2. Create an **Application Load Balancer** with one HTTPS listener and two target groups:
   - `ev-api`: protocol HTTP, port **8000**.
   - `ev-streamlit`: protocol HTTP, port **8501** (optional if you want Streamlit public).
3. Add **listener rules**:
   - Path `/ev/*` (and `/docs` if desired) → forward to `ev-api` target group.
   - Subdomain rule (e.g., host header `dash.yourdomain.com`) → forward to `ev-streamlit`.
4. Create two **task definitions** (Fargate) using the ECR images and set container ports (8000 for API, 8501 for Streamlit). Add environment variables if needed (e.g., `UVICORN_WORKERS`, `STREAMLIT_SERVER_BASEURLPATH=/streamlit`).
5. Create **ECS services** for each task definition, attach them to the ALB target groups, and enable auto-scaling as needed.

## 4) DNS and TLS
- Point `api.yourdomain.com` (ALIAS/AAAA in Route 53) to the ALB.
- Point `dash.yourdomain.com` to the same ALB with the Streamlit rule.
- Attach an **ACM certificate** (in the ALB’s region) covering both subdomains.

## 5) Security and networking
- Place services in **private subnets** with a NAT gateway; ALB in public subnets.
- Use **security groups** so ALB can reach the ECS tasks on 8000/8501, but tasks are not publicly exposed.
- For private Streamlit usage, restrict the Streamlit listener rule by source IP or put it behind an Identity Provider (e.g., Cognito + ALB authentication action).

## 6) Health checks and observability
- FastAPI: configure ALB health check to `/` or `/docs` on port 8000.
- Streamlit: health check `/health` (add `--server.enableXsrfProtection=false` if you need custom probes).
- Enable **AWS Logs** on each task (e.g., `/ecs/ev-api`) and consider **X-Ray** for tracing.

## 7) Environment variables to consider
- `ALLOWED_ORIGINS` for CORS (or update `scripts/api_server.py` to load from env before deployment).
- `UVICORN_WORKERS` if you want more workers in the API container (override CMD in ECS to pass `--workers`).
- `STREAMLIT_SERVER_BASEURLPATH=/streamlit` if you route Streamlit under a path instead of a subdomain (also update ALB rule to strip the prefix).

## 8) Optional: Infrastructure as Code
- **AWS Copilot CLI**: `copilot init`, then define two services (api + streamlit) with path-based routing.
- **AWS CDK/Terraform**: encode the ALB, ECS services, and CloudFront distribution for repeatable deploys.

## 9) Validation
- Open `https://api.yourdomain.com/docs` to confirm FastAPI is reachable.
- Call `https://api.yourdomain.com/sample-payloads` from your React app.
- Visit `https://dash.yourdomain.com` (if exposed) to confirm Streamlit renders.
