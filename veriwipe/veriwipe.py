#!/usr/bin/env python3
"""
VeriWipe Main Entry Point
Launches the VeriWipe application with proper error handling and logging
"""

import sys
import os
import logging
import argparse
from pathlib import Path

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def setup_logging(log_level: str = "INFO"):
    """Set up logging configuration"""
    log_dir = Path("/var/log/veriwipe")
    log_dir.mkdir(exist_ok=True, parents=True)
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / "veriwipe.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )

def check_dependencies():
    """Check if all required dependencies are available"""
    missing_deps = []
    
    try:
        import PyQt5
    except ImportError:
        missing_deps.append("PyQt5")
    
    try:
        import cryptography
    except ImportError:
        missing_deps.append("cryptography")
    
    try:
        import reportlab
    except ImportError:
        missing_deps.append("reportlab")
    
    try:
        import qrcode
    except ImportError:
        missing_deps.append("qrcode")
    
    if missing_deps:
        print(f"Error: Missing dependencies: {', '.join(missing_deps)}")
        print("Please install with: pip install -r requirements.txt")
        return False
    
    return True

def check_permissions():
    """Check if running with appropriate permissions"""
    if os.geteuid() != 0:
        print("Warning: VeriWipe should be run as root for full functionality")
        print("Some disk operations may fail without root privileges")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            return False
    return True

def launch_gui():
    """Launch the GUI application"""
    try:
        from gui.main_window import main as gui_main
        gui_main()
    except Exception as e:
        logging.error(f"Failed to launch GUI: {e}")
        print(f"Error launching GUI: {e}")
        return 1
    return 0

def launch_cli():
    """Launch CLI mode (for testing and automation)"""
    try:
        from ai_engine.ai_wipe_engine import AIWipeEngine
        from wipe_core.wipe_engine import WipeCore
        
        print("VeriWipe CLI Mode")
        print("================")
        
        ai_engine = AIWipeEngine()
        wipe_core = WipeCore(ai_engine)
        
        print("Detecting devices...")
        devices = ai_engine.detect_devices()
        
        if not devices:
            print("No devices detected.")
            return 1
        
        print(f"Found {len(devices)} device(s):")
        for i, device in enumerate(devices):
            print(f"{i+1}. {device.device_path} - {device.model} ({device.size_gb:.2f} GB)")
            method = ai_engine.select_optimal_wipe_method(device)
            print(f"   Recommended method: {method.value}")
        
        return 0
        
    except Exception as e:
        logging.error(f"CLI mode failed: {e}")
        print(f"Error in CLI mode: {e}")
        return 1

def show_system_info():
    """Show system information relevant to VeriWipe"""
    import platform
    import subprocess
    
    print("VeriWipe System Information")
    print("==========================")
    print(f"OS: {platform.system()} {platform.release()}")
    print(f"Architecture: {platform.machine()}")
    print(f"Python: {platform.python_version()}")
    print(f"User: {os.getenv('USER', 'unknown')} (UID: {os.getuid()})")
    
    # Check available disk tools
    tools = ['hdparm', 'nvme', 'cryptsetup', 'smartctl', 'blkdiscard']
    print("\\nAvailable disk tools:")
    for tool in tools:
        try:
            result = subprocess.run(['which', tool], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"  ✅ {tool}: {result.stdout.strip()}")
            else:
                print(f"  ❌ {tool}: Not found")
        except Exception:
            print(f"  ❌ {tool}: Error checking")
    
    # Check disk devices
    print("\\nBlock devices:")
    try:
        result = subprocess.run(['lsblk', '-d', '-o', 'NAME,TYPE,SIZE,MODEL'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(result.stdout)
    except Exception as e:
        print(f"Error listing devices: {e}")

def main():
    parser = argparse.ArgumentParser(
        description="VeriWipe - AI-Powered Secure Data Wiping",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Launch GUI (default)
  %(prog)s --cli              # CLI mode for testing
  %(prog)s --info             # Show system information
  %(prog)s --verify cert.json # Verify a certificate
        """
    )
    
    parser.add_argument(
        '--cli', '-c',
        action='store_true',
        help='Run in CLI mode (no GUI)'
    )
    
    parser.add_argument(
        '--info', '-i',
        action='store_true',
        help='Show system information and exit'
    )
    
    parser.add_argument(
        '--verify', '-v',
        metavar='CERTIFICATE',
        help='Verify a certificate file and exit'
    )
    
    parser.add_argument(
        '--log-level', '-l',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Set logging level (default: INFO)'
    )
    
    parser.add_argument(
        '--no-gui-check',
        action='store_true',
        help='Skip GUI dependency check (for CLI mode)'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='VeriWipe v1.0.0 - Smart India Hackathon 2025'
    )
    
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    logger.info("VeriWipe starting...")
    
    # Handle special modes first
    if args.info:
        show_system_info()
        return 0
    
    if args.verify:
        from verification.cli_verifier import verify_certificate_simple, print_verification_result
        result = verify_certificate_simple(args.verify)
        print_verification_result(result)
        return 0 if result["valid"] else 1
    
    # Check dependencies (skip GUI check for CLI mode)
    if not args.cli and not args.no_gui_check:
        if not check_dependencies():
            return 1
    
    # Check permissions
    if not check_permissions():
        return 1
    
    # Launch appropriate mode
    if args.cli:
        return launch_cli()
    else:
        return launch_gui()

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\\nOperation cancelled by user")
        sys.exit(130)
    except Exception as e:
        logging.error(f"Unexpected error: {e}", exc_info=True)
        print(f"Unexpected error: {e}")
        sys.exit(1)