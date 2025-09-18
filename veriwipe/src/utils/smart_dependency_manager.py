#!/usr/bin/env python3
"""
VeriWipe Smart Dependency Manager
Automatically detects, installs, and fixes dependencies with AI-powered diagnostics
"""

import os
import sys
import subprocess
import importlib
import logging
from pathlib import Path
from typing import List, Tuple, Dict, Optional

class SmartDependencyManager:
    """AI-powered dependency manager that automatically fixes missing packages"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.missing_system_packages = []
        self.missing_python_packages = []
        self.installation_log = []
        
    def check_all_dependencies(self) -> bool:
        """Comprehensive dependency check with auto-fix capability"""
        self.logger.info("🔍 Starting smart dependency analysis...")
        
        # Check system dependencies
        system_ok = self._check_system_dependencies()
        
        # Check Python dependencies  
        python_ok = self._check_python_dependencies()
        
        if system_ok and python_ok:
            self.logger.info("✅ All dependencies satisfied!")
            return True
        
        # Attempt auto-fix if running with proper privileges
        if os.geteuid() == 0:  # Running as root
            return self._auto_fix_dependencies()
        else:
            self._show_fix_instructions()
            return False
    
    def _check_system_dependencies(self) -> bool:
        """Check for required system packages"""
        self.logger.info("Checking system dependencies...")
        
        required_packages = {
            'python3': 'python3',
            'pip3': 'python3-pip',
            'PyQt5': 'python3-pyqt5',
            'libssl': 'libssl-dev',
            'libffi': 'libffi-dev',
            'hdparm': 'hdparm',
            'nvme-cli': 'nvme-cli',
            'smartctl': 'smartmontools'
        }
        
        missing = []
        for check_cmd, package_name in required_packages.items():
            if not self._check_system_package(check_cmd):
                missing.append(package_name)
        
        self.missing_system_packages = missing
        return len(missing) == 0
    
    def _check_python_dependencies(self) -> bool:
        """Check for required Python packages"""
        self.logger.info("Checking Python dependencies...")
        
        required_modules = [
            'PyQt5', 'cryptography', 'reportlab', 'qrcode', 
            'sklearn', 'numpy', 'scipy', 'psutil', 'flask'
        ]
        
        missing = []
        for module in required_modules:
            try:
                importlib.import_module(module.lower() if module == 'PyQt5' else module)
                self.logger.debug(f"✅ {module}: OK")
            except ImportError:
                missing.append(module)
                self.logger.debug(f"❌ {module}: Missing")
        
        self.missing_python_packages = missing
        return len(missing) == 0
    
    def _check_system_package(self, command: str) -> bool:
        """Check if a system command/package is available"""
        try:
            if command == 'PyQt5':
                # Special check for PyQt5 system package
                result = subprocess.run(['dpkg', '-l', 'python3-pyqt5'], 
                                      capture_output=True, text=True)
                return result.returncode == 0
            elif command in ['libssl', 'libffi']:
                # Check for development libraries
                lib_name = 'libssl-dev' if command == 'libssl' else 'libffi-dev'
                result = subprocess.run(['dpkg', '-l', lib_name], 
                                      capture_output=True, text=True)
                return result.returncode == 0
            else:
                # Check for executable commands
                result = subprocess.run(['which', command], 
                                      capture_output=True, text=True)
                return result.returncode == 0
        except Exception:
            return False
    
    def _auto_fix_dependencies(self) -> bool:
        """Automatically install missing dependencies"""
        self.logger.info("🤖 AI Auto-Fix: Installing missing dependencies...")
        
        success = True
        
        # Install system packages first
        if self.missing_system_packages:
            success &= self._install_system_packages()
        
        # Install Python packages
        if self.missing_python_packages:
            success &= self._install_python_packages()
        
        if success:
            self.logger.info("✅ Auto-fix completed successfully!")
            # Verify installation
            return self.check_all_dependencies()
        else:
            self.logger.error("❌ Auto-fix failed. Manual intervention required.")
            self._show_fix_instructions()
            return False
    
    def _install_system_packages(self) -> bool:
        """Install missing system packages"""
        self.logger.info(f"Installing system packages: {self.missing_system_packages}")
        
        try:
            # Update package list
            subprocess.run(['apt', 'update'], check=True, capture_output=True)
            
            # Install packages
            cmd = ['apt', 'install', '-y'] + self.missing_system_packages
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.installation_log.append("✅ System packages installed successfully")
                return True
            else:
                self.installation_log.append(f"❌ System package installation failed: {result.stderr}")
                return False
                
        except Exception as e:
            self.installation_log.append(f"❌ System package installation error: {e}")
            return False
    
    def _install_python_packages(self) -> bool:
        """Install missing Python packages"""
        self.logger.info(f"Installing Python packages: {self.missing_python_packages}")
        
        try:
            # Create requirements mapping
            package_mapping = {
                'PyQt5': 'PyQt5>=5.15.4',
                'cryptography': 'cryptography>=3.4.8',
                'reportlab': 'reportlab>=3.6.0',
                'qrcode': 'qrcode[pil]>=7.3.1',
                'sklearn': 'scikit-learn>=1.0.0',
                'numpy': 'numpy>=1.21.0',
                'scipy': 'scipy>=1.7.0',
                'psutil': 'psutil>=5.8.0',
                'flask': 'flask>=2.0.0'
            }
            
            packages_to_install = [
                package_mapping.get(pkg, pkg) 
                for pkg in self.missing_python_packages
            ]
            
            # Install packages
            cmd = [sys.executable, '-m', 'pip', 'install', '--upgrade'] + packages_to_install
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.installation_log.append("✅ Python packages installed successfully")
                return True
            else:
                self.installation_log.append(f"❌ Python package installation failed: {result.stderr}")
                return False
                
        except Exception as e:
            self.installation_log.append(f"❌ Python package installation error: {e}")
            return False
    
    def _show_fix_instructions(self):
        """Show user-friendly fix instructions"""
        print("\n🔧 VeriWipe Dependency Fix Required")
        print("=" * 50)
        
        if self.missing_system_packages:
            print("\n📦 Missing System Packages:")
            for pkg in self.missing_system_packages:
                print(f"  • {pkg}")
            print("\n🔨 Fix Command:")
            print(f"sudo apt update && sudo apt install -y {' '.join(self.missing_system_packages)}")
        
        if self.missing_python_packages:
            print("\n🐍 Missing Python Packages:")
            for pkg in self.missing_python_packages:
                print(f"  • {pkg}")
            print("\n🔨 Fix Command:")
            print(f"pip install {' '.join(self.missing_python_packages)}")
        
        print("\n🚀 Quick Fix (Run as root):")
        print("sudo python3 veriwipe.py --auto-fix")
        
        print("\n💡 Or use the automated setup script:")
        print("./setup_ubuntu.sh")
        print("\n" + "=" * 50)
    
    def create_portable_installer(self) -> str:
        """Create a portable installer script"""
        installer_script = f"""#!/bin/bash
