#!/bin/bash
# VeriWipe Live Environment Setup Script
# This script customizes the live environment for VeriWipe

set -e

# Configuration
VERIWIPE_HOME="/opt/veriwipe"
DESKTOP_DIR="/home/ubuntu/Desktop"
AUTOSTART_DIR="/home/ubuntu/.config/autostart"

log() {
    echo "[SETUP] $1"
}

error() {
    echo "[ERROR] $1"
    exit 1
}

setup_permissions() {
    log "Setting up permissions for disk access..."
    
    # Add ubuntu user to necessary groups
    usermod -a -G disk,sudo ubuntu
    
    # Create udev rules for disk access
    cat > /etc/udev/rules.d/99-veriwipe.rules << 'EOF'
# VeriWipe disk access rules
SUBSYSTEM=="block", GROUP="disk", MODE="0660"
KERNEL=="sd*", GROUP="disk", MODE="0660"
KERNEL=="nvme*", GROUP="disk", MODE="0660"
KERNEL=="mmc*", GROUP="disk", MODE="0660"
EOF
    
    # Set up sudo rules for VeriWipe operations
    cat > /etc/sudoers.d/veriwipe << 'EOF'
# VeriWipe sudo rules
ubuntu ALL=(ALL) NOPASSWD: /usr/bin/hdparm
ubuntu ALL=(ALL) NOPASSWD: /usr/bin/nvme
ubuntu ALL=(ALL) NOPASSWD: /usr/sbin/cryptsetup
ubuntu ALL=(ALL) NOPASSWD: /bin/dd
ubuntu ALL=(ALL) NOPASSWD: /usr/bin/shred
ubuntu ALL=(ALL) NOPASSWD: /sbin/blkdiscard
ubuntu ALL=(ALL) NOPASSWD: /bin/mount
ubuntu ALL=(ALL) NOPASSWD: /bin/umount
EOF
    
    log "Permissions configured"
}

setup_desktop_environment() {
    log "Setting up desktop environment..."
    
    # Create desktop directories
    mkdir -p "$DESKTOP_DIR"
    mkdir -p "$AUTOSTART_DIR"
    mkdir -p "/home/ubuntu/.config"
    
    # Create VeriWipe desktop shortcut
    cat > "$DESKTOP_DIR/VeriWipe.desktop" << 'EOF'
[Desktop Entry]
Version=1.0
Name=VeriWipe
Comment=AI-Powered Secure Data Wiping
Exec=sudo -E /opt/veriwipe/veriwipe.sh
Icon=/opt/veriwipe/config/veriwipe-icon.png
Terminal=false
Type=Application
Categories=System;Security;
StartupNotify=true
EOF
    
    chmod +x "$DESKTOP_DIR/VeriWipe.desktop"
    
    # Create documentation shortcut
    cat > "$DESKTOP_DIR/VeriWipe-Help.desktop" << 'EOF'
[Desktop Entry]
Version=1.0
Name=VeriWipe Documentation
Comment=VeriWipe User Guide and Documentation
Exec=firefox /opt/veriwipe/docs/user-guide.html
Icon=help-browser
Terminal=false
Type=Application
Categories=Documentation;
EOF
    
    chmod +x "$DESKTOP_DIR/VeriWipe-Help.desktop"
    
    # Create system information shortcut
    cat > "$DESKTOP_DIR/System-Info.desktop" << 'EOF'
[Desktop Entry]
Version=1.0
Name=System Information
Comment=View system and hardware information
Exec=hardinfo
Icon=computer
Terminal=false
Type=Application
Categories=System;
EOF
    
    chmod +x "$DESKTOP_DIR/System-Info.desktop"
    
    # Set ownership
    chown -R ubuntu:ubuntu /home/ubuntu
    
    log "Desktop environment configured"
}

