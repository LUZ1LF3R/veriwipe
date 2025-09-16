#!/usr/bin/env python3
"""
VeriWipe Certificate Engine - Tamper-Proof Certificate Generation
"""

import json
import hashlib
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import os
import base64
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import load_pem_private_key, load_pem_public_key
from cryptography.exceptions import InvalidSignature
import qrcode
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import io

from wipe_core.wipe_engine import WipeOperation, WipeStatus

@dataclass
class LogEntry:
    timestamp: float
    entry_id: str
    message: str
    level: str
    previous_hash: str
    entry_hash: str = ""
    
    def __post_init__(self):
        if not self.entry_hash:
            self.entry_hash = self.calculate_hash()
    
    def calculate_hash(self) -> str:
        """Calculate hash of this log entry"""
        data = f"{self.timestamp}{self.entry_id}{self.message}{self.level}{self.previous_hash}"
        return hashlib.sha256(data.encode()).hexdigest()

@dataclass
class CertificateData:
    certificate_id: str
    timestamp: str
    device_info: Dict[str, Any]
    wipe_operation: Dict[str, Any]
    verification_hashes: Dict[str, str]
    operation_log: List[Dict[str, Any]]
    tool_info: Dict[str, str]
    compliance_info: Dict[str, str]
    signature: str = ""
    blockchain_anchor: Optional[str] = None

class TamperProofLogger:
    def __init__(self, log_file_path: str = None):
        self.log_file_path = log_file_path or "/tmp/veriwipe_operation.log"
        self.log_chain: List[LogEntry] = []
        self.genesis_hash = "0000000000000000000000000000000000000000000000000000000000000000"
        self._load_existing_log()
    
    def _load_existing_log(self):
        """Load existing log file if it exists"""
        if os.path.exists(self.log_file_path):
            try:
                with open(self.log_file_path, 'r') as f:
                    log_data = json.load(f)
                    for entry_data in log_data:
                        entry = LogEntry(**entry_data)
                        self.log_chain.append(entry)
            except Exception as e:
                print(f"Warning: Could not load existing log: {e}")
    
    def add_entry(self, message: str, level: str = "INFO") -> str:
        """Add a new entry to the tamper-proof log chain"""
        timestamp = time.time()
        entry_id = str(uuid.uuid4())
        previous_hash = self.log_chain[-1].entry_hash if self.log_chain else self.genesis_hash
        
        entry = LogEntry(
            timestamp=timestamp,
            entry_id=entry_id,
            message=message,
            level=level,
            previous_hash=previous_hash
        )
        
        self.log_chain.append(entry)
        self._save_log()
        return entry_id
    
    def verify_chain_integrity(self) -> bool:
        """Verify the integrity of the entire log chain"""
        if not self.log_chain:
            return True
        
        expected_previous = self.genesis_hash
        for entry in self.log_chain:
            # Check if previous hash matches
            if entry.previous_hash != expected_previous:
                return False
            
            # Verify entry hash
            if entry.entry_hash != entry.calculate_hash():
                return False
            
            expected_previous = entry.entry_hash
        
        return True
    
    def get_log_summary(self) -> Dict[str, Any]:
        """Get a summary of the log for certificate inclusion"""
        return {
            "total_entries": len(self.log_chain),
            "first_entry_timestamp": self.log_chain[0].timestamp if self.log_chain else None,
            "last_entry_timestamp": self.log_chain[-1].timestamp if self.log_chain else None,
            "chain_hash": self.log_chain[-1].entry_hash if self.log_chain else self.genesis_hash,
            "integrity_verified": self.verify_chain_integrity()
        }
    
    def _save_log(self):
        """Save the log chain to file"""
        try:
            with open(self.log_file_path, 'w') as f:
                json.dump([asdict(entry) for entry in self.log_chain], f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save log: {e}")

class CryptographicSigner:
    def __init__(self, private_key_path: str = None, public_key_path: str = None):
        self.private_key_path = private_key_path or "/opt/veriwipe/keys/private_key.pem"
        self.public_key_path = public_key_path or "/opt/veriwipe/keys/public_key.pem"
        self.private_key = None
        self.public_key = None
        self._load_or_generate_keys()
    
    def _load_or_generate_keys(self):
        """Load existing keys or generate new ones"""
        try:
            if os.path.exists(self.private_key_path) and os.path.exists(self.public_key_path):
                self._load_keys()
            else:
                self._generate_keys()
        except Exception as e:
            print(f"Error with cryptographic keys: {e}")
            self._generate_keys()
    
    def _load_keys(self):
        """Load existing cryptographic keys"""
        with open(self.private_key_path, 'rb') as f:
            self.private_key = load_pem_private_key(f.read(), password=None)
        
        with open(self.public_key_path, 'rb') as f:
            self.public_key = load_pem_public_key(f.read())
    
    def _generate_keys(self):
        """Generate new ECDSA key pair"""
        # Generate private key
        self.private_key = ec.generate_private_key(ec.SECP256R1())
        self.public_key = self.private_key.public_key()
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.private_key_path), exist_ok=True)
        
        # Save private key
        with open(self.private_key_path, 'wb') as f:
            f.write(self.private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
        
        # Save public key
        with open(self.public_key_path, 'wb') as f:
            f.write(self.public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ))
        
        # Set restrictive permissions
        os.chmod(self.private_key_path, 0o600)
        os.chmod(self.public_key_path, 0o644)
    
    def sign_data(self, data: str) -> str:
        """Sign data and return base64-encoded signature"""
        if not self.private_key:
            raise Exception("No private key available for signing")
        
        signature = self.private_key.sign(
            data.encode(),
            ec.ECDSA(hashes.SHA256())
        )
        
        return base64.b64encode(signature).decode()
    
    def verify_signature(self, data: str, signature: str) -> bool:
        """Verify a signature"""
        if not self.public_key:
            return False
        
        try:
            signature_bytes = base64.b64decode(signature)
            self.public_key.verify(
                signature_bytes,
                data.encode(),
                ec.ECDSA(hashes.SHA256())
            )
            return True
        except InvalidSignature:
            return False
        except Exception:
            return False
    
    def get_public_key_fingerprint(self) -> str:
        """Get fingerprint of public key for identification"""
        if not self.public_key:
            return ""
        
        public_key_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        return hashlib.sha256(public_key_bytes).hexdigest()[:16]

