# Pysitant Server

An AI-powered assistant server that helps developers debug and manage their projects. Built with FastAPI, featuring multiple AI model providers with automatic fallback support and session-based authentication.

## Features

- **Multi-Model Support**: Seamlessly switch between different AI model providers
  - **Groq** (Light) - Fast, lightweight model for quick responses
  - **HuggingFace** (Heavy) - Advanced model for complex analysis
  - **Google Gemini** - Fallback model with automatic failover

- **Session Management**: Secure session-based authentication with configurable timeout
- **Queue-Based Architecture**: Async job scheduling with 3 worker threads for handling concurrent requests
- **Automatic Failover**: If a primary model fails, the system automatically falls back to Gemini
- **CORS Support**: Cross-origin requests enabled for easy client integration
- **Health Monitoring**: Real-time server health and queue status endpoint

## Prerequisites

- Python 3.11+
- API keys for model providers:
  - `GROQ_API_KEY` (Groq)
  - `HUGGINGFACE_API_TOKEN` (HuggingFace)
  - `GOOGLE_API_KEY` (Google Gemini)
- `PYSITANT_API_KEY` - Server authentication key

## Installation

### Local Setup

1. Clone the repository:
```bash
git clone <repo-url>
cd Server_Pypilot
```

2. Create a `.env` file with required environment variables:
```env
PYSITANT_API_KEY=your_api_key_here
PYSITANT_SESSION_TIMEOUT_SECONDS=1800
GROQ_API_KEY=your_groq_key
HUGGINGFACE_API_TOKEN=your_huggingface_token
GOOGLE_API_KEY=your_google_key
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the server:
```bash
uvicorn main:app --host 0.0.0.0 --port 8001
```

### How to Convert Code to Docker Container

Converting this Python application to a Docker container is simple. The project already includes a `Dockerfile`:

**1. Understanding the Dockerfile**
```dockerfile
FROM python:3.11-slim          # Use Python 3.11 base image
WORKDIR /app                   # Set working directory
COPY requirements.txt .        # Copy dependencies
RUN pip install -r requirements.txt  # Install packages
COPY . .                       # Copy application code
EXPOSE 8001                    # Expose port
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
```

**2. Build the Docker image**
```bash
docker build -t pysitant-server .
```
This creates a Docker image called `pysitant-server` from your code.

**3. Run the container**
```bash
docker run -p 8001:8001 \
  -e PYSITANT_API_KEY=your_key \
  -e GROQ_API_KEY=your_groq_key \
  -e HUGGINGFACE_API_TOKEN=your_huggingface_token \
  -e GOOGLE_API_KEY=your_google_key \
  pysitant-server
```
This starts a container from the image with environment variables.

**4. Test the container**
```bash
curl http://localhost:8001/health
```

**What Docker does:**
- Packages your entire application (Python code + all dependencies) into a single image
- Ensures it runs the same way on any machine (laptop, VPS, cloud)
- Isolates the application from your system
- Makes deployment and scaling simple

### Docker Setup (Local)

Build and run using Docker locally:
```bash
docker build -t pysitant-server .
docker run -p 8001:8001 \
  -e PYSITANT_API_KEY=your_key \
  -e GROQ_API_KEY=your_groq_key \
  -e HUGGINGFACE_API_TOKEN=your_huggingface_token \
  -e GOOGLE_API_KEY=your_google_key \
  pysitant-server
```

### Deploy Built Docker Image to VPS

Once you've built the Docker image locally, transfer it to your VPS and run it there.

#### Method 1: Using Docker Save & Load (Simple)

**On your local machine:**
```bash
# Build the image locally
docker build -t pysitant-server .

# Save the image to a file
docker save pysitant-server -o pysitant-server.tar

# Transfer to VPS (this uploads the file)
scp pysitant-server.tar root@your_vps_ip:/tmp/
```

**On your VPS:**
```bash
# SSH into VPS
ssh root@your_vps_ip

# Load the image
docker load -i /tmp/pysitant-server.tar

# Create .env file
cat > /opt/pysitant-server/.env << EOF
PYSITANT_API_KEY=your_secure_key
GROQ_API_KEY=your_groq_key
HUGGINGFACE_API_TOKEN=your_hf_token
GOOGLE_API_KEY=your_google_key
EOF

# Run the container
docker run -d \
  -p 8001:8001 \
  --name pysitant-server \
  --restart unless-stopped \
  -e PYSITANT_API_KEY=your_secure_key \
  -e GROQ_API_KEY=your_groq_key \
  -e HUGGINGFACE_API_TOKEN=your_hf_token \
  -e GOOGLE_API_KEY=your_google_key \
  pysitant-server

# Verify it's running
docker ps
curl http://localhost:8001/health
```

#### Method 2: Using Docker Hub (Recommended for Production)

**Create Docker Hub account** at [hub.docker.com](https://hub.docker.com)

**On your local machine:**
```bash
# Build the image
docker build -t pysitant-server .

