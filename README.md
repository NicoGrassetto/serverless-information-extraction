# Azure AI Content Understanding - People Counter

Simple deployment and usage of Azure AI Content Understanding service for counting people in images.

## 🚀 Quick Deployment

Deploy the Azure AI Content Understanding service:

```bash
# PowerShell
cd infra
.\deploy.ps1

# Bash
cd infra
./deploy.sh
```

## 🔑 Get API Key

```bash
az cognitiveservices account keys list \
  --name content-understanding-smywgt2vzzxmi \
  --resource-group rg-document-intelligence \
  --query key1 --output tsv
```

## 🖼️ Count People in Images

Set your API key and run the people counter:

```bash
# Set API key
export CONTENT_UNDERSTANDING_KEY="your-api-key-here"

# Count people in test images
python people_counter.py

# Count people in your own image
python people_counter.py "https://your-image-url.jpg"
```

## 📋 What's Included

- `infra/main.bicep` - Simple Bicep template for Azure AI Content Understanding
- `infra/deploy.ps1` - PowerShell deployment script  
- `infra/deploy.sh` - Bash deployment script
- `people_counter.py` - Python script to analyze images and count people

## 🎯 Service Details

- **Service**: Azure AI Content Understanding
- **Kind**: AIServices 
- **SKU**: S0
- **Location**: West US
- **Capabilities**: Document, image, audio, and video analysis

That's it! Simple and clean. 🎉
