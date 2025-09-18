#!/bin/bash
# VeriWipe Bootable ISO Builder
# Creates a custom Ubuntu-based live ISO with VeriWipe components

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$SCRIPT_DIR/build"
ISO_DIR="$BUILD_DIR/iso"
WORK_DIR="$BUILD_DIR/work"
OUTPUT_DIR="$SCRIPT_DIR/output"
ISO_NAME="veriwipe-live.iso"

# Ubuntu base ISO (minimal)
UBUNTU_VERSION="22.04.3"
UBUNTU_ISO_URL="https://releases.ubuntu.com/22.04/ubuntu-22.04.3-desktop-amd64.iso"
UBUNTU_ISO="ubuntu-22.04.3-desktop-amd64.iso"

# Colors for output
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
BLUE='\\033[0;34m'
NC='\\033[0m' # No Color

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

check_dependencies() {
    log "Checking dependencies..."
    
    local deps=("wget" "7z" "xorriso" "mksquashfs" "unsquashfs" "chroot" "debootstrap")
    local missing_deps=()
    
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            missing_deps+=("$dep")
        fi
    done
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        error "Missing dependencies: ${missing_deps[*]}\\nInstall with: sudo apt-get install wget p7zip-full xorriso squashfs-tools debootstrap"
    fi
    
    success "All dependencies found"
}

check_permissions() {
    log "Checking permissions..."
    
    if [ "$EUID" -ne 0 ]; then
        error "This script must be run as root for chroot operations"
    fi
    
    success "Running as root"
}

download_ubuntu_iso() {
    log "Downloading Ubuntu base ISO..."
    
    mkdir -p "$BUILD_DIR"
    cd "$BUILD_DIR"
    
    if [ ! -f "$UBUNTU_ISO" ]; then
        log "Downloading $UBUNTU_ISO..."
        wget -O "$UBUNTU_ISO" "$UBUNTU_ISO_URL"
    else
        log "Ubuntu ISO already exists, skipping download"
    fi
    
    success "Ubuntu ISO ready"
}

extract_iso() {
    log "Extracting Ubuntu ISO..."
    
    rm -rf "$ISO_DIR" "$WORK_DIR"
    mkdir -p "$ISO_DIR" "$WORK_DIR"
    
    # Extract ISO contents
    cd "$BUILD_DIR"
    7z x "$UBUNTU_ISO" -o"$ISO_DIR"
    
    # Extract squashfs filesystem
    log "Extracting squashfs filesystem..."
    unsquashfs -d "$WORK_DIR/squashfs-root" "$ISO_DIR/casper/filesystem.squashfs"
    
    success "ISO extracted"
}

