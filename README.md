6 🛡️ FakeSight - Deepfake Detection System

A microservices-based platform for detecting AI-generated faces and deepfakes using an ensemble of computer vision models.

## 🏗️ Architecture

- **`traefik`**: Reverse proxy and load balancer (Port 80).
- **`frontend`**: Static HTML/JS Dashboard (Nginx).
- **`auth-service`**: Django/JWT authentication service.
- **`user-service`**: Django user profile and detection history management.
- **`ai-service`**: FastAPI service running SigLIP and CLIP models.
- **`worker-service`**: RabbitMQ consumer for asynchronous database logging.
- **`rabbitmq`**: Message broker for inter-service communication.
- **`mysql`**: Databases for authentication and user data.

---

## 🚀 How to Run (Docker)

This is the recommended way to run the entire stack.

### Prerequisites
- Docker and Docker Compose installed.

### Steps
1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd deepfakedetector-main
   ```

2. **Start the environment**:
   ```bash
   docker-compose up --build
   ```

3. **Access the Application**:
   - **Main Web Interface**: [http://localhost](http://localhost) (or [http://localhost:8500](http://localhost:8500))
   - **Traefik Dashboard**: [http://localhost:8080](http://localhost:8080)
   - **RabbitMQ Management**: [http://localhost:15672](http://localhost:15672) (admin/admin1234)

---

## 💻 How to Run Locally (Manual)

If you want to run services individually for development:

### 1. Database & Broker (Use Docker for convenience)
```bash
docker run -d --name auth-db -e MYSQL_ROOT_PASSWORD=root1234 -e MYSQL_DATABASE=auth_db -p 3306:3306 mysql:8.0
docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management
```

### 2. Auth Service
```bash
cd auth-service
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8001
```

### 3. User Service
```bash
cd user-service
# Set environment variables for local DB and Auth service
export AUTH_SERVICE_URL=http://localhost:8001
python manage.py migrate
python manage.py runserver 0.0.0.0:8002
```

### 4. AI Service
```bash
cd ai-service
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8003
```

### 5. Frontend
Simply open `frontend/index.html` in your browser or serve it with a local server like `live-server`.

---

## 📝 Features & Comments

- **Ensemble Detection**: Combines deep learning classification with zero-shot CLIP analysis.
- **Async Logging**: Detection events are sent to RabbitMQ to ensure the user gets a fast response while logs are saved in the background.
- **JWT Security**: All sensitive API calls require a Bearer token.
