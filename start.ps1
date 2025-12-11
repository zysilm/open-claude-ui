# BreezeRun Start Script for Windows (PowerShell)
# This script sets up the environment and starts the services
# Run with: powershell -ExecutionPolicy Bypass -File start.ps1

param(
    [switch]$SkipDocker,
    [switch]$NoStart
)

$ErrorActionPreference = "Stop"

# Configuration
$PYTHON_VERSION = "3.12"
$NODE_VERSION = "20"

# Capture script directory at load time (before any functions run)
$script:ScriptDirectory = if ($PSScriptRoot) { 
    $PSScriptRoot 
} elseif ($MyInvocation.MyCommand.Path) { 
    Split-Path -Parent $MyInvocation.MyCommand.Path 
} else { 
    Get-Location 
}

# Store the detected Python command globally
$script:PythonCmd = $null

function Test-RealPython {
    param([string]$Command)
    
    # Check if command exists
    $cmdInfo = Get-Command $Command -ErrorAction SilentlyContinue
    if (-not $cmdInfo) {
        return $false
    }
    
    # Skip Windows Store stub (it's in WindowsApps folder)
    if ($cmdInfo.Source -and $cmdInfo.Source -match "WindowsApps") {
        return $false
    }
    
    # Try to run it and check for valid version output
    try {
        $output = & $Command --version 2>&1
        if ($output -match "Python \d+\.\d+") {
            return $true
        }
    } catch {
        # Command failed to run properly
    }
    
    return $false
}

function Get-PythonCommand {
    # Return cached result if already found
    if ($script:PythonCmd) {
        return $script:PythonCmd
    }
    
    # Try py launcher first (most reliable on Windows)
    if (Test-RealPython "py") {
        $script:PythonCmd = "py"
        return "py"
    }
    
    # Try python3
    if (Test-RealPython "python3") {
        $script:PythonCmd = "python3"
        return "python3"
    }
    
    # Try python (but avoid Windows Store stub)
    if (Test-RealPython "python") {
        $script:PythonCmd = "python"
        return "python"
    }
    
    return $null
}

function Get-PythonVersion {
    $pythonCmd = Get-PythonCommand
    if (-not $pythonCmd) {
        return $null
    }
    
    try {
        $output = & $pythonCmd --version 2>&1
        if ($output -match "Python (\d+\.\d+\.\d+)") {
            return $matches[1]
        } elseif ($output -match "Python (\d+\.\d+)") {
            return $matches[1]
        }
    } catch {
        # Failed to get version
    }
    
    return $null
}

function Test-RealNode {
    $cmdInfo = Get-Command "node" -ErrorAction SilentlyContinue
    if (-not $cmdInfo) {
        return $false
    }
    
    # Skip if it's a Windows Store stub
    if ($cmdInfo.Source -and $cmdInfo.Source -match "WindowsApps") {
        return $false
    }
    
    try {
        $output = & node --version 2>&1
        if ($output -match "v\d+\.\d+") {
            return $true
        }
    } catch {
        # Command failed
    }
    
    return $false
}

function Write-Header {
    Write-Host ""
    Write-Host "+=============================================================+" -ForegroundColor Blue
    Write-Host "|                    BreezeRun Setup                          |" -ForegroundColor Blue
    Write-Host "|         Run your code like a breeze                         |" -ForegroundColor Blue
    Write-Host "+=============================================================+" -ForegroundColor Blue
    Write-Host ""
}

function Write-Step {
    param([string]$Message)
    Write-Host "[STEP] " -ForegroundColor Green -NoNewline
    Write-Host $Message
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] " -ForegroundColor Yellow -NoNewline
    Write-Host $Message
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] " -ForegroundColor Red -NoNewline
    Write-Host $Message
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] " -ForegroundColor Green -NoNewline
    Write-Host $Message
}

function Test-Command {
    param([string]$Command)
    $null = Get-Command $Command -ErrorAction SilentlyContinue
    return $?
}

