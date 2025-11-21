# Terraform + GitHub Actions CI/CD for the EV model

This guide shows how to deploy the FastAPI and Streamlit containers plus a React build using **Terraform** and **GitHub Actions**, with AWS authentication via **OIDC** (recommended) or **access keys**.

## Architecture targets
- **Containers**: FastAPI (`deploy/aws/Dockerfile.api`) and optional Streamlit (`deploy/aws/Dockerfile.streamlit`) run on ECS Fargate behind an ALB.
- **Static frontend**: React build on S3 + CloudFront (or Amplify).
- **State**: Terraform state in S3 with DynamoDB locking.

## Prerequisites
- Terraform >= 1.5.
- AWS account with permissions to create IAM roles, S3, DynamoDB, ECR, ECS, ALB, and CloudFront.
- GitHub repository that hosts the Terraform code.

## Terraform layout (example)
```
infra/
  main.tf            # providers, backend config (S3 state + DynamoDB lock)
  variables.tf       # image tags, VPC/subnets, domain names, cert ARNs, etc.
  ecr.tf             # ECR repos for api + streamlit
  ecs.tf             # ECS cluster, task defs, services, security groups
  alb.tf             # ALB, listeners, target groups, rules (/ev/* to api, optional host rule to streamlit)
  s3_cloudfront.tf   # React hosting bucket + CloudFront distro
  outputs.tf         # API/Streamlit endpoints, CloudFront URL
```

Keep the Terraform module names and variables aligned with the AWS guide in `docs/aws_deployment.md` (ports 8000 for FastAPI, 8501 for Streamlit).

## AWS authentication from GitHub Actions
### OIDC (preferred)
1. Create an **IAM role** with a trust policy that allows your GitHub repo to assume it via the `token.actions.githubusercontent.com` provider.
2. Attach policies that permit creating/updating the resources above.
3. Store the role ARN in a GitHub Actions secret (e.g., `AWS_ROLE_TO_ASSUME`).

### Access keys (fallback)
- Create an IAM user with scoped permissions and store `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` as GitHub secrets. Rotate regularly.

## Example GitHub Actions workflow
Save as `.github/workflows/terraform.yaml` in your repo and adjust the paths/variables. The workflow plans on pull requests and applies on `main`.

```yaml
name: terraform

on:
  pull_request:
    paths:
      - 'infra/**'
  push:
    branches: [main]
    paths:
      - 'infra/**'

permissions:
  id-token: write   # needed for OIDC
  contents: read

env:
  TF_WORKING_DIR: infra
  AWS_REGION: us-east-1

jobs:
  terraform:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Configure AWS credentials (OIDC)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_TO_ASSUME }}
          aws-region: ${{ env.AWS_REGION }}
        # If using access keys instead, comment the step above and set AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY env vars.

      - name: Set up Terraform
        uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: 1.6.6

      - name: Terraform Init
        working-directory: ${{ env.TF_WORKING_DIR }}
        run: terraform init -input=false

      - name: Terraform Plan
        if: github.event_name == 'pull_request'
        working-directory: ${{ env.TF_WORKING_DIR }}
        run: terraform plan -input=false -out=tfplan

      - name: Terraform Apply
        if: github.event_name == 'push' && github.ref == 'refs/heads/main'
        working-directory: ${{ env.TF_WORKING_DIR }}
        run: terraform apply -input=false -auto-approve
```

### Variables to wire
- **Container images**: pass the ECR image URIs/tags for FastAPI and Streamlit as variables (or build/push earlier in the workflow using the Dockerfiles in `deploy/aws/`).
- **Domain + certs**: hostnames for API/Streamlit/React and matching ACM certificate ARNs.
- **Network**: VPC ID, private subnets for ECS, public subnets for ALB, security group IDs.
- **State backend**: configure `backend "s3" {}` in `infra/main.tf` with bucket, key, region, and DynamoDB table.

## CLI-based deploy (local)
1. Configure AWS creds locally (OIDC via `aws sso login` or access keys).
2. Run `terraform -chdir=infra init`, `terraform plan`, then `terraform apply`.
3. Tag and push new container images to ECR before applying if you changed app code.

## Tips
- Keep **plan-only** runs on PRs and restrict **apply** to protected branches.
- Use **workspaces** or separate state files for dev/stage/prod.
- Surface outputs (ALB DNS, CloudFront URL) to your React environment config and API clients.
- Use **backend versioning** (S3 object locking) and **DynamoDB locking** to avoid concurrent applies.