# Tag it for Docker Hub
docker tag pysitant-server your_dockerhub_username/pysitant-server:latest

# Login to Docker Hub
docker login

# Push to Docker Hub
docker push your_dockerhub_username/pysitant-server:latest
```

**On your VPS:**
```bash
# SSH into VPS
ssh root@your_vps_ip

# Pull the image from Docker Hub
docker pull your_dockerhub_username/pysitant-server:latest

# Create .env file
mkdir -p /opt/pysitant-server
cat > /opt/pysitant-server/.env << EOF
PYSITANT_API_KEY=your_secure_key
GROQ_API_KEY=your_groq_key
HUGGINGFACE_API_TOKEN=your_hf_token
GOOGLE_API_KEY=your_google_key
EOF

# Run the container
docker run -d \
  -p 8001:8001 \
  --name pysitant-server \
  --restart unless-stopped \
  --env-file /opt/pysitant-server/.env \
  your_dockerhub_username/pysitant-server:latest

# Verify
docker ps
curl http://localhost:8001/health
```

### Docker Deployment on VPS

#### Prerequisites
- VPS with Docker and Docker Compose installed
- SSH access to your VPS
- Domain name (optional, for reverse proxy)

#### Step 1: Connect to Your VPS
```bash
ssh root@your_vps_ip
```

#### Step 2: Install Docker (if not already installed)
```bash
# Update system packages
apt update && apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version
```

#### Step 3: Clone Repository and Setup
```bash
# Create app directory
mkdir -p /opt/pysitant-server
cd /opt/pysitant-server

# Clone your repository
git clone <repo-url> .

# Or if you're uploading files directly:
# scp -r /local/path/to/project root@your_vps_ip:/opt/pysitant-server
```

#### Step 4: Create Docker Compose File
Create `docker-compose.yml` in your project directory:
```yaml
version: '3.8'

services:
  pysitant:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: pysitant-server
    ports:
      - "8001:8001"
    environment:
      - PYSITANT_API_KEY=${PYSITANT_API_KEY}
      - PYSITANT_SESSION_TIMEOUT_SECONDS=${PYSITANT_SESSION_TIMEOUT_SECONDS:-1800}
      - GROQ_API_KEY=${GROQ_API_KEY}
      - HUGGINGFACE_API_TOKEN=${HUGGINGFACE_API_TOKEN}
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
    restart: unless-stopped
    networks:
      - pysitant-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # Optional: Nginx reverse proxy
  nginx:
    image: nginx:alpine
    container_name: pysitant-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/nginx/certs:ro
    depends_on:
      - pysitant
    restart: unless-stopped
    networks:
      - pysitant-network

networks:
  pysitant-network:
    driver: bridge
```

#### Step 5: Create Environment File
Create `.env` file in your project directory:
```bash
PYSITANT_API_KEY=your_secure_api_key_here
PYSITANT_SESSION_TIMEOUT_SECONDS=1800
GROQ_API_KEY=your_groq_api_key
HUGGINGFACE_API_TOKEN=your_huggingface_token
GOOGLE_API_KEY=your_google_api_key
```

**Important**: Protect your `.env` file:
```bash
chmod 600 .env
```

#### Step 6: Create Nginx Configuration (Optional)
Create `nginx.conf` for reverse proxy:
```nginx
events {
    worker_connections 1024;
}