# VeriWipe Portable Auto-Installer
# Generated automatically by Smart Dependency Manager

set -e

echo "🚀 VeriWipe Auto-Installer"
echo "========================="

# Check for root privileges
if [[ $EUID -ne 0 ]]; then
   echo "❌ This installer requires root privileges"
   echo "Please run: sudo $0"
   exit 1
fi

echo "📦 Installing system dependencies..."
apt update
apt install -y {' '.join(self.missing_system_packages)}

echo "🐍 Installing Python dependencies..."
pip3 install {' '.join(self.missing_python_packages)}

echo "✅ Installation complete!"
echo "🚀 You can now run: python3 veriwipe.py"
"""
        
        installer_path = Path("veriwipe_auto_installer.sh")
        installer_path.write_text(installer_script)
        installer_path.chmod(0o755)
        
        return str(installer_path)

def smart_dependency_check() -> bool:
    """Main entry point for smart dependency checking"""
    manager = SmartDependencyManager()
    return manager.check_all_dependencies()

if __name__ == "__main__":
    # Standalone dependency checker
    logging.basicConfig(level=logging.INFO)
    
    manager = SmartDependencyManager()
    
    if "--auto-fix" in sys.argv:
        if os.geteuid() != 0:
            print("❌ Auto-fix requires root privileges. Run with sudo.")
            sys.exit(1)
        success = manager.check_all_dependencies()
        sys.exit(0 if success else 1)
    
    elif "--create-installer" in sys.argv:
        manager._check_system_dependencies()
        manager._check_python_dependencies()
        installer_path = manager.create_portable_installer()
        print(f"✅ Portable installer created: {installer_path}")
        print(f"Run: sudo ./{installer_path}")
    
    else:
        success = manager.check_all_dependencies()
        if not success:
            print("\n💡 Quick fixes available:")
            print("  • sudo python3 smart_dependency_manager.py --auto-fix")
            print("  • python3 smart_dependency_manager.py --create-installer")
        sys.exit(0 if success else 1)