function Install-Chocolatey {
    if (-not (Test-Command "choco")) {
        Write-Step "Installing Chocolatey..."
        Set-ExecutionPolicy Bypass -Scope Process -Force
        [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
        Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

        # Refresh PATH
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
    }
}

function Install-Python {
    Write-Step "Checking Python installation..."

    $pythonCmd = Get-PythonCommand
    if ($pythonCmd) {
        $version = Get-PythonVersion
        if ($version -and $version -match "^3\.(11|12|13)") {
            Write-Success "Python is installed: Python $version (using '$pythonCmd')"
            return
        } elseif ($version) {
            Write-Warning "Python $version found, but version 3.11+ is recommended"
        }
    }

    Write-Step "Installing Python $PYTHON_VERSION..."
    choco install python --version=$PYTHON_VERSION -y

    # Refresh PATH
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
    
    # Clear cached python command so it gets re-detected
    $script:PythonCmd = $null
}

function Install-NodeJS {
    Write-Step "Checking Node.js installation..."

    if (Test-RealNode) {
        try {
            $nodeVersion = node --version 2>&1
            $majorVersion = [int]($nodeVersion -replace 'v(\d+)\..*', '$1')
            if ($majorVersion -ge 18) {
                Write-Success "Node.js is installed: $nodeVersion"
                return
            } else {
                Write-Warning "Node.js $nodeVersion found, but version 18+ is required"
            }
        } catch {
            Write-Warning "Could not determine Node.js version"
        }
    }

    Write-Step "Installing Node.js $NODE_VERSION..."
    choco install nodejs-lts -y

    # Refresh PATH
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
}

function Install-Docker {
    Write-Step "Checking Docker installation..."

    if (Test-Command "docker") {
        Write-Success "Docker is installed"
        return
    }

    Write-Step "Installing Docker Desktop..."
    choco install docker-desktop -y

    Write-Warning "Please start Docker Desktop manually after installation"
    Write-Warning "You may need to restart your computer for Docker to work properly"
}

function Install-Poetry {
    Write-Step "Checking Poetry installation..."

    if (Test-Command "poetry") {
        Write-Success "Poetry is installed"
        return
    }

    $pythonCmd = Get-PythonCommand
    if (-not $pythonCmd) {
        Write-Error "Python is required to install Poetry. Please install Python first."
        return
    }

    Write-Step "Installing Poetry using $pythonCmd..."
    $installerContent = (Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content
    $installerContent | & $pythonCmd -

    # Add Poetry to PATH
    $poetryPath = "$env:APPDATA\Python\Scripts"
    if (Test-Path $poetryPath) {
        $env:Path += ";$poetryPath"
    }

    $poetryPath2 = "$env:LOCALAPPDATA\Programs\Python\Python313\Scripts"
    if (Test-Path $poetryPath2) {
        $env:Path += ";$poetryPath2"
    }
    
    $poetryPath3 = "$env:LOCALAPPDATA\Programs\Python\Python312\Scripts"
    if (Test-Path $poetryPath3) {
        $env:Path += ";$poetryPath3"
    }
}

function Install-Git {
    Write-Step "Checking Git installation..."

    if (Test-Command "git") {
        Write-Success "Git is installed"
        return
    }

    Write-Step "Installing Git..."
    choco install git -y

    # Refresh PATH
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
}

function Setup-Backend {
    Write-Step "Setting up backend..."

    Push-Location backend

    try {
        # Get the correct Python command
        $pythonCmd = Get-PythonCommand
        if (-not $pythonCmd) {
            Write-Error "Python is required for backend setup"
            return
        }
        $pythonPath = (Get-Command $pythonCmd).Source
        Write-Step "Using Python: $pythonPath"
        
        # Check if Poetry's virtualenv works by testing it directly
        Write-Step "Checking Poetry virtual environment..."
        $envWorks = $false
        
        # Suppress errors and test if poetry can run python
        $testOutput = poetry run python --version 2>&1
        if ($LASTEXITCODE -eq 0 -and $testOutput -match "Python") {
            Write-Success "Poetry environment is working: $testOutput"
            $envWorks = $true
        } else {
            Write-Warning "Poetry environment is broken or missing"
            Write-Step "Cleaning up old virtual environments..."
            
            # Method 1: Try poetry env remove --all (Poetry 1.2+)
            $null = poetry env remove --all 2>&1
            
            # Method 2: Remove local .venv folder
            if (Test-Path ".venv") {
                Write-Step "Removing .venv folder..."
                Remove-Item -Recurse -Force ".venv" -ErrorAction SilentlyContinue
            }
            
            # Method 3: Find and remove from Poetry's cache directory
            $poetryCacheDir = "$env:LOCALAPPDATA\pypoetry\virtualenvs"
            if (Test-Path $poetryCacheDir) {
                # Find virtualenvs for this project (they start with the project folder name)
                $projectName = (Get-Item .).Name
                $oldEnvs = Get-ChildItem -Path $poetryCacheDir -Directory | Where-Object { $_.Name -like "$projectName-*" }
                foreach ($oldEnv in $oldEnvs) {
                    Write-Step "Removing cached virtualenv: $($oldEnv.Name)"
                    Remove-Item -Recurse -Force $oldEnv.FullName -ErrorAction SilentlyContinue
                }
            }
            
            # Method 4: Also check alternative cache location
            $poetryCacheDir2 = "$env:APPDATA\pypoetry\virtualenvs"
            if (Test-Path $poetryCacheDir2) {
                $projectName = (Get-Item .).Name
                $oldEnvs = Get-ChildItem -Path $poetryCacheDir2 -Directory | Where-Object { $_.Name -like "$projectName-*" }
                foreach ($oldEnv in $oldEnvs) {
                    Write-Step "Removing cached virtualenv: $($oldEnv.Name)"
                    Remove-Item -Recurse -Force $oldEnv.FullName -ErrorAction SilentlyContinue
                }
            }
            
            # Now create a new virtualenv with the correct Python
            Write-Step "Creating new virtual environment with: $pythonPath"
            poetry env use $pythonPath 2>&1
            
            if ($LASTEXITCODE -ne 0) {
                Write-Error "Failed to create Poetry virtual environment"
                Write-Warning "Try manually running: poetry env use `"$pythonPath`""
                return
            }
            
            Write-Success "New virtual environment created"
        }
        
        # Install dependencies
        Write-Step "Installing Python dependencies..."
        poetry install --with dev
        
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Failed to install dependencies"
            return
        }

        # Create .env if it doesn't exist
        if (-not (Test-Path ".env")) {
            Write-Step "Creating .env file..."

            # Generate encryption key using Poetry's Python (now that it works)
            $encryptionKey = poetry run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>&1
            
            if ($LASTEXITCODE -ne 0) {
                # Fallback to system Python
                Write-Warning "Using system Python for key generation"
                $encryptionKey = & $pythonCmd -c "import secrets; print(secrets.token_urlsafe(32))"
            }

            if (Test-Path ".env.example") {
                Copy-Item ".env.example" ".env"
                $content = Get-Content ".env" -Raw
                if ($content -match "MASTER_ENCRYPTION_KEY=") {
                    $content = $content -replace "MASTER_ENCRYPTION_KEY=.*", "MASTER_ENCRYPTION_KEY=$encryptionKey"
                } else {
                    $content += "`nMASTER_ENCRYPTION_KEY=$encryptionKey"
                }
                Set-Content ".env" $content
            } else {
                @"
# BreezeRun Backend Configuration
DATABASE_URL=sqlite+aiosqlite:///./data/breezerun.db
HOST=127.0.0.1
PORT=8000
CORS_ORIGINS=http://localhost:3000,http://localhost:5173,http://localhost:5174
DOCKER_CONTAINER_POOL_SIZE=5
MASTER_ENCRYPTION_KEY=$encryptionKey
"@ | Set-Content ".env"
            }

            Write-Success ".env file created with encryption key"
        }

        # Create data directory
        if (-not (Test-Path "data")) {
            New-Item -ItemType Directory -Path "data" | Out-Null
        }
        
        # Final verification
        Write-Step "Verifying backend setup..."
        $finalTest = poetry run python --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Backend setup complete! Python: $finalTest"
        } else {
            Write-Error "Backend setup may have issues. Test with: cd backend; poetry run python --version"
        }
    }
    finally {
        Pop-Location
    }
}