http {
    upstream pysitant {
        server pysitant:8001;
    }

    server {
        listen 80;
        server_name your_domain.com;

        location / {
            proxy_pass http://pysitant;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }

        location /health {
            proxy_pass http://pysitant/health;
            access_log off;
        }
    }

    # HTTPS configuration (after setting up SSL certs)
    # server {
    #     listen 443 ssl;
    #     server_name your_domain.com;
    #     ssl_certificate /etc/nginx/certs/cert.pem;
    #     ssl_certificate_key /etc/nginx/certs/key.pem;
    #     ...
    # }
}
```

#### Step 7: Start the Application
```bash
cd /opt/pysitant-server

# Pull latest code
git pull

# Build and start containers
docker-compose up -d

# View logs
docker-compose logs -f pysitant

# Check status
docker-compose ps
```

#### Step 8: Verify Deployment
```bash
# Check health endpoint
curl http://your_vps_ip:8001/health

# Check logs
docker-compose logs pysitant

# Check running containers
docker ps
```

#### Step 9: Setup SSL/HTTPS (Recommended)
Using Let's Encrypt with Certbot:
```bash
# Install Certbot
apt install certbot python3-certbot-nginx -y

# Get certificate
certbot certonly --standalone -d your_domain.com

# Update nginx.conf with SSL paths and restart
docker-compose restart nginx
```

### Common VPS Docker Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Restart a service
docker-compose restart pysitant

# View real-time logs
docker-compose logs -f pysitant

# Rebuild image
docker-compose build --no-cache pysitant

# Scale services
docker-compose up -d --scale pysitant=2

# Execute command in container
docker-compose exec pysitant bash

# Remove unused Docker resources
docker system prune -a

# Check resource usage
docker stats
```

### Heroku Deployment

Deploy using Procfile:
```bash
git push heroku main
```

## API Endpoints

### Health Check
```
GET /health
```
Returns server status and queue metrics.

**Response:**
```json
{
  "status": "ok",
  "incoming_queue": 2,
  "outgoing_queue": 0,
  "active_sessions": 5
}
```

### Create Session
```
POST /api/session
Header: Authorization: Bearer {PYSITANT_API_KEY}
```
Creates a new authenticated session.

**Response:**
```json
{
  "session_token": "token_here",
  "expires_in": 1800
}
```

### Ask AI
```
POST /api/ask
Header: Authorization: Bearer {SESSION_TOKEN}
Content-Type: application/json

{
  "prompt": "How do I fix this bug?",
  "context": {
    "file_structure": "...",
    "error_message": "..."
  },
  "provider": "light",
  "metadata": {}
}
```

**Parameters:**
- `prompt` (string): The question or prompt for the AI
- `context` (object): Project context and relevant information
- `provider` (string): Model provider - `"light"`, `"heavy"`, or `"gemini"`
- `metadata` (object, optional): Additional metadata

**Response:**
```json
{
  "answer": "Here's how to fix the bug...",
  "provider": "light"
}
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PYSITANT_API_KEY` | - | API key for server authentication (required) |
| `PYSITANT_SESSION_TIMEOUT_SECONDS` | 1800 | Session timeout in seconds (30 minutes) |
| `GROQ_API_KEY` | - | Groq API key |
| `HUGGINGFACE_API_TOKEN` | - | HuggingFace API token |
| `GOOGLE_API_KEY` | - | Google Gemini API key |

### Timeouts

- **Light Model (Groq)**: 10 seconds
- **Heavy Model (HuggingFace)**: 15 seconds
- **Gemini Model**: 15 seconds
- **Request Timeout**: 40 seconds

## Architecture

### Worker System
- **3 Processing Workers**: Handle incoming requests from the queue
- **1 Outgoing Worker**: Manage outgoing responses
- **1 Session Cleanup Worker**: Clean up expired sessions every 60 seconds

### Request Flow
1. Client creates a session with API key
2. Client sends prompt with session token
3. Job is queued in the incoming queue
4. Worker picks up the job and calls the selected model provider
5. On success or timeout, result is returned to client
6. Job is moved to outgoing queue for cleanup

## Authentication Flow

```
1. GET /api/session (with API key)
   ↓
   Returns session_token (valid for 30 minutes)
   ↓
2. POST /api/ask (with session_token)
   ↓
   Process request and return answer
```

## Error Handling

- **401 Unauthorized**: Invalid or missing API/session key
- **503 Service Unavailable**: Request queue is full
- **504 Gateway Timeout**: Request took too long to process
- **500 Internal Server Error**: Server processing error

All model failures automatically trigger Gemini fallback.

## Development

### Project Structure
```
.
├── main.py              # FastAPI app and core logic
├── models/
│   ├── model1.py       # Groq models
│   ├── model2.py       # HuggingFace models
│   └── fallback_model1.py  # Google Gemini fallback
├── requirements.txt     # Python dependencies
├── Dockerfile          # Docker configuration
├── Procfile            # Heroku deployment config
└── README.md           # This file
```

### Dependencies
- **fastapi**: Web framework
- **uvicorn**: ASGI server
- **pydantic**: Data validation
- **groq**: Groq API client
- **huggingface_hub**: HuggingFace client
- **google-genai**: Google Gemini API client
- **python-dotenv**: Environment variable management
- **httpx**: HTTP client library

## Monitoring

Monitor server health using the `/health` endpoint:
```bash
curl http://localhost:8001/health
```

Check logs for:
- Worker startup/shutdown messages
- Session cleanup activity
- Provider failures and fallback events
- Request processing times

## Troubleshooting

### Server Won't Start
- Verify all required API keys are set in `.env`
- Check that port 8001 is available
- Ensure Python 3.11+ is installed

### High Queue Sizes
- Increase worker count if consistently full
- Check model provider API limits and rate limits
- Monitor timeout values

### Session Token Expired
- Create a new session via `/api/session`
- Adjust `PYSITANT_SESSION_TIMEOUT_SECONDS` for longer sessions

### Model Provider Failures
- Check API key validity for the failing provider
- Monitor provider service status
- Verify network connectivity

## License

Specify your license here.

## Support

For issues and questions, please create an issue in the repository.
