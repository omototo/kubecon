# DeepSeek with Kokoro TTS Integration

This example deploys the DeepSeek-R1-Distill LLM with Kokoro-82M text-to-speech model on a Kubernetes cluster with GPU capability.

## Prerequisites

- Kubernetes cluster with GPU nodes
- Inference capability enabled in the cluster
- NVIDIA device plugin installed
- ArgoCD installed for GitOps deployment

## Components

This integration consists of three main services:

1. **DeepSeek VLLM Service**: Provides the large language model capabilities using VLLM for efficient inference
2. **Kokoro TTS Service**: Provides text-to-speech functionality with high-quality voice synthesis
3. **Integration Service**: Acts as a bridge between the two services, processing user requests and responses

## Architecture

```
┌─────────────┐     ┌───────────────┐     ┌─────────────┐
│   Client    │────►│  Integration  │────►│  DeepSeek   │
│  (Browser)  │     │    Service    │     │    VLLM     │
└─────────────┘     └───────────────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │   Kokoro    │
                    │     TTS     │
                    └─────────────┘
```

## Usage

### API Endpoints

The integration service exposes the following endpoints:

- **POST /api/chat**
  - Request body: `{"input": "Your question or prompt here"}`
  - Response: `{"text": "LLM response text", "audio_url": "/api/audio/filename.wav"}`

- **GET /api/audio/{filename}**
  - Returns the audio file generated from the TTS service

## Resource Requirements

- DeepSeek VLLM: 1 GPU, 32 CPU, 100GB memory
- Kokoro TTS: 4 CPU, 8GB memory
- Integration Service: 1 CPU, 2GB memory

## Customization

You can customize the deployment by modifying the `values.yaml` file to adjust:

- Model parameters
- Resource allocations
- Service configurations 

## Building and Deploying the Kokoro TTS Image

The Kokoro TTS service requires a custom Docker image that uses the Hugging Face model `hexgrad/Kokoro-82M`. Follow these steps to build and deploy the image:

1. Set environment variables:
```bash
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export AWS_REGION=$(aws configure get region)
```

2. Create an ECR repository for the Kokoro TTS image:
```bash
aws ecr create-repository --repository-name kokoro-tts
```

3. Log in to ECR:
```bash
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
```

4. Build the Docker image:
```bash
cd examples/deepseek-kokoro
docker build -t kokoro-tts:latest -f Dockerfile.kokoro-tts .
```

5. Tag and push the image to ECR:
```bash
docker tag kokoro-tts:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/kokoro-tts:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/kokoro-tts:latest
```

6. Update the kokoro-tts.yaml file with your AWS account ID and region:
```bash
sed -i "s/\${AWS_ACCOUNT_ID}/$AWS_ACCOUNT_ID/g" kokoro-tts.yaml
sed -i "s/\${AWS_REGION}/$AWS_REGION/g" kokoro-tts.yaml
```

7. Deploy the application using ArgoCD:
```bash
kubectl apply -f app_manifest.yaml
```

## Using the Kokoro TTS API

Once deployed, you can use the Kokoro TTS API to convert text to speech:

```bash
# Forward the service port
kubectl port-forward -n inference svc/kokoro-tts 8080:8080

# Send a request to the API
curl -X POST http://localhost:8080/tts \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, this is a test of the Kokoro TTS system."}'
```

The API will return a JSON response with the audio data encoded in base64, which you can decode and save as a WAV file. 