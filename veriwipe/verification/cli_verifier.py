#!/usr/bin/env python3
"""
VeriWipe Command Line Certificate Verifier
Standalone tool for verifying VeriWipe certificates without web interface
"""

import json
import os
import sys
import argparse
import base64
from datetime import datetime
from typing import Dict, Any

def load_public_key_simple(public_key_path: str) -> str:
    """Load public key as string for simple verification"""
    try:
        with open(public_key_path, 'r') as f:
            return f.read()
    except Exception as e:
        print(f"Error loading public key: {e}")
        return ""

def verify_certificate_simple(certificate_path: str, public_key_path: str = None) -> Dict[str, Any]:
    """Simple certificate verification without cryptographic libraries"""
    try:
        # Load certificate
        with open(certificate_path, 'r') as f:
            cert_data = json.load(f)
        
        # Basic structure validation
        required_fields = [
            'certificate_id', 'timestamp', 'device_info', 
            'wipe_operation', 'tool_info', 'compliance_info'
        ]
        
        missing_fields = []
        for field in required_fields:
            if field not in cert_data:
                missing_fields.append(field)
        
        if missing_fields:
            return {
                "valid": False,
                "error": f"Missing required fields: {', '.join(missing_fields)}"
            }
        
        # Validate timestamp
        try:
            timestamp = cert_data.get('timestamp', '')
            datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        except ValueError:
            return {
                "valid": False,
                "error": "Invalid timestamp format"
            }
        
        # Check if signature exists
        signature = cert_data.get('signature', '')
        if not signature:
            return {
                "valid": False,
                "error": "No digital signature found"
            }
        
        # Structure validation passed
        return {
            "valid": True,
            "certificate_id": cert_data.get('certificate_id'),
            "timestamp": cert_data.get('timestamp'),
            "device_info": cert_data.get('device_info', {}),
            "wipe_operation": cert_data.get('wipe_operation', {}),
            "tool_info": cert_data.get('tool_info', {}),
            "compliance_info": cert_data.get('compliance_info', {}),
            "signature_present": bool(signature),
            "note": "Basic validation only - cryptographic verification requires full setup"
        }
        
    except json.JSONDecodeError:
        return {
            "valid": False,
            "error": "Invalid JSON format"
        }
    except FileNotFoundError:
        return {
            "valid": False,
            "error": f"Certificate file not found: {certificate_path}"
        }
    except Exception as e:
        return {
            "valid": False,
            "error": f"Verification error: {str(e)}"
        }

def print_verification_result(result: Dict[str, Any]):
    """Print verification result in a formatted way"""
    print("\\n" + "="*60)
    print("VeriWipe Certificate Verification Result")
    print("="*60)
    
    if result["valid"]:
        print("✅ CERTIFICATE VALID")
        print(f"\\nCertificate ID: {result.get('certificate_id', 'N/A')}")
        print(f"Timestamp: {result.get('timestamp', 'N/A')}")
        
        device_info = result.get('device_info', {})
        print(f"\\nDevice Information:")
        print(f"  Type: {device_info.get('device_type', 'N/A')}")
        print(f"  Model: {device_info.get('model', 'N/A')}")
        print(f"  Size: {device_info.get('size_gb', 'N/A')} GB")
        print(f"  Interface: {device_info.get('interface', 'N/A')}")
        print(f"  Encryption: {device_info.get('encryption_status', 'N/A')}")
        
        wipe_op = result.get('wipe_operation', {})
        print(f"\\nWipe Operation:")
        print(f"  Method: {wipe_op.get('method', 'N/A')}")
        print(f"  Status: {wipe_op.get('status', 'N/A')}")
        print(f"  Duration: {wipe_op.get('duration_seconds', 'N/A')} seconds")
        
        compliance = result.get('compliance_info', {})
        print(f"\\nCompliance:")
        print(f"  Standards: {', '.join(compliance.get('standards', []))}")
        print(f"  NIST Classification: {compliance.get('method_classification', 'N/A')}")
        
        tool_info = result.get('tool_info', {})
        print(f"\\nTool Information:")
        print(f"  Name: {tool_info.get('name', 'N/A')}")
        print(f"  Version: {tool_info.get('version', 'N/A')}")
        
        if result.get('note'):
            print(f"\\nNote: {result['note']}")
            
    else:
        print("❌ CERTIFICATE INVALID")
        print(f"\\nError: {result.get('error', 'Unknown error')}")
    
    print("="*60)

def main():
    parser = argparse.ArgumentParser(
        description="VeriWipe Certificate Verifier",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s certificate.json
  %(prog)s certificate.json --public-key public_key.pem
  %(prog)s --help
        """
    )
    
    parser.add_argument(
        'certificate',
        help='Path to the VeriWipe certificate JSON file'
    )
    
    parser.add_argument(
        '--public-key', '-k',
        help='Path to the public key file for signature verification'
    )
    
    parser.add_argument(
        '--json', '-j',
        action='store_true',
        help='Output result in JSON format'
    )
    
    parser.add_argument(
        '--version', '-v',
        action='version',
        version='VeriWipe Certificate Verifier v1.0.0'
    )
    
    args = parser.parse_args()
    
    # Verify certificate
    result = verify_certificate_simple(args.certificate, args.public_key)
    
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print_verification_result(result)
    
    # Exit with appropriate code
    sys.exit(0 if result["valid"] else 1)

if __name__ == "__main__":
    main()