setup_boot_configuration() {
    log "Setting up boot configuration..."
    
    # Create custom boot splash
    cat > /etc/plymouth/themes/veriwipe/veriwipe.plymouth << 'EOF'
[Plymouth Theme]
Name=VeriWipe
Description=VeriWipe Secure Data Wiping Live Environment
ModuleName=script

[script]
ImageDir=/etc/plymouth/themes/veriwipe
ScriptFile=/etc/plymouth/themes/veriwipe/veriwipe.script
EOF
    
    # Create boot message
    cat > /etc/motd << 'EOF'
 _   _           _ _    _ _            
| | | |         (_) |  | (_)           
| | | | ___ _ __ _| |  | |_ _ __   ___  
| | | |/ _ \ '__| | |/\| | | '_ \ / _ \ 
\ \_/ /  __/ |  | \  /\  / | |_) |  __/ 
 \___/ \___|_|  |_|\/  \/_/| .__/ \___| 
                           | |          
                           |_|          

VeriWipe Live Environment
AI-Powered Secure Data Wiping for Trustworthy IT Asset Recycling

IMPORTANT SECURITY NOTICE:
- This environment is designed for secure data wiping
- All operations are logged and tamper-evident
- Ensure you have proper authorization before wiping any device
- Back up any important data before proceeding

For documentation and help, see the desktop shortcuts.

Team: 4× Cybersecurity | 1× Blockchain | 1× Quantum
Event: Smart India Hackathon 2025
Problem Statement ID: 25070
EOF
    
    log "Boot configuration completed"
}

setup_networking() {
    log "Setting up networking configuration..."
    
    # Create network configuration that allows optional connectivity
    cat > /etc/netplan/99-veriwipe.yaml << 'EOF'
network:
  version: 2
  renderer: networkd
  ethernets:
    eth0:
      dhcp4: true
      optional: true
  wifis:
    wlan0:
      dhcp4: true
      optional: true
      access-points:
        "VeriWipe-Setup":
          password: "veriwipe2025"
EOF
    
    log "Networking configured"
}

