#!/bin/bash
set -e

# Function to display usage information
usage() {
  echo "Usage: $0 [options]"
  echo "Options:"
  echo "  -h, --help                 Display this help message"
  echo "  -r, --region REGION        AWS region (default: current configured region)"
  echo "  -a, --account-id ACCOUNT   AWS account ID (default: current account)"
  echo "  -n, --namespace NAMESPACE  Kubernetes namespace (default: inference)"
  echo "  -b, --build                Trigger CodeBuild project to build the image"
  echo "  -p, --project PROJECT      CodeBuild project name (default: kokoro-tts-build)"
  echo "  -d, --debug                Enable debug mode"
  exit 1
}

# Default values
AWS_REGION=$(aws configure get region)
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
NAMESPACE="inference"
TRIGGER_BUILD=false
CODEBUILD_PROJECT="kokoro-tts-build"
DEBUG=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      ;;
    -r|--region)
      AWS_REGION="$2"
      shift 2
      ;;
    -a|--account-id)
      AWS_ACCOUNT_ID="$2"
      shift 2
      ;;
    -n|--namespace)
      NAMESPACE="$2"
      shift 2
      ;;
    -b|--build)
      TRIGGER_BUILD=true
      shift
      ;;
    -p|--project)
      CODEBUILD_PROJECT="$2"
      shift 2
      ;;
    -d|--debug)
      DEBUG=true
      shift
      ;;
    *)
      echo "Unknown option: $1"
      usage
      ;;
  esac
done

# Enable debug mode if requested
if [ "$DEBUG" = true ]; then
  set -x
fi

echo "Using AWS Account ID: $AWS_ACCOUNT_ID"
echo "Using AWS Region: $AWS_REGION"
echo "Using Kubernetes Namespace: $NAMESPACE"
echo "Using CodeBuild Project: $CODEBUILD_PROJECT"

# Check if kubectl is installed
if ! command -v kubectl &> /dev/null; then
  echo "Error: kubectl is not installed or not in PATH"
  exit 1
fi

# Check if aws CLI is installed
if ! command -v aws &> /dev/null; then
  echo "Error: aws CLI is not installed or not in PATH"
  exit 1
fi

# Create the namespace if it doesn't exist
if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
  echo "Creating namespace: $NAMESPACE"
  kubectl create namespace "$NAMESPACE"
else
  echo "Namespace $NAMESPACE already exists"
fi

if [ "$TRIGGER_BUILD" = true ]; then
  # Check if CodeBuild project exists
  if ! aws codebuild batch-get-projects --names "$CODEBUILD_PROJECT" --query 'projects[0].name' --output text &> /dev/null; then
    echo "Error: CodeBuild project $CODEBUILD_PROJECT does not exist"
    echo "You need to deploy the Terraform module first:"
    echo "cd guidance-for-automated-provisioning-of-application-ready-amazon-eks-clusters/single-account-single-cluster-multi-env/30.eks/35.addons"
    echo "terraform apply -target=module.kokoro_tts_ci"
    exit 1
  fi

  # Trigger CodeBuild project
  echo "Triggering CodeBuild project: $CODEBUILD_PROJECT"
  BUILD_ID=$(aws codebuild start-build --project-name "$CODEBUILD_PROJECT" --query 'build.id' --output text)
  echo "Build started with ID: $BUILD_ID"
  
  # Wait for the build to complete
  echo "Waiting for build to complete..."
  aws codebuild wait build-complete --id "$BUILD_ID"
  
  # Check build status
  BUILD_STATUS=$(aws codebuild batch-get-builds --ids "$BUILD_ID" --query 'builds[0].buildStatus' --output text)
  if [ "$BUILD_STATUS" != "SUCCEEDED" ]; then
    echo "Build failed with status: $BUILD_STATUS"
    echo "Check the build logs for more information:"
    echo "aws codebuild batch-get-builds --ids $BUILD_ID --query 'builds[0].logs.deepLink' --output text"
    exit 1
  fi
  
  echo "Build completed successfully!"
fi

# Update the kokoro-tts.yaml file with AWS account ID and region
echo "Updating kokoro-tts.yaml with AWS account ID and region"
sed -i.bak "s/\${AWS_ACCOUNT_ID}/$AWS_ACCOUNT_ID/g" kokoro-tts.yaml
sed -i.bak "s/\${AWS_REGION}/$AWS_REGION/g" kokoro-tts.yaml
sed -i.bak "s/inference/$NAMESPACE/g" kokoro-tts.yaml

# Update the values.yaml file with AWS account ID and region
echo "Updating values.yaml with AWS account ID and region"
sed -i.bak "s/\${AWS_ACCOUNT_ID}/$AWS_ACCOUNT_ID/g" values.yaml
sed -i.bak "s/\${AWS_REGION}/$AWS_REGION/g" values.yaml

# Clean up backup files
rm -f *.bak

# Deploy the application using ArgoCD
echo "Deploying application using ArgoCD"
kubectl apply -f app_manifest.yaml

echo "Deployment complete!"
echo "To check the status of the application, run: kubectl get pods -n $NAMESPACE"
echo "To forward the service port, run: kubectl port-forward -n $NAMESPACE svc/kokoro-tts 8080:8080"
echo "To test the TTS service, run: curl -X POST http://localhost:8080/tts -H 'Content-Type: application/json' -d '{\"text\":\"Hello, this is a test of the Kokoro TTS system.\"}'" 