function Setup-Frontend {
    Write-Step "Setting up frontend..."

    Push-Location frontend

    try {
        # Install dependencies
        npm install
    }
    finally {
        Pop-Location
    }
}

function Build-DockerImages {
    $dockerAvailable = $false
    
    if (Test-Command "docker") {
        # Check if Docker daemon is running
        $null = docker info 2>&1
        if ($?) {
            $dockerAvailable = $true
        }
    }
    
    if ($dockerAvailable) {
        Write-Step "Building Docker sandbox images..."

        Push-Location "backend\app\core\sandbox\environments"

        try {
            # Build only the default Python image for quick setup
            if (Test-Path "python3.13.Dockerfile") {
                docker build -t breezerun-env-python3.13:latest -f python3.13.Dockerfile .
                if (-not $?) {
                    Write-Warning "Failed to build Python 3.13 image"
                }
            }
        }
        finally {
            Pop-Location
        }

        Write-Success "Docker images built"
    } else {
        Write-Warning "Docker is not running. Skipping Docker image build."
        Write-Warning "Start Docker Desktop and run: cd backend\app\core\sandbox\environments; .\build_images.ps1"
    }
}

function Test-Installation {
    Write-Step "Verifying installation..."

    $errors = 0

    $pythonCmd = Get-PythonCommand
    if (-not $pythonCmd) {
        Write-Error "Python is not installed (or only Windows Store stub found)"
        $errors++
    } else {
        $version = Get-PythonVersion
        Write-Success "Python verified: $version (using '$pythonCmd')"
    }

    if (-not (Test-RealNode)) {
        Write-Error "Node.js is not installed"
        $errors++
    } else {
        $nodeVersion = node --version 2>&1
        Write-Success "Node.js verified: $nodeVersion"
    }

    if (-not (Test-Command "poetry")) {
        Write-Error "Poetry is not installed"
        $errors++
    } else {
        Write-Success "Poetry verified"
    }

    if (-not (Test-Command "docker")) {
        Write-Warning "Docker is not installed (optional but recommended)"
    } else {
        Write-Success "Docker verified"
    }

    if ($errors -gt 0) {
        Write-Error "Installation verification failed with $errors errors"
        exit 1
    }

    Write-Success "All required dependencies are installed!"
}