create_documentation() {
    log "Creating user documentation..."
    
    mkdir -p "$VERIWIPE_HOME/docs"
    
    cat > "$VERIWIPE_HOME/docs/user-guide.html" << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>VeriWipe User Guide</title>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
        .header { background: #2c5282; color: white; padding: 20px; border-radius: 10px; }
        .section { margin: 20px 0; }
        .warning { background: #fef2f2; border-left: 4px solid #f87171; padding: 15px; }
        .info { background: #eff6ff; border-left: 4px solid #3b82f6; padding: 15px; }
        .success { background: #f0fdf4; border-left: 4px solid #22c55e; padding: 15px; }
        code { background: #f1f5f9; padding: 2px 5px; border-radius: 3px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🛡️ VeriWipe User Guide</h1>
        <p>AI-Powered Secure Data Wiping for Trustworthy IT Asset Recycling</p>
    </div>
    
    <div class="section">
        <h2>⚠️ Important Safety Information</h2>
        <div class="warning">
            <strong>WARNING:</strong> VeriWipe permanently destroys all data on selected storage devices. 
            This action is IRREVERSIBLE. Ensure you have proper authorization and have backed up any 
            important data before proceeding.
        </div>
    </div>
    
    <div class="section">
        <h2>🚀 Getting Started</h2>
        <ol>
            <li>Launch VeriWipe from the desktop icon</li>
            <li>Click "Detect Devices" to scan for storage devices</li>
            <li>Review detected devices carefully</li>
            <li>Select the device(s) you want to wipe</li>
            <li>Follow the confirmation prompts</li>
            <li>Wait for the operation to complete</li>
            <li>Review the generated certificate</li>
        </ol>
    </div>
    
    <div class="section">
        <h2>🤖 AI-Powered Features</h2>
        <div class="info">
            VeriWipe uses artificial intelligence to:
            <ul>
                <li>Automatically detect device types (HDD, SSD, NVMe, etc.)</li>
                <li>Select optimal wiping methods for each device</li>
                <li>Detect and resolve common errors</li>
                <li>Provide guidance throughout the process</li>
            </ul>
        </div>
    </div>
    
    <div class="section">
        <h2>📜 Certificates and Verification</h2>
        <p>After each successful wipe operation, VeriWipe generates:</p>
        <ul>
            <li><strong>PDF Certificate:</strong> Human-readable certificate with QR code</li>
            <li><strong>JSON Certificate:</strong> Machine-readable certificate for verification</li>
            <li><strong>Tamper-Proof Logs:</strong> Cryptographically secured operation logs</li>
        </ul>
        
        <div class="success">
            All certificates are digitally signed and can be verified independently.
        </div>
    </div>
    
    <div class="section">
        <h2>🔧 Supported Wipe Methods</h2>
        <table border="1" style="border-collapse: collapse; width: 100%;">
            <tr style="background: #f8f9fa;">
                <th style="padding: 10px;">Method</th>
                <th style="padding: 10px;">Device Type</th>
                <th style="padding: 10px;">NIST Classification</th>
                <th style="padding: 10px;">Description</th>
            </tr>
            <tr>
                <td style="padding: 10px;">ATA Secure Erase</td>
                <td style="padding: 10px;">HDD, SATA SSD</td>
                <td style="padding: 10px;">Purge</td>
                <td style="padding: 10px;">Hardware-level secure erase command</td>
            </tr>
            <tr>
                <td style="padding: 10px;">NVMe Secure Erase</td>
                <td style="padding: 10px;">NVMe SSD</td>
                <td style="padding: 10px;">Purge</td>
                <td style="padding: 10px;">NVMe format with secure erase</td>
            </tr>
            <tr>
                <td style="padding: 10px;">Crypto Erase</td>
                <td style="padding: 10px;">Encrypted devices</td>
                <td style="padding: 10px;">Purge</td>
                <td style="padding: 10px;">Destruction of encryption keys</td>
            </tr>
            <tr>
                <td style="padding: 10px;">Multi-pass Overwrite</td>
                <td style="padding: 10px;">Any</td>
                <td style="padding: 10px;">Purge</td>
                <td style="padding: 10px;">Multiple overwrites with patterns</td>
            </tr>
        </table>
    </div>
    
    <div class="section">
        <h2>🆘 Troubleshooting</h2>
        <h3>Device Not Detected</h3>
        <ul>
            <li>Ensure the device is properly connected</li>
            <li>Check USB connections and power</li>
            <li>Verify device is not mounted or in use</li>
        </ul>
        
        <h3>Permission Denied</h3>
        <ul>
            <li>VeriWipe requires administrator privileges</li>
            <li>Device may be mounted - check for auto-mount</li>
        </ul>
        
        <h3>Wipe Operation Failed</h3>
        <ul>
            <li>Check device health using SMART diagnostics</li>
            <li>Try alternative wipe method if available</li>
            <li>Consult the operation logs for details</li>
        </ul>
    </div>
    
    <div class="section">
        <h2>📞 Support</h2>
        <p>For technical support and additional resources:</p>
        <ul>
            <li>Project Repository: <code>https://github.com/veriwipe/veriwipe</code></li>
            <li>Documentation: <code>https://docs.veriwipe.org</code></li>
            <li>Certificate Verification: <code>https://verify.veriwipe.org</code></li>
        </ul>
    </div>
    
    <div class="section">
        <div style="text-align: center; color: #666; margin-top: 40px;">
            <p>VeriWipe v1.0.0 | Smart India Hackathon 2025 | Problem Statement ID: 25070</p>
            <p>Team: 4× Cybersecurity | 1× Blockchain | 1× Quantum</p>
        </div>
    </div>
</body>
</html>
EOF
    
    log "Documentation created"
}

setup_system_monitoring() {
    log "Setting up system monitoring..."
    
    # Create system monitor script
    cat > "$VERIWIPE_HOME/monitor.sh" << 'EOF'
#!/bin/bash
# VeriWipe System Monitor
# Monitors system resources during wipe operations

LOG_FILE="/var/log/veriwipe-monitor.log"

while true; do
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
    memory_usage=$(free | grep Mem | awk '{printf "%.1f", ($3/$2) * 100.0}')
    disk_io=$(iostat -d 1 1 | tail -n +4 | awk '{sum+=$4} END {print sum}')
    
    echo "[$timestamp] CPU: ${cpu_usage}% MEM: ${memory_usage}% DISK_IO: ${disk_io}" >> "$LOG_FILE"
    
    sleep 30
done
EOF
    
    chmod +x "$VERIWIPE_HOME/monitor.sh"
    
    log "System monitoring configured"
}

main() {
    log "Starting VeriWipe live environment setup..."
    
    setup_permissions
    setup_desktop_environment
    setup_boot_configuration
    setup_networking
    create_documentation
    setup_system_monitoring
    
    log "VeriWipe live environment setup completed successfully!"
}

# Run main function
main "$@"