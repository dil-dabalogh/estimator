# Running Frontend Locally with VPC-Backed Backend

## Overview

You can deploy only the backend to AWS (behind VPC endpoints) and run the frontend locally. This is useful for:
- Testing backend changes without deploying frontend
- Development workflow where frontend changes frequently
- Avoiding S3 endpoint setup initially

## Requirements

- **API Gateway VPC Interface Endpoint**: Required (must be created by VPC owner)
- **S3 VPC Gateway Endpoint**: Not needed (only required for S3-hosted frontend)
- **VPN Connection**: You must be connected to the Diligent VPN to access the backend

## Setup Steps

### 1. Deploy Backend Only

Update `infrastructure/samconfig.toml` to use only the API Gateway endpoint:

```toml
[dev.deploy.parameters]
parameter_overrides = "VpcId=vpc-0debf6fec89321668 VpcCidrBlock=10.0.0.0/16 ExistingApiGatewayVpcEndpointId=vpce-xxxxxxxxxxxxxxxxx ExistingS3VpcEndpointId= LLMProvider=bedrock ..."
```

**Note**: `ExistingS3VpcEndpointId=` is left empty (no S3 endpoint needed).

Deploy the backend:

```bash
cd infrastructure
chore deploy backend
```

After deployment, note the API URLs from the output:
- **HTTP API URL**: `https://xxxxx.execute-api.us-west-2.amazonaws.com`
- **WebSocket URL**: `wss://xxxxx.execute-api.us-west-2.amazonaws.com/prod`

### 2. Connect to VPN

Ensure you're connected to the Diligent VPN. The backend API is only accessible through the VPC endpoint.

### 3. Configure Local Frontend

The frontend needs to be configured to use the deployed backend API URL.

#### Option A: Environment Variable (Recommended)

Create or update `frontend/.env.local`:

```bash
VITE_API_URL=https://xxxxx.execute-api.us-west-2.amazonaws.com
VITE_WS_URL=wss://xxxxx.execute-api.us-west-2.amazonaws.com/prod
```

#### Option B: Update Frontend Code

If the frontend uses a hardcoded API URL, update it to use the deployed backend URL.

Check `frontend/src/lib/api.ts` or similar files for API configuration.

### 4. Run Frontend Locally

```bash
cd frontend
npm install
npm run dev
```

The frontend will start at `http://localhost:5173` and connect to the deployed backend.

## How It Works

```
Your Local Machine (on VPN)
    │
    ├─→ Local Frontend (localhost:5173)
    │        │
    │        └─→ API Gateway VPC Interface Endpoint
    │                    │
    │                    └─→ API Gateway (Backend)
    │                                │
    │                                └─→ Lambda Functions
```

1. Frontend runs locally on your machine
2. Frontend makes API calls to the deployed backend URL
3. Your VPN connection routes requests through the VPC endpoint
4. API Gateway resource policy allows access only from the VPC endpoint
5. Backend processes requests and returns responses

## Troubleshooting

### Cannot Connect to Backend

**Symptom**: Frontend shows connection errors or timeouts.

**Solutions**:
1. **Verify VPN Connection**: Ensure you're connected to Diligent VPN
   ```bash
   # Test VPN connectivity
   ping 10.0.0.1  # Replace with a VPC IP if known
   ```

2. **Check API URL**: Verify the API URL in frontend matches the deployed backend
   ```bash
   # Get API URL from CloudFormation
   aws cloudformation describe-stacks \
     --stack-name estimation-tool-api \
     --query 'Stacks[0].Outputs[?OutputKey==`EstimationApiUrl`].OutputValue' \
     --output text
   ```

3. **Test API Directly**: Try accessing the API directly from your machine (while on VPN)
   ```bash
   curl https://xxxxx.execute-api.us-west-2.amazonaws.com/health
   ```

4. **Check DNS Resolution**: Verify DNS resolves to private IPs
   ```bash
   nslookup xxxxx.execute-api.us-west-2.amazonaws.com
   # Should resolve to a private IP (10.x.x.x) when on VPN
   ```

### CORS Errors

**Symptom**: Browser shows CORS errors in console.

**Solution**: The backend CORS configuration should allow `localhost` origins. Check `infrastructure/template.yaml`:

```yaml
CorsConfiguration:
  AllowOrigins:
    - "*"  # Allows all origins including localhost
```

If CORS is restricted, you may need to add `http://localhost:5173` to allowed origins.

### WebSocket Connection Fails

**Symptom**: WebSocket connection cannot be established.

**Solutions**:
1. Verify WebSocket URL is correct (should use `wss://` not `ws://`)
2. Check that you're on VPN (WebSocket also goes through VPC endpoint)
3. Verify the WebSocket API has the resource policy applied

## Switching to S3-Hosted Frontend Later

When you're ready to deploy the frontend to S3:

1. Request S3 VPC Gateway Endpoint from VPC owner
2. Update `samconfig.toml` with the S3 endpoint ID:
   ```toml
   ExistingS3VpcEndpointId=vpce-yyyyyyyyyyyyyyyyy
   ```
3. Deploy frontend:
   ```bash
   chore deploy frontend
   ```

## Benefits of This Approach

- **Faster Development**: Frontend changes don't require deployment
- **Cost Savings**: No S3 endpoint needed initially (~$0 vs ~$14.40/month)
- **Easier Testing**: Quick iteration on frontend without deployment cycles
- **Simpler Setup**: Only need one VPC endpoint to get started

## Limitations

- Frontend is only accessible from your local machine
- Requires VPN connection to access backend
- Not suitable for production or shared access
- WebSocket connections also require VPN

