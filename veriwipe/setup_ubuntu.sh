#!/bin/bash
# VeriWipe Ubuntu Setup and Troubleshooting Script
# Run this in your Ubuntu VM to fix dependency issues

set -e

echo "🔧 VeriWipe Ubuntu Setup & Troubleshooting"
echo "=========================================="

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

# Install system dependencies
install_system_deps() {
    log "Installing system dependencies..."
    
    # Essential build tools
    sudo apt install -y \
        python3 \
        python3-pip \
        python3-dev \
        python3-venv \
        build-essential \
        git \
        curl \
        wget
    
    # PyQt5 system dependencies
    sudo apt install -y \
        python3-pyqt5 \
        python3-pyqt5.qtcore \
        python3-pyqt5.qtgui \
        python3-pyqt5.qtwidgets \
        qtbase5-dev \
        qt5-qmake \
        qtbase5-dev-tools
    
    # Cryptography dependencies
    sudo apt install -y \
        libssl-dev \
        libffi-dev \
        libcairo2-dev \
        libpango1.0-dev \
        libgdk-pixbuf2.0-dev \
        libxml2-dev \
        libxslt1-dev
    
    # Storage/disk utilities
    sudo apt install -y \
        hdparm \
        nvme-cli \
        smartmontools \
        parted \
        util-linux
    
    success "System dependencies installed"
}

# Create virtual environment
setup_venv() {
    log "Setting up Python virtual environment..."
    
    if [ -d "venv" ]; then
        warn "Virtual environment already exists. Removing..."
        rm -rf venv
    fi
    
    python3 -m venv venv
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    success "Virtual environment created"
}

# Install Python dependencies
install_python_deps() {
    log "Installing Python dependencies..."
    
    # Make sure we're in venv
    if [[ "$VIRTUAL_ENV" == "" ]]; then
        source venv/bin/activate
    fi
    
    # Install dependencies one by one for better error tracking
    log "Installing NumPy..."
    pip install numpy>=1.21.0
    
    log "Installing SciPy..."
    pip install scipy>=1.7.0
    
    log "Installing scikit-learn..."
    pip install scikit-learn>=1.0.0
    
    log "Installing cryptography..."
    pip install cryptography>=3.4.8
    
    log "Installing PyQt5..."
    pip install PyQt5>=5.15.4
    
    log "Installing ReportLab..."
    pip install reportlab>=3.6.0
    
    log "Installing QRCode..."
    pip install "qrcode[pil]>=7.3.1"
    
    log "Installing psutil..."
    pip install psutil>=5.8.0
    
    log "Installing pycryptodome..."
    pip install pycryptodome>=3.15.0
    
    log "Installing Flask..."
    pip install flask>=2.0.0
    
    log "Installing Pillow..."
    pip install pillow>=8.0.0
    
    # Install from requirements.txt as backup
    if [ -f "requirements.txt" ]; then
        log "Installing from requirements.txt..."
        pip install -r requirements.txt
    fi
    
    success "Python dependencies installed"
}

# Test imports
test_imports() {
    log "Testing Python imports..."
    
    if [[ "$VIRTUAL_ENV" == "" ]]; then
        source venv/bin/activate
    fi
    
    python3 -c "
import sys
print(f'Python version: {sys.version}')

try:
    import PyQt5
    print('✅ PyQt5: OK')
except ImportError as e:
    print(f'❌ PyQt5: {e}')

try:
    import cryptography
    print('✅ cryptography: OK')
except ImportError as e:
    print(f'❌ cryptography: {e}')

try:
    import reportlab
    print('✅ reportlab: OK')
except ImportError as e:
    print(f'❌ reportlab: {e}')

try:
    import qrcode
    print('✅ qrcode: OK')
except ImportError as e:
    print(f'❌ qrcode: {e}')

try:
    import sklearn
    print('✅ scikit-learn: OK')
except ImportError as e:
    print(f'❌ scikit-learn: {e}')

try:
    import numpy
    print('✅ numpy: OK')
except ImportError as e:
    print(f'❌ numpy: {e}')

try:
    import psutil
    print('✅ psutil: OK')
except ImportError as e:
    print(f'❌ psutil: {e}')
"
    
    success "Import test completed"
}

# Test VeriWipe launch
test_veriwipe() {
    log "Testing VeriWipe launch..."
    
    if [[ "$VIRTUAL_ENV" == "" ]]; then
        source venv/bin/activate
    fi
    
    if [ ! -f "veriwipe.py" ]; then
        error "veriwipe.py not found in current directory"
        return 1
    fi
    
    log "Testing dependency check..."
    python3 -c "
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname('__file__'), 'src'))

def check_dependencies():
    missing_deps = []
    
    try:
        import PyQt5
    except ImportError:
        missing_deps.append('PyQt5')
    
    try:
        import cryptography
    except ImportError:
        missing_deps.append('cryptography')
    
    try:
        import reportlab
    except ImportError:
        missing_deps.append('reportlab')
    
    try:
        import qrcode
    except ImportError:
        missing_deps.append('qrcode')
    
    if missing_deps:
        print(f'Missing dependencies: {missing_deps}')
        return False
    else:
        print('✅ All dependencies available')
        return True

check_dependencies()
"
    
    success "VeriWipe dependency check completed"
}

# Main setup function
main() {
    echo
    log "Starting VeriWipe setup..."
    
    check_root
    echo
    
    read -p "Update system packages? (y/N): " update_sys
    if [[ $update_sys =~ ^[Yy]$ ]]; then
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
    
    success "Setup completed!"
    echo
    log "To run VeriWipe:"
    echo "  1. Activate virtual environment: source venv/bin/activate"
    echo "  2. Run with GUI: sudo ./venv/bin/python veriwipe.py --gui"
    echo "  3. Or run CLI: sudo ./venv/bin/python veriwipe.py --help"
    echo
    warn "Note: VeriWipe requires root privileges for disk operations"
}

# Run if executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi