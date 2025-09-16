#!/bin/bash
# VeriWipe Installation Script for Linux Systems

set -e

# Configuration
INSTALL_DIR="/opt/veriwipe"
BIN_DIR="/usr/local/bin"
DESKTOP_DIR="/usr/share/applications"
ICON_DIR="/usr/share/pixmaps"
SERVICE_DIR="/etc/systemd/system"

# Colors
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
BLUE='\\033[0;34m'
NC='\\033[0m'

log() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        error "This script must be run as root"
    fi
}

install_dependencies() {
    log "Installing system dependencies..."
    
    # Detect package manager
    if command -v apt-get >/dev/null 2>&1; then
        apt-get update
        apt-get install -y python3 python3-pip python3-venv
        apt-get install -y hdparm nvme-cli smartmontools cryptsetup
        apt-get install -y util-linux parted gdisk sg3-utils
        apt-get install -y python3-pyqt5 python3-pyqt5.qtwidgets
    elif command -v yum >/dev/null 2>&1; then
        yum install -y python3 python3-pip
        yum install -y hdparm nvme-cli smartmontools cryptsetup
        yum install -y util-linux parted gdisk sg3_utils
        yum install -y python3-qt5
    elif command -v pacman >/dev/null 2>&1; then
        pacman -S --noconfirm python python-pip
        pacman -S --noconfirm hdparm nvme-cli smartmontools cryptsetup
        pacman -S --noconfirm util-linux parted gptfdisk sg3_utils
        pacman -S --noconfirm python-pyqt5
    else
        error "Unsupported package manager. Please install dependencies manually."
    fi
    
    success "System dependencies installed"
}

create_directories() {
    log "Creating directories..."
    
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$INSTALL_DIR/keys"
    mkdir -p "$INSTALL_DIR/models"
    mkdir -p "$INSTALL_DIR/logs"
    mkdir -p "/var/log/veriwipe"
    
    success "Directories created"
}

install_veriwipe() {
    log "Installing VeriWipe..."
    
    # Copy source files
    cp -r src "$INSTALL_DIR/"
    cp -r config "$INSTALL_DIR/"
    cp veriwipe.py "$INSTALL_DIR/"
    cp requirements.txt "$INSTALL_DIR/"
    
    # Set up Python virtual environment
    python3 -m venv "$INSTALL_DIR/venv"
    source "$INSTALL_DIR/venv/bin/activate"
    pip install --upgrade pip
    pip install -r "$INSTALL_DIR/requirements.txt"
    
    # Create launcher script
    cat > "$BIN_DIR/veriwipe" << EOF
#!/bin/bash
cd "$INSTALL_DIR"
source venv/bin/activate
export PYTHONPATH="$INSTALL_DIR/src:\\$PYTHONPATH"
python3 veriwipe.py "\\$@"
EOF
    
    chmod +x "$BIN_DIR/veriwipe"
    
    success "VeriWipe installed"
}

create_desktop_entry() {
    log "Creating desktop entry..."
    
    cat > "$DESKTOP_DIR/veriwipe.desktop" << EOF
[Desktop Entry]
Name=VeriWipe
Comment=AI-Powered Secure Data Wiping
Exec=pkexec veriwipe
Icon=veriwipe
Terminal=false
Type=Application
Categories=System;Security;
StartupNotify=true
Keywords=wipe;secure;data;disk;encryption;
EOF
    
    # Create simple icon (placeholder)
    echo "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==" | base64 -d > "$ICON_DIR/veriwipe.png" 2>/dev/null || true
    
    success "Desktop entry created"
}

setup_permissions() {
    log "Setting up permissions..."
    
    # Create udev rules
    cat > "/etc/udev/rules.d/99-veriwipe.rules" << EOF
# VeriWipe disk access rules
SUBSYSTEM=="block", GROUP="disk", MODE="0660"
KERNEL=="sd*", GROUP="disk", MODE="0660"
KERNEL=="nvme*", GROUP="disk", MODE="0660"
KERNEL=="mmc*", GROUP="disk", MODE="0660"
EOF
    
    # Create sudo rules
    cat > "/etc/sudoers.d/veriwipe" << EOF
# VeriWipe sudo rules
%sudo ALL=(ALL) NOPASSWD: /usr/local/bin/veriwipe
%wheel ALL=(ALL) NOPASSWD: /usr/local/bin/veriwipe
EOF
    
    # Set ownership and permissions
    chown -R root:root "$INSTALL_DIR"
    chmod -R 755 "$INSTALL_DIR"
    chmod 600 "$INSTALL_DIR/keys" 2>/dev/null || true
    
    # Reload udev rules
    udevadm control --reload-rules || true
    
    success "Permissions configured"
}

create_verification_service() {
    log "Creating verification service..."
    
    cat > "$SERVICE_DIR/veriwipe-verifier.service" << EOF
[Unit]
Description=VeriWipe Certificate Verification Service
After=network.target

[Service]
Type=simple
User=veriwipe
Group=veriwipe
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python verification/web_verifier.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    # Create service user
    useradd -r -s /bin/false -d "$INSTALL_DIR" veriwipe 2>/dev/null || true
    
    success "Verification service created"
}

show_completion_message() {
    echo ""
    success "VeriWipe installation completed successfully!"
    echo ""
    echo "Usage:"
    echo "  veriwipe                 # Launch GUI"
    echo "  veriwipe --cli           # CLI mode"
    echo "  veriwipe --info          # System information"
    echo "  veriwipe --verify cert   # Verify certificate"
    echo ""
    echo "Files installed to: $INSTALL_DIR"
    echo "Desktop entry created for GUI access"
    echo ""
    echo "For verification service:"
    echo "  systemctl enable veriwipe-verifier"
    echo "  systemctl start veriwipe-verifier"
    echo ""
    warn "Important: VeriWipe requires root privileges for disk operations"
    echo ""
}

uninstall() {
    log "Uninstalling VeriWipe..."
    
    # Stop and disable service
    systemctl stop veriwipe-verifier 2>/dev/null || true
    systemctl disable veriwipe-verifier 2>/dev/null || true
    
    # Remove files
    rm -rf "$INSTALL_DIR"
    rm -f "$BIN_DIR/veriwipe"
    rm -f "$DESKTOP_DIR/veriwipe.desktop"
    rm -f "$ICON_DIR/veriwipe.png"
    rm -f "$SERVICE_DIR/veriwipe-verifier.service"
    rm -f "/etc/udev/rules.d/99-veriwipe.rules"
    rm -f "/etc/sudoers.d/veriwipe"
    
    # Remove user
    userdel veriwipe 2>/dev/null || true
    
    success "VeriWipe uninstalled"
}

main() {
    echo "VeriWipe Installation Script"
    echo "============================"
    
    case "${1:-install}" in
        install)
            check_root
            install_dependencies
            create_directories
            install_veriwipe
            create_desktop_entry
            setup_permissions
            create_verification_service
            show_completion_message
            ;;
        uninstall)
            check_root
            uninstall
            ;;
        *)
            echo "Usage: $0 [install|uninstall]"
            exit 1
            ;;
    esac
}

main "$@"