function Write-Usage {
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host "                    Setup Complete!                          " -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "To start BreezeRun:"
    Write-Host ""
    Write-Host "  1. Start the backend:"
    Write-Host "     cd backend"
    Write-Host "     poetry run python -m app.main"
    Write-Host ""
    Write-Host "  2. Start the frontend (in a new terminal):"
    Write-Host "     cd frontend"
    Write-Host "     npm run dev"
    Write-Host ""
    Write-Host "  3. Open http://localhost:5173 in your browser"
    Write-Host ""
    Write-Host "Optional: Build all Docker sandbox images:"
    Write-Host "     cd backend\app\core\sandbox\environments"
    Write-Host "     .\build_images.ps1"
    Write-Host ""
}

# Main
function Main {
    Write-Header

    # Change to script directory
    Set-Location $script:ScriptDirectory

    # Check for admin privileges (recommended for Chocolatey)
    $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if (-not $isAdmin) {
        Write-Warning "Running without administrator privileges. Some installations may fail."
        Write-Warning "Consider running PowerShell as Administrator for best results."
    }

    Install-Chocolatey
    Install-Git
    Install-Python
    Install-NodeJS
    Install-Poetry

    if (-not $SkipDocker) {
        Install-Docker
    }

    Setup-Backend
    Setup-Frontend

    if (-not $SkipDocker) {
        Build-DockerImages
    }

    Test-Installation

    if ($NoStart) {
        Write-Usage
    } else {
        Start-Services
    }
}

