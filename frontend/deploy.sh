#!/usr/bin/env bash
# Deploy the frontend: CloudFront + S3 stack, build, upload, invalidate.
# Requires the fallguard-backend stack to be deployed first.
set -euo pipefail
cd "$(dirname "$0")"

REGION=us-east-1
STACK=fallguard-frontend

stack_output() {
  aws cloudformation describe-stacks --region "$REGION" --stack-name "$1" \
    --query "Stacks[0].Outputs[?OutputKey=='$2'].OutputValue" --output text
}

API_URL=$(stack_output fallguard-backend ApiUrl)

aws cloudformation deploy --region "$REGION" --stack-name "$STACK" \
  --template-file template.yaml \
  --parameter-overrides "ApiUrl=$API_URL" \
  --no-fail-on-empty-changeset

BUCKET=$(stack_output "$STACK" BucketName)
DIST_ID=$(stack_output "$STACK" DistributionId)

npm run build

# Hashed assets are immutable; index.html must always revalidate.
aws s3 sync dist/ "s3://$BUCKET/" --delete --exclude index.html \
  --cache-control "public,max-age=31536000,immutable"
aws s3 cp dist/index.html "s3://$BUCKET/index.html" --cache-control "no-cache"

aws cloudfront create-invalidation --distribution-id "$DIST_ID" \
  --paths "/" "/index.html" --query Invalidation.Id --output text

echo "Deployed: $(stack_output "$STACK" SiteUrl)"
