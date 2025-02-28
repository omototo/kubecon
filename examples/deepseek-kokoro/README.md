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