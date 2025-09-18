#!/bin/bash
# VeriWipe Ubuntu Setup and Troubleshooting Script
# Enhanced with AI-powered dependency management

set -e

echo "🔧 VeriWipe Smart Ubuntu Setup"
echo "=============================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        warn "Running as root. This is OK for system setup."
    else
        log "Running as regular user. Will use sudo when needed."
    fi
}

# Update system packages
update_system() {
    log "Updating system packages..."
    sudo apt update
    sudo apt upgrade -y
    success "System updated"
}

# Install comprehensive system dependencies
install_system_deps() {
    log "Installing comprehensive system dependencies..."
    
    # Essential build tools and Python
    log "Installing Python environment..."
    sudo apt install -y \
        python3 \
        python3-pip \
        python3-dev \
        python3-venv \
        build-essential \
        git \
        curl \
        wget \
        software-properties-common
    
    # PyQt5 system dependencies with all components
    log "Installing GUI framework..."
    sudo apt install -y \
        python3-pyqt5 \
        python3-pyqt5.qtcore \
        python3-pyqt5.qtgui \
        python3-pyqt5.qtwidgets \
        python3-pyqt5.qtsvg \
        qtbase5-dev \
        qt5-qmake \
        qtbase5-dev-tools \
        libxcb-xinerama0 \
        libxcb1 \
        libx11-xcb1 \
        libxrender1 \
        libxkbcommon-x11-0 \
        libglu1-mesa
    
    # Cryptography and security dependencies
    log "Installing security libraries..."
    sudo apt install -y \
        libssl-dev \
        libffi-dev \
        libcairo2-dev \
        libpango1.0-dev \
        libgdk-pixbuf2.0-dev \
        libxml2-dev \
        libxslt1-dev
    
    # Storage/disk utilities
    log "Installing disk utilities..."
    sudo apt install -y \
        hdparm \
        nvme-cli \
        smartmontools \
        parted \
        util-linux \
        cryptsetup \
        lsscsi \
        sg3-utils \
        sdparm
    
    # AI/ML system dependencies
    log "Installing AI/ML system libraries..."
    sudo apt install -y \
        python3-numpy \
        python3-scipy \
        python3-sklearn \
        libblas-dev \
        liblapack-dev \
        gfortran
    
    success "System dependencies installed"
}

# Create or update virtual environment
setup_venv() {
    log "Setting up Python virtual environment..."
    
    if [ -d "venv" ]; then
        warn "Virtual environment already exists. Recreating..."
        rm -rf venv
    fi
    
    # Create venv with system packages for better compatibility
    python3 -m venv venv --system-site-packages
    source venv/bin/activate
    
    # Upgrade pip and core tools
    pip install --upgrade pip setuptools wheel
    
    success "Virtual environment created"
}

# Install Python dependencies with error handling
install_python_deps() {
    log "Installing Python dependencies..."
    
    # Make sure we're in venv
    if [[ "$VIRTUAL_ENV" == "" ]]; then
        source venv/bin/activate
    fi
    
    # Install dependencies with specific versions for stability
    log "Installing core scientific libraries..."
    pip install \
        numpy>=1.21.0 \
        scipy>=1.7.0 \
        scikit-learn>=1.0.0
    
    log "Installing GUI framework..."
    pip install PyQt5>=5.15.4
    
    log "Installing security libraries..."
    pip install \
        cryptography>=3.4.8 \
        pycryptodome>=3.15.0
    
    log "Installing document generation..."
    pip install \
        reportlab>=3.6.0 \
        "qrcode[pil]>=7.3.1" \
        pillow>=8.0.0
    
    log "Installing system utilities..."
    pip install \
        psutil>=5.8.0 \
        flask>=2.0.0
    
    log "Installing ML support libraries..."
    pip install \
        joblib \
        threadpoolctl
    
    # Install from requirements.txt as final step
    if [ -f "requirements.txt" ]; then
        log "Installing from requirements.txt..."
        pip install -r requirements.txt
    fi
    
    success "Python dependencies installed"
}

# Test all imports comprehensively
test_imports() {
    log "Testing Python imports..."
    
    if [[ "$VIRTUAL_ENV" == "" ]]; then
        source venv/bin/activate
    fi
    
    python3 -c "
import sys
print(f'🐍 Python version: {sys.version}')
print()

# Test core dependencies
deps = [
    ('PyQt5', 'GUI Framework'),
    ('cryptography', 'Security Library'),
    ('reportlab', 'PDF Generation'),
    ('qrcode', 'QR Code Generation'),
    ('sklearn', 'Machine Learning'),
    ('numpy', 'Numerical Computing'),
    ('scipy', 'Scientific Computing'),
    ('psutil', 'System Utilities'),
    ('flask', 'Web Framework'),
    ('PIL', 'Image Processing')
]

all_ok = True
for module, description in deps:
    try:
        if module == 'sklearn':
            import sklearn
        elif module == 'PIL':
            import PIL
        else:
            __import__(module)
        print(f'✅ {module:12} ({description})')
    except ImportError as e:
        print(f'❌ {module:12} ({description}) - {e}')
        all_ok = False

print()
if all_ok:
    print('✅ All dependencies successfully imported!')
else:
    print('❌ Some dependencies failed to import')
    sys.exit(1)
"
    
    success "Import test completed successfully"
}