class CertificateGenerator:
    def __init__(self, logger: TamperProofLogger = None, signer: CryptographicSigner = None):
        self.logger = logger or TamperProofLogger()
        self.signer = signer or CryptographicSigner()
        self.logger.add_entry("Certificate generator initialized")
    
    def generate_certificate(self, wipe_operation: WipeOperation, output_dir: str = "/tmp") -> Dict[str, str]:
        """Generate complete certificate package (JSON + PDF)"""
        self.logger.add_entry(f"Starting certificate generation for {wipe_operation.device_info.device_path}")
        
        # Generate certificate data
        certificate_data = self._prepare_certificate_data(wipe_operation)
        
        # Sign the certificate
        certificate_data.signature = self._sign_certificate(certificate_data)
        
        # Generate files
        json_path = self._generate_json_certificate(certificate_data, output_dir)
        pdf_path = self._generate_pdf_certificate(certificate_data, output_dir)
        
        self.logger.add_entry(f"Certificate generation completed: {json_path}, {pdf_path}")
        
        return {
            "json_certificate": json_path,
            "pdf_certificate": pdf_path,
            "certificate_id": certificate_data.certificate_id
        }
    
    def _prepare_certificate_data(self, wipe_operation: WipeOperation) -> CertificateData:
        """Prepare certificate data structure"""
        certificate_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Sanitize device info (remove sensitive data, keep hashes)
        device_info = {
            "device_path_hash": hashlib.sha256(wipe_operation.device_info.device_path.encode()).hexdigest()[:16],
            "device_type": wipe_operation.device_info.device_type.value,
            "model": wipe_operation.device_info.model,
            "serial_hash": hashlib.sha256(wipe_operation.device_info.serial.encode()).hexdigest()[:16],
            "size_gb": wipe_operation.device_info.size_gb,
            "interface": wipe_operation.device_info.interface,
            "encryption_status": wipe_operation.device_info.encryption_status,
            "hpa_dco_present": wipe_operation.device_info.hpa_dco_present,
            "secure_erase_supported": wipe_operation.device_info.secure_erase_supported
        }
        
        # Wipe operation details
        wipe_op_data = {
            "method": wipe_operation.method.value,
            "status": wipe_operation.status.value,
            "start_time": wipe_operation.start_time,
            "end_time": wipe_operation.end_time,
            "duration_seconds": (wipe_operation.end_time - wipe_operation.start_time) if wipe_operation.end_time and wipe_operation.start_time else None,
            "progress": wipe_operation.progress,
            "error_message": wipe_operation.error_message
        }
        
        # Convert operation log to serializable format
        operation_log = []
        for entry in self.logger.log_chain:
            operation_log.append({
                "timestamp": entry.timestamp,
                "entry_id": entry.entry_id,
                "message": entry.message,
                "level": entry.level,
                "entry_hash": entry.entry_hash
            })
        
        # Tool information
        tool_info = {
            "name": "VeriWipe",
            "version": "1.0.0",
            "build_hash": "development",
            "signer_fingerprint": self.signer.get_public_key_fingerprint()
        }
        
        # Compliance information
        compliance_info = {
            "standards": ["NIST SP 800-88"],
            "method_classification": self._get_nist_classification(wipe_operation.method),
            "verification_level": "Basic" if wipe_operation.verification_hashes else "None"
        }
        
        return CertificateData(
            certificate_id=certificate_id,
            timestamp=timestamp,
            device_info=device_info,
            wipe_operation=wipe_op_data,
            verification_hashes=wipe_operation.verification_hashes or {},
            operation_log=operation_log,
            tool_info=tool_info,
            compliance_info=compliance_info
        )
    
    def _sign_certificate(self, certificate_data: CertificateData) -> str:
        """Sign the certificate data"""
        # Create canonical JSON representation for signing
        cert_dict = asdict(certificate_data)
        cert_dict.pop('signature', None)  # Remove signature field if present
        cert_dict.pop('blockchain_anchor', None)  # Remove blockchain field if present
        
        canonical_json = json.dumps(cert_dict, sort_keys=True, separators=(',', ':'))
        return self.signer.sign_data(canonical_json)
    
    def _generate_json_certificate(self, certificate_data: CertificateData, output_dir: str) -> str:
        """Generate JSON certificate file"""
        filename = f"veriwipe_certificate_{certificate_data.certificate_id}.json"
        file_path = os.path.join(output_dir, filename)
        
        with open(file_path, 'w') as f:
            json.dump(asdict(certificate_data), f, indent=2)
        
        return file_path
    
    def _generate_pdf_certificate(self, certificate_data: CertificateData, output_dir: str) -> str:
        """Generate PDF certificate with QR code"""
        filename = f"veriwipe_certificate_{certificate_data.certificate_id}.pdf"
        file_path = os.path.join(output_dir, filename)
        
        # Create PDF document
        doc = SimpleDocTemplate(file_path, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.darkblue
        )
        story.append(Paragraph("VeriWipe Secure Data Wiping Certificate", title_style))
        story.append(Spacer(1, 20))
        
        # Certificate ID and timestamp
        story.append(Paragraph(f"<b>Certificate ID:</b> {certificate_data.certificate_id}", styles['Normal']))
        story.append(Paragraph(f"<b>Generated:</b> {certificate_data.timestamp}", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Device Information
        story.append(Paragraph("Device Information", styles['Heading2']))
        device_data = [
            ['Property', 'Value'],
            ['Device Type', certificate_data.device_info['device_type']],
            ['Model', certificate_data.device_info['model']],
            ['Size', f"{certificate_data.device_info['size_gb']:.2f} GB"],
            ['Interface', certificate_data.device_info['interface']],
            ['Encryption Status', certificate_data.device_info['encryption_status']],
            ['Secure Erase Supported', 'Yes' if certificate_data.device_info['secure_erase_supported'] else 'No']
        ]
        
        device_table = Table(device_data)
        device_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(device_table)
        story.append(Spacer(1, 20))
        
        # Wipe Operation Details
        story.append(Paragraph("Wipe Operation Details", styles['Heading2']))
        wipe_data = [
            ['Property', 'Value'],
            ['Method Used', certificate_data.wipe_operation['method']],
            ['Status', certificate_data.wipe_operation['status']],
            ['Duration', f"{certificate_data.wipe_operation.get('duration_seconds', 0):.1f} seconds" if certificate_data.wipe_operation.get('duration_seconds') else 'N/A'],
            ['NIST Classification', certificate_data.compliance_info['method_classification']],
            ['Verification Level', certificate_data.compliance_info['verification_level']]
        ]
        
        wipe_table = Table(wipe_data)
        wipe_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(wipe_table)
        story.append(Spacer(1, 20))
        
        # QR Code for verification
        qr_data = {
            "certificate_id": certificate_data.certificate_id,
            "verification_url": f"https://verify.veriwipe.org/{certificate_data.certificate_id}",
            "signature": certificate_data.signature[:32] + "..."  # Truncated for QR
        }
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(json.dumps(qr_data))
        qr.make(fit=True)
        
        qr_img = qr.make_image(fill_color="black", back_color="white")
        qr_buffer = io.BytesIO()
        qr_img.save(qr_buffer, format='PNG')
        qr_buffer.seek(0)
        
        # Add QR code to PDF
        story.append(Paragraph("Verification QR Code", styles['Heading2']))
        story.append(Paragraph("Scan this QR code to verify the certificate online:", styles['Normal']))
        story.append(Spacer(1, 10))
        
        # Create temporary file for QR code
        qr_temp_path = os.path.join(output_dir, f"qr_{certificate_data.certificate_id}.png")
        with open(qr_temp_path, 'wb') as f:
            f.write(qr_buffer.getvalue())
        
        qr_image = Image(qr_temp_path, width=2*inch, height=2*inch)
        story.append(qr_image)
        story.append(Spacer(1, 20))
        
        # Digital Signature
        story.append(Paragraph("Digital Signature", styles['Heading2']))
        story.append(Paragraph(f"<b>Signature:</b> {certificate_data.signature[:64]}...", styles['Normal']))
        story.append(Paragraph(f"<b>Signer Fingerprint:</b> {certificate_data.tool_info['signer_fingerprint']}", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Footer
        footer_text = """
        This certificate was generated by VeriWipe, an AI-powered secure data wiping solution.
        The digital signature ensures the authenticity and integrity of this certificate.
        For verification, visit https://verify.veriwipe.org or scan the QR code above.
        """
        story.append(Paragraph(footer_text, styles['Normal']))
        
        # Build PDF
        doc.build(story)
        
        # Clean up temporary QR code file
        try:
            os.remove(qr_temp_path)
        except:
            pass
        
        return file_path
    
    def _get_nist_classification(self, wipe_method) -> str:
        """Get NIST SP 800-88 classification for wipe method"""
        classifications = {
            "ata_secure_erase": "Purge",
            "nvme_secure_erase": "Purge", 
            "nvme_crypto_erase": "Purge",
            "crypto_erase": "Purge",
            "multipass_overwrite": "Purge",
            "single_pass_random": "Clear",
            "factory_reset": "Clear"
        }
        return classifications.get(wipe_method.value, "Unknown")
    
    def verify_certificate(self, certificate_path: str) -> Dict[str, Any]:
        """Verify a certificate's authenticity and integrity"""
        try:
            with open(certificate_path, 'r') as f:
                cert_data = json.load(f)
            
            # Extract signature
            signature = cert_data.pop('signature', '')
            blockchain_anchor = cert_data.pop('blockchain_anchor', None)
            
            # Recreate canonical JSON
            canonical_json = json.dumps(cert_data, sort_keys=True, separators=(',', ':'))
            
            # Verify signature
            signature_valid = self.signer.verify_signature(canonical_json, signature)
            
            return {
                "valid": signature_valid,
                "certificate_id": cert_data.get('certificate_id'),
                "timestamp": cert_data.get('timestamp'),
                "signer_fingerprint": cert_data.get('tool_info', {}).get('signer_fingerprint'),
                "blockchain_anchor": blockchain_anchor
            }
            
        except Exception as e:
            return {
                "valid": False,
                "error": str(e)
            }

if __name__ == "__main__":
    # Test certificate generation
    from wipe_core.wipe_engine import DeviceInfo, DeviceType, WipeMethod, WipeOperation, WipeStatus
    
    # Create test data
    device_info = DeviceInfo(
        device_path="/dev/sdb",
        device_type=DeviceType.SSD_SATA,
        model="Samsung SSD 850",
        serial="TEST123456",
        size_gb=256.0,
        interface="SATA",
        encryption_status="None",
        hpa_dco_present=False,
        secure_erase_supported=True,
        features={}
    )
    
    wipe_op = WipeOperation(
        device_info=device_info,
        method=WipeMethod.ATA_SECURE_ERASE,
        start_time=time.time() - 300,
        end_time=time.time(),
        status=WipeStatus.COMPLETED,
        progress=100.0,
        verification_hashes={"pre_wipe_sample": "abc123", "post_wipe_sample": "def456"}
    )
    
    # Generate certificate
    logger = TamperProofLogger()
    logger.add_entry("Test wipe operation started")
    logger.add_entry("Device detected and analyzed")
    logger.add_entry("Wipe operation completed successfully")
    
    cert_gen = CertificateGenerator(logger)
    results = cert_gen.generate_certificate(wipe_op)
    
    print("Generated certificates:")
    for key, path in results.items():
        print(f"{key}: {path}")
    
    # Test verification
    verification = cert_gen.verify_certificate(results["json_certificate"])
    print(f"\\nCertificate verification: {verification}")