function Start-Services {
    Write-Step "Starting BreezeRun services..."

    # Add Poetry to PATH
    $poetryPath = "$env:APPDATA\Python\Scripts"
    if (Test-Path $poetryPath) {
        $env:Path += ";$poetryPath"
    }

    # Use script directory
    $scriptDir = $script:ScriptDirectory
    
    # Verify Poetry can run Python in the backend directory
    Write-Step "Verifying Poetry environment..."
    Push-Location "$scriptDir\backend"
    try {
        $testResult = poetry run python --version 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Poetry cannot run Python. Error: $testResult"
            Write-Warning "Try running: cd backend; poetry env use (Get-Command py).Source"
            Pop-Location
            return
        }
        Write-Success "Poetry Python is working: $testResult"
    } catch {
        Write-Error "Failed to verify Poetry environment: $_"
        Pop-Location
        return
    }
    Pop-Location

    # Start backend in a new window
    Write-Step "Starting backend server..."
    $backendJob = Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-Command", "cd '$scriptDir\backend'; poetry run python -m app.main" -PassThru

    # Wait for backend to be ready
    Write-Step "Waiting for backend to start (max 30 seconds)..."
    $backendReady = $false
    for ($i = 1; $i -le 30; $i++) {
        Start-Sleep -Seconds 1
        try {
            $response = Invoke-WebRequest -Uri http://localhost:8000/ -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -eq 200) {
                Write-Success "Backend is running at http://localhost:8000"
                $backendReady = $true
                break
            }
        } catch {
            # Still waiting...
            if ($i % 10 -eq 0) {
                Write-Host "  Still waiting... ($i seconds)"
            }
        }
    }
    
    if (-not $backendReady) {
        Write-Warning "Backend did not respond within 30 seconds."
        Write-Warning "Check the backend terminal window for errors."
        Write-Warning "Common issues:"
        Write-Warning "  - Poetry virtual environment has wrong Python path"
        Write-Warning "  - Missing dependencies (run: cd backend; poetry install)"
        Write-Warning "  - Port 8000 already in use"
    }

    # Start frontend in a new window
    Write-Step "Starting frontend server..."
    $frontendJob = Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-Command", "cd '$scriptDir\frontend'; npm run dev" -PassThru

    # Wait for frontend to be ready
    Write-Step "Waiting for frontend to start (max 30 seconds)..."
    $frontendReady = $false
    for ($i = 1; $i -le 30; $i++) {
        Start-Sleep -Seconds 1
        try {
            $response = Invoke-WebRequest -Uri http://localhost:5173/ -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -eq 200) {
                Write-Success "Frontend is running at http://localhost:5173"
                $frontendReady = $true
                break
            }
        } catch {
            # Still waiting...
            if ($i % 10 -eq 0) {
                Write-Host "  Still waiting... ($i seconds)"
            }
        }
    }
    
    if (-not $frontendReady) {
        Write-Warning "Frontend did not respond within 30 seconds."
        Write-Warning "Check the frontend terminal window for errors."
    }

    Write-Host ""
    if ($backendReady -and $frontendReady) {
        Write-Host "============================================================" -ForegroundColor Green
        Write-Host "                BreezeRun is running!                        " -ForegroundColor Green
        Write-Host "============================================================" -ForegroundColor Green
    } else {
        Write-Host "============================================================" -ForegroundColor Yellow
        Write-Host "            BreezeRun started with warnings                  " -ForegroundColor Yellow
        Write-Host "============================================================" -ForegroundColor Yellow
    }
    Write-Host ""
    Write-Host "  Backend:  http://localhost:8000"
    Write-Host "  Frontend: http://localhost:5173"
    Write-Host ""
    Write-Host "  Close the terminal windows to stop the services"
    Write-Host ""

    # Open browser if frontend is ready
    if ($frontendReady) {
        Start-Process "http://localhost:5173"
    }
}

Main