# Test VeriWipe functionality
test_veriwipe() {
    log "Testing VeriWipe functionality..."
    
    if [[ "$VIRTUAL_ENV" == "" ]]; then
        source venv/bin/activate
    fi
    
    if [ ! -f "veriwipe.py" ]; then
        error "veriwipe.py not found in current directory"
        return 1
    fi
    
    log "Testing smart dependency manager..."
    python3 -c "
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname('__file__'), 'src'))

try:
    from utils.smart_dependency_manager import smart_dependency_check
    if smart_dependency_check():
        print('✅ Smart dependency check passed')
    else:
        print('❌ Smart dependency check failed')
        sys.exit(1)
except ImportError:
    print('⚠️ Smart dependency manager not found, testing basic dependencies...')
    
    # Test basic imports
    try:
        import PyQt5, cryptography, reportlab, qrcode
        print('✅ Basic dependencies available')
    except ImportError as e:
        print(f'❌ Basic dependency missing: {e}')
        sys.exit(1)
except Exception as e:
    print(f'❌ Dependency test error: {e}')
    sys.exit(1)
"
    
    success "VeriWipe dependency test completed"
}

# Create convenient launcher scripts
create_launchers() {
    log "Creating launcher scripts..."
    
    # Create smart launcher
    cat > veriwipe_launcher.sh << 'LAUNCHER'
#!/bin/bash
# VeriWipe Smart Launcher for development environment

# Navigate to script directory
cd "$(dirname "$0")"

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "❌ Virtual environment not found. Run ./setup_ubuntu.sh first."
    exit 1
fi

# Set environment
export PYTHONPATH="$(pwd)/src:$PYTHONPATH"
export QT_QPA_PLATFORM_PLUGIN_PATH=/usr/lib/x86_64-linux-gnu/qt5/plugins/platforms

# Check for root if needed
if [ "$1" != "--check-only" ] && [ "$(id -u)" -ne 0 ]; then
    echo "🔐 VeriWipe requires root privileges for disk operations"
    exec sudo -E "$0" "$@"
fi

# Run VeriWipe
if [ "$1" = "--cli" ]; then
    python3 veriwipe.py --cli "${@:2}"
else
    python3 veriwipe.py "${@}"
fi
LAUNCHER
    
    chmod +x veriwipe_launcher.sh
    
    success "Launcher scripts created"
}

# Main setup function
main() {
    echo
    log "Starting comprehensive VeriWipe setup..."
    
    check_root
    echo
    
    read -p "Update system packages? (Y/n): " update_sys
    if [[ ! $update_sys =~ ^[Nn]$ ]]; then
        update_system
        echo
    fi
    
    install_system_deps
    echo
    
    setup_venv
    echo
    
    install_python_deps
    echo
    
    test_imports
    echo
    
    test_veriwipe
    echo
    
    create_launchers
    echo
    
    success "🎉 VeriWipe setup completed successfully!"
    echo
    log "🚀 How to run VeriWipe:"
    echo "  GUI Mode:  ./veriwipe_launcher.sh"
    echo "  CLI Mode:  ./veriwipe_launcher.sh --cli"
    echo "  With venv: source venv/bin/activate && sudo python3 veriwipe.py"
    echo
    warn "💡 VeriWipe requires root privileges for disk operations"
    warn "🔒 Always verify device selection before wiping!"
}

# Command line options
case "${1:-}" in
    --auto-fix)
        log "Running auto-fix mode..."
        main
        ;;
    --test-only)
        log "Running dependency test only..."
        if [ -d "venv" ]; then
            source venv/bin/activate
            test_imports
            test_veriwipe
        else
            error "Virtual environment not found. Run setup first."
        fi
        ;;
    --help)
        echo "VeriWipe Setup Script"
        echo "Usage: $0 [OPTION]"
        echo ""
        echo "Options:"
        echo "  (none)      Interactive setup"
        echo "  --auto-fix  Automatic setup without prompts"
        echo "  --test-only Test existing installation"
        echo "  --help      Show this help"
        ;;
    *)
        main "$@"
        ;;
esac