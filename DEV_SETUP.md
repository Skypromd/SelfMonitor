# SelfMonitor Development Environment Setup

This guide helps you set up a complete development environment for the SelfMonitor FinTech platform.

## 🚀 Quick Start

### 1. Automated Setup (Recommended)

```powershell
# Clone and enter the project
git clone <repository-url>
cd SelfMonitor

# Run the automated setup script
.\setup-dev-env.ps1
```

### 2. Manual Setup

If you prefer to set up manually or the automated script fails:

#### Prerequisites

- **Python 3.8+** - [Download](https://python.org)
- **Node.js 16+** - [Download](https://nodejs.org) 
- **Docker Desktop** - [Download](https://docker.com)
- **VS Code** - [Download](https://code.visualstudio.com)

#### Steps

1. **Create Virtual Environment**
   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

2. **Install Dependencies**
   ```powershell
   # Install development tools
   pip install black flake8 mypy pytest pytest-asyncio

   # Install service dependencies
   cd services\user-profile-service
   pip install -r requirements.txt
   cd ..\..
   ```

3. **Environment Configuration**
   ```powershell
   cp .env.development .env.local
   # Edit .env.local with your API keys
   ```

4. **Start Infrastructure**
   ```powershell
   docker-compose up -d postgres redis
   ```

5. **Run Migrations**
   ```powershell
   cd services\user-profile-service
   alembic upgrade head
   cd ..\..
   ```

## 🛠️ Development Workflow

### VS Code Setup

1. **Open Workspace**
   ```
   File → Open Workspace from File → SelfMonitor.code-workspace
   ```

2. **Install Recommended Extensions**
   VS Code will prompt you to install recommended extensions automatically.

### Running Services

#### Individual Service (for debugging)
- Press `F5` in VS Code
- Select service from dropdown
- Service starts with hot reload

#### All Services (production-like)
```powershell
docker-compose up --build
```

### Testing

#### Run Tests for Specific Service
```powershell
cd services\user-profile-service
python -m pytest tests\ -v
```

#### Run All Tests
```powershell
python -m pytest tests\ -v
```

#### Using VS Code
- `Ctrl+Shift+P` → `Tasks: Run Task` → `Run Service Tests`

### Code Quality

#### Format Code
```powershell
python -m black services\user-profile-service\
```

#### Lint Code  
```powershell
python -m flake8 services\user-profile-service\
```

#### Type Check
```powershell
python -m mypy services\user-profile-service\
```

#### Using VS Code
- `Ctrl+Shift+P` → `Tasks: Run Task` → Select formatting/linting task

## 📁 Project Structure

```
SelfMonitor/
├── 📁 .vscode/                   # VS Code configuration
│   ├── settings.json             # Workspace settings
│   ├── extensions.json           # Recommended extensions
│   ├── launch.json               # Debug configurations
│   └── tasks.json                # Automated tasks
├── 📁 services/                  # Microservices
│   ├── user-profile-service/     # User management
│   ├── transactions-service/     # Transaction processing
│   ├── auth-service/              # Authentication
│   └── ...                       # Other services
├── 📁 apps/                      # Client applications
│   ├── web-portal/               # Next.js web app
│   └── mobile/                   # React Native app
├── 📁 libs/                      # Shared libraries
│   ├── common-types/             # TypeScript types
│   ├── db/                       # Database utilities
│   └── event_streaming/          # Kafka utilities
├── 📁 ml/                        # Machine learning
│   ├── models/                   # ML models
│   └── mlops-platform/           # MLflow setup
├── 📁 infra/                     # Infrastructure
│   ├── k8s/                      # Kubernetes manifests
│   ├── terraform/                # Infrastructure as code
│   └── docker-compose.yml        # Local development
├── 📁 docs/                      # Documentation
└── 📁 tests/                     # Integration tests
```

## 🌐 Service URLs (Development)

| Service | URL | Documentation |
|---------|-----|---------------|
| User Profile | http://localhost:8001 | http://localhost:8001/docs |
| Transactions | http://localhost:8002 | http://localhost:8002/docs |
| Auth Service | http://localhost:8003 | http://localhost:8003/docs |
| Banking Connector | http://localhost:8004 | http://localhost:8004/docs |
| Advice Service | http://localhost:8005 | http://localhost:8005/docs |
| GraphQL Gateway | http://localhost:4000 | http://localhost:4000/graphql |
| Web Portal | http://localhost:3000 | - |
| Grafana | http://localhost:3001 | admin/admin |
| Jaeger | http://localhost:16686 | - |

## 🔧 Common Tasks

### Database Operations

#### Reset Database
```powershell
docker-compose down -v
docker-compose up -d postgres
cd services\user-profile-service
alembic upgrade head
```

#### Create Migration
```powershell
cd services\user-profile-service
alembic revision --autogenerate -m "Add new feature"
```

### Service Development

#### Add New Endpoint
1. Edit `services\{service}\app\routers\{router}.py`
2. Add tests in `services\{service}\tests\test_{router}.py`
3. Run tests: `python -m pytest tests\test_{router}.py -v`

#### Add New Service
1. Copy existing service structure
2. Update `docker-compose.yml`
3. Update `.vscode\launch.json` and `.vscode\tasks.json`
4. Add to service list in workspace configs

### Frontend Development

#### Web Portal
```powershell
cd apps\web-portal
npm run dev
```

#### GraphQL Gateway
```powershell
cd services\graphql-gateway  
npm run dev
```

## 🐛 Troubleshooting

### Common Issues

#### Python Virtual Environment
```powershell
# If activation fails
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

#### Docker Issues
```powershell
# Reset Docker environment
docker-compose down -v
docker system prune -f
docker-compose up -d
```

#### VS Code Python Interpreter
1. `Ctrl+Shift+P` → `Python: Select Interpreter`
2. Choose `.venv\Scripts\python.exe`

#### Port Conflicts
```powershell
# Check what's using a port
netstat -ano | findstr :8001
# Kill process by PID
taskkill /PID {pid} /F
```

### Getting Help

- 📖 Check the [docs/](docs/) directory for detailed documentation
- 🐛 Create an issue for bugs or questions
- 💬 Ask in team chat for immediate help

## 🎯 Next Steps

After setting up your development environment:

1. **Read the Architecture Guide** - `docs/architecture/README.md`
2. **Review API Documentation** - Visit service `/docs` endpoints
3. **Run the Test Suite** - Ensure everything works
4. **Pick a Task** - Check GitHub issues or project board
5. **Start Coding** - Create a feature branch and begin development

Happy coding! 🚀