customize_filesystem() {
    log "Customizing filesystem..."
    
    local chroot_dir="$WORK_DIR/squashfs-root"
    
    # Mount necessary filesystems for chroot
    mount --bind /dev "$chroot_dir/dev"
    mount --bind /proc "$chroot_dir/proc"
    mount --bind /sys "$chroot_dir/sys"
    mount -t tmpfs tmpfs "$chroot_dir/tmp"
    
    # Copy VeriWipe source code
    log "Installing VeriWipe components..."
    mkdir -p "$chroot_dir/opt/veriwipe"
    cp -r "$PROJECT_ROOT/src" "$chroot_dir/opt/veriwipe/"
    cp -r "$PROJECT_ROOT/config" "$chroot_dir/opt/veriwipe/"
    cp "$PROJECT_ROOT/requirements.txt" "$chroot_dir/opt/veriwipe/"
    
    # Create installation script for chroot
    cat > "$chroot_dir/tmp/install_veriwipe.sh" << 'EOF'
#!/bin/bash
set -e

# Update package lists
apt-get update

# Install Python and dependencies with comprehensive packages
echo "🐍 Installing Python environment..."
apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    python3-venv \
    build-essential \
    git \
    curl \
    wget \
    software-properties-common

# Install PyQt5 and GUI dependencies with all required components
echo "🖥️ Installing GUI dependencies..."
apt-get install -y \
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

# Install cryptography and security libraries
echo "🔐 Installing security dependencies..."
apt-get install -y \
    libssl-dev \
    libffi-dev \
    libcairo2-dev \
    libpango1.0-dev \
    libgdk-pixbuf2.0-dev \
    libxml2-dev \
    libxslt1-dev

# Install system tools for disk operations with comprehensive coverage
echo "💾 Installing disk utilities..."
apt-get install -y \
    hdparm \
    nvme-cli \
    smartmontools \
    cryptsetup \
    util-linux \
    parted \
    gdisk \
    sg3-utils \
    sdparm \
    lsscsi

# Install AI/ML system dependencies
echo "🤖 Installing AI/ML dependencies..."
apt-get install -y \
    python3-numpy \
    python3-scipy \
    python3-sklearn \
    libblas-dev \
    liblapack-dev \
    gfortran

# Create virtual environment for VeriWipe with system packages
echo "📦 Setting up VeriWipe environment..."
python3 -m venv /opt/veriwipe/venv --system-site-packages
source /opt/veriwipe/venv/bin/activate

# Install Python packages with specific versions for stability
echo "📚 Installing Python packages..."
pip install --upgrade pip setuptools wheel
pip install \
    numpy>=1.21.0 \
    scipy>=1.7.0 \
    scikit-learn>=1.0.0 \
    PyQt5>=5.15.4 \
    cryptography>=3.4.8 \
    reportlab>=3.6.0 \
    "qrcode[pil]>=7.3.1" \
    psutil>=5.8.0 \
    pycryptodome>=3.15.0 \
    flask>=2.0.0 \
    pillow>=8.0.0 \
    joblib \
    threadpoolctl

# Install from requirements.txt if available
if [ -f /opt/veriwipe/requirements.txt ]; then
    pip install -r /opt/veriwipe/requirements.txt
fi

# Create smart VeriWipe launcher script with dependency management
cat > /opt/veriwipe/veriwipe_launcher.sh << 'LAUNCHER'
#!/bin/bash
# VeriWipe Smart Launcher - Handles dependencies and environment automatically

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[VeriWipe]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Change to VeriWipe directory
cd /opt/veriwipe

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    log "Environment activated"
else
    error "Virtual environment not found. Please reinstall VeriWipe."
fi

# Set up environment variables
export PYTHONPATH="/opt/veriwipe/src:$PYTHONPATH"
export QT_QPA_PLATFORM_PLUGIN_PATH=/usr/lib/x86_64-linux-gnu/qt5/plugins/platforms

# Check for root privileges if needed for disk operations
if [ "$1" != "--check-only" ] && [ "$(id -u)" -ne 0 ]; then
    log "VeriWipe requires root privileges for disk operations"
    exec sudo -E "$0" "$@"
fi

# Run smart dependency check
log "Verifying dependencies..."
if python3 -c "
import sys
sys.path.insert(0, '/opt/veriwipe/src')
try:
    from utils.smart_dependency_manager import smart_dependency_check
    if smart_dependency_check():
        print('✅ All dependencies satisfied')
    else:
        print('❌ Some dependencies missing')
        sys.exit(1)
except ImportError:
    # Fallback to basic check
    try:
        import PyQt5, cryptography, reportlab, qrcode, sklearn
        print('✅ Basic dependencies OK')
    except ImportError as e:
        print(f'❌ Missing dependency: {e}')
        sys.exit(1)
except Exception as e:
    print(f'⚠️ Dependency check warning: {e}')
    # Continue anyway in live environment
"; then
    success "Ready to launch"
else
    error "Dependency verification failed"
fi

# Launch VeriWipe based on arguments
if [ "$1" = "--cli" ]; then
    log "Starting VeriWipe CLI mode..."
    python3 veriwipe.py --cli "${@:2}"
elif [ "$1" = "--check-only" ]; then
    success "VeriWipe is ready to use"
else
    log "Starting VeriWipe GUI..."
    python3 veriwipe.py "${@}"
fi
LAUNCHER

chmod +x /opt/veriwipe/veriwipe_launcher.sh

# Create enhanced desktop entry
mkdir -p /home/ubuntu/Desktop
cat > /home/ubuntu/Desktop/VeriWipe.desktop << 'DESKTOP'
[Desktop Entry]
Name=VeriWipe - Secure Data Wiping
GenericName=Data Destruction Tool
Comment=AI-Powered Secure Data Wiping with Certificate Generation
Exec=/opt/veriwipe/veriwipe_launcher.sh
Icon=/opt/veriwipe/assets/veriwipe-icon.png
Terminal=false
Type=Application
Categories=System;Security;Utility;
Keywords=wipe;secure;delete;data;destruction;privacy;
StartupNotify=true
DESKTOP

chmod +x /home/ubuntu/Desktop/VeriWipe.desktop

# Create menu entry
mkdir -p /usr/share/applications
cp /home/ubuntu/Desktop/VeriWipe.desktop /usr/share/applications/

# Create CLI shortcut for easy command-line access
cat > /usr/local/bin/veriwipe << 'CLI'
#!/bin/bash
# VeriWipe CLI shortcut
exec /opt/veriwipe/veriwipe_launcher.sh "$@"
CLI

chmod +x /usr/local/bin/veriwipe

# Create icon directory and placeholder
mkdir -p /opt/veriwipe/assets
if [ ! -f "/opt/veriwipe/assets/veriwipe-icon.png" ]; then
    # Try to create a simple icon or use system icon
    convert -size 64x64 xc:blue -fill white -pointsize 20 -gravity center \
            -annotate +0+0 "VW" /opt/veriwipe/assets/veriwipe-icon.png 2>/dev/null || \
    cp /usr/share/pixmaps/ubuntu-logo.png /opt/veriwipe/assets/veriwipe-icon.png 2>/dev/null || \
    echo "Warning: Could not create VeriWipe icon"
fi

# Set up log directory with proper permissions
mkdir -p /var/log/veriwipe
chmod 755 /var/log/veriwipe

# Create welcome message script
cat > /opt/veriwipe/welcome.sh << 'WELCOME'
#!/bin/bash
echo "=================================================="
echo "🛡️  VeriWipe Live Environment Ready!"
echo "=================================================="
echo ""
echo "🚀 Quick Start:"
echo "   Desktop: Double-click VeriWipe icon"
echo "   Terminal: type 'veriwipe' or 'veriwipe --cli'"
echo ""
echo "🎯 Features:"
echo "   • AI-powered device detection"
echo "   • NIST-compliant secure wiping" 
echo "   • Tamper-proof certificates"
echo "   • Real-time progress tracking"
echo ""
echo "⚠️  Safety: Always verify device before wiping!"
echo "📖 Help: veriwipe --help"
echo "=================================================="
WELCOME

chmod +x /opt/veriwipe/welcome.sh

# Add welcome to bashrc for user guidance
echo "" >> /home/ubuntu/.bashrc
echo "# VeriWipe live environment" >> /home/ubuntu/.bashrc
echo "/opt/veriwipe/welcome.sh" >> /home/ubuntu/.bashrc

# Create AI models directory
mkdir -p /opt/veriwipe/models

# Clean up
apt-get autoremove -y
apt-get clean
rm -rf /var/lib/apt/lists/*
rm -rf /tmp/*
rm -rf /var/tmp/*

echo "VeriWipe installation completed"
EOF
    
    chmod +x "$chroot_dir/tmp/install_veriwipe.sh"
    
    # Execute installation in chroot
    log "Running installation in chroot environment..."
    chroot "$chroot_dir" /bin/bash -c "/tmp/install_veriwipe.sh"
    
    # Copy additional configuration files
    log "Installing configuration files..."
    
    # Create VeriWipe icon
    mkdir -p "$chroot_dir/opt/veriwipe/config"
    cat > "$chroot_dir/opt/veriwipe/config/veriwipe-icon.png.b64" << 'ICON'
iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==
ICON
    
    # Decode base64 icon (placeholder - in real implementation, use actual icon)
    base64 -d "$chroot_dir/opt/veriwipe/config/veriwipe-icon.png.b64" > "$chroot_dir/opt/veriwipe/config/veriwipe-icon.png" || true
    
    # Create startup script that runs VeriWipe automatically
    cat > "$chroot_dir/opt/veriwipe/autostart.sh" << 'AUTOSTART'
#!/bin/bash
# Wait for desktop to load
sleep 5

# Check if running in live environment
if [ -f /rofs/etc/casper.conf ] || [ -f /etc/casper.conf ]; then
    # Show welcome message
    zenity --info --title="VeriWipe Live Environment" --text="Welcome to VeriWipe Live Environment!\\n\\nThis system is designed for secure data wiping.\\n\\nVeriWipe will start automatically.\\n\\nPlease ensure you have backed up any important data before proceeding." --width=400 2>/dev/null || true
    
    # Start VeriWipe
    /opt/veriwipe/veriwipe.sh
fi
AUTOSTART
    
    chmod +x "$chroot_dir/opt/veriwipe/autostart.sh"
    
    # Add autostart to .bashrc for ubuntu user
    echo "/opt/veriwipe/autostart.sh &" >> "$chroot_dir/home/ubuntu/.bashrc"
    
    # Set ownership for ubuntu user
    chroot "$chroot_dir" chown -R ubuntu:ubuntu /home/ubuntu
    
    # Unmount filesystems
    umount "$chroot_dir/tmp" || true
    umount "$chroot_dir/sys" || true
    umount "$chroot_dir/proc" || true
    umount "$chroot_dir/dev" || true
    
    success "Filesystem customized"
}

create_squashfs() {
    log "Creating new squashfs filesystem..."
    
    cd "$WORK_DIR"
    
    # Remove old filesystem
    rm -f "$ISO_DIR/casper/filesystem.squashfs"
    
    # Create new squashfs with better compression
    mksquashfs squashfs-root "$ISO_DIR/casper/filesystem.squashfs" \\
        -comp xz -Xbcj x86 -b 1048576 -Xdict-size 100% \\
        -e boot
    
    # Update filesystem size
    printf $(du -sx --block-size=1 squashfs-root | cut -f1) > "$ISO_DIR/casper/filesystem.size"
    
    success "Squashfs created"
}

create_iso() {
    log "Creating bootable ISO..."
    
    mkdir -p "$OUTPUT_DIR"
    
    cd "$ISO_DIR"
    
    # Update md5sums
    find . -type f -print0 | xargs -0 md5sum | grep -v isolinux/boot.cat | tee md5sum.txt
    
    # Create the ISO
    xorriso -as mkisofs \\
        -isohybrid-mbr /usr/lib/ISOLINUX/isohdpfx.bin \\
        -c isolinux/boot.cat \\
        -b isolinux/isolinux.bin \\
        -no-emul-boot \\
        -boot-load-size 4 \\
        -boot-info-table \\
        -eltorito-alt-boot \\
        -e boot/grub/efi.img \\
        -no-emul-boot \\
        -isohybrid-gpt-basdat \\
        -isohybrid-apm-hfsplus \\
        -volid "VeriWipe Live" \\
        -o "$OUTPUT_DIR/$ISO_NAME" \\
        .
    
    success "ISO created: $OUTPUT_DIR/$ISO_NAME"
}

update_grub_config() {
    log "Updating GRUB configuration..."
    
    # Update isolinux configuration
    cat > "$ISO_DIR/isolinux/txt.cfg" << 'EOF'
default live
label live
  menu label ^Try VeriWipe Live
  kernel /casper/vmlinuz
  append initrd=/casper/initrd boot=casper quiet splash ---
label live-nomodeset
  menu label ^Try VeriWipe Live (safe graphics)
  kernel /casper/vmlinuz
  append initrd=/casper/initrd boot=casper nomodeset quiet splash ---
EOF

    # Update GRUB configuration
    if [ -f "$ISO_DIR/boot/grub/grub.cfg" ]; then
        sed -i 's/Ubuntu/VeriWipe Live/g' "$ISO_DIR/boot/grub/grub.cfg"
        sed -i 's/Try Ubuntu/Try VeriWipe/g' "$ISO_DIR/boot/grub/grub.cfg"
    fi
    
    success "GRUB configuration updated"
}

create_hybrid_iso() {
    log "Making ISO hybrid (USB bootable)..."
    
    if command -v isohybrid &> /dev/null; then
        isohybrid "$OUTPUT_DIR/$ISO_NAME"
        success "ISO made hybrid for USB booting"
    else
        warn "isohybrid not found, ISO may not be USB bootable"
    fi
}

cleanup() {
    log "Cleaning up..."
    
    # Unmount any remaining mounts
    for mount_point in "$WORK_DIR/squashfs-root/dev" "$WORK_DIR/squashfs-root/proc" "$WORK_DIR/squashfs-root/sys" "$WORK_DIR/squashfs-root/tmp"; do
        if mountpoint -q "$mount_point" 2>/dev/null; then
            umount "$mount_point" || true
        fi
    done
    
    # Remove build directory (optional - comment out for debugging)
    # rm -rf "$BUILD_DIR"
    
    success "Cleanup completed"
}

show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo "  -c, --clean    Clean build directory before building"
    echo "  -k, --keep     Keep build directory after building (default)"
    echo "  -o, --output   Output directory (default: ./output)"
    echo ""
    echo "This script creates a bootable VeriWipe Live ISO for secure data wiping."
}

main() {
    local clean_build=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            -c|--clean)
                clean_build=true
                shift
                ;;
            -k|--keep)
                # Default behavior
                shift
                ;;
            -o|--output)
                OUTPUT_DIR="$2"
                shift 2
                ;;
            *)
                error "Unknown option: $1"
                ;;
        esac
    done
    
    log "Starting VeriWipe Live ISO build..."
    log "Project root: $PROJECT_ROOT"
    log "Build directory: $BUILD_DIR"
    log "Output directory: $OUTPUT_DIR"
    
    # Clean build directory if requested
    if [ "$clean_build" = true ]; then
        log "Cleaning build directory..."
        rm -rf "$BUILD_DIR"
    fi
    
    # Execute build steps
    check_dependencies
    check_permissions
    download_ubuntu_iso
    extract_iso
    update_grub_config
    customize_filesystem
    create_squashfs
    create_iso
    create_hybrid_iso
    
    # Show final results
    echo ""
    success "VeriWipe Live ISO build completed successfully!"
    echo ""
    echo "Output ISO: $OUTPUT_DIR/$ISO_NAME"
    echo "Size: $(du -h "$OUTPUT_DIR/$ISO_NAME" | cut -f1)"
    echo ""
    echo "To create a bootable USB drive:"
    echo "  sudo dd if=$OUTPUT_DIR/$ISO_NAME of=/dev/sdX bs=4M status=progress"
    echo "  (Replace /dev/sdX with your USB device)"
    echo ""
    echo "Or use a tool like Etcher, Rufus, or UNetbootin."
    echo ""
    
    cleanup
}

# Handle interrupts
trap cleanup EXIT INT TERM

# Run main function
main "$@"