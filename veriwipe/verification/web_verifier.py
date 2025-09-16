#!/usr/bin/env python3
"""
VeriWipe Certificate Verification Server
Web interface for third-party validation of wipe certificates
"""

from flask import Flask, render_template, request, jsonify, send_file
import json
import os
import hashlib
from datetime import datetime
import qrcode
import io
import base64
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.exceptions import InvalidSignature

app = Flask(__name__)

class CertificateVerifier:
    def __init__(self, public_key_path: str = None):
        self.public_key_path = public_key_path or "/opt/veriwipe/keys/public_key.pem"
        self.public_key = None
        self.load_public_key()
    
    def load_public_key(self):
        """Load the public key for verification"""
        try:
            if os.path.exists(self.public_key_path):
                with open(self.public_key_path, 'rb') as f:
                    self.public_key = load_pem_public_key(f.read())
            else:
                print(f"Warning: Public key not found at {self.public_key_path}")
        except Exception as e:
            print(f"Error loading public key: {e}")
    
    def verify_certificate(self, certificate_data: dict) -> dict:
        """Verify a certificate's authenticity"""
        try:
            # Extract signature
            signature = certificate_data.get('signature', '')
            if not signature:
                return {"valid": False, "error": "No signature found"}
            
            # Create a copy without signature for verification
            cert_copy = certificate_data.copy()
            cert_copy.pop('signature', None)
            cert_copy.pop('blockchain_anchor', None)
            
            # Create canonical JSON
            canonical_json = json.dumps(cert_copy, sort_keys=True, separators=(',', ':'))
            
            # Verify signature
            if not self.public_key:
                return {"valid": False, "error": "Public key not available"}
            
            try:
                signature_bytes = base64.b64decode(signature)
                self.public_key.verify(
                    signature_bytes,
                    canonical_json.encode(),
                    ec.ECDSA(hashes.SHA256())
                )
                signature_valid = True
            except InvalidSignature:
                signature_valid = False
            except Exception as e:
                return {"valid": False, "error": f"Signature verification error: {str(e)}"}
            
            # Additional validation
            validation_result = self._validate_certificate_structure(certificate_data)
            
            return {
                "valid": signature_valid and validation_result["valid"],
                "signature_valid": signature_valid,
                "structure_valid": validation_result["valid"],
                "certificate_id": certificate_data.get('certificate_id'),
                "timestamp": certificate_data.get('timestamp'),
                "device_info": certificate_data.get('device_info', {}),
                "wipe_operation": certificate_data.get('wipe_operation', {}),
                "tool_info": certificate_data.get('tool_info', {}),
                "compliance_info": certificate_data.get('compliance_info', {}),
                "errors": validation_result.get("errors", [])
            }
            
        except Exception as e:
            return {"valid": False, "error": f"Verification error: {str(e)}"}
    
    def _validate_certificate_structure(self, cert_data: dict) -> dict:
        """Validate the structure and content of the certificate"""
        errors = []
        
        # Required fields
        required_fields = [
            'certificate_id', 'timestamp', 'device_info', 
            'wipe_operation', 'tool_info', 'compliance_info'
        ]
        
        for field in required_fields:
            if field not in cert_data:
                errors.append(f"Missing required field: {field}")
        
        # Validate timestamp
        try:
            datetime.fromisoformat(cert_data.get('timestamp', '').replace('Z', '+00:00'))
        except ValueError:
            errors.append("Invalid timestamp format")
        
        # Validate wipe operation status
        wipe_op = cert_data.get('wipe_operation', {})
        if wipe_op.get('status') not in ['completed', 'failed']:
            errors.append("Invalid wipe operation status")
        
        # Validate device info
        device_info = cert_data.get('device_info', {})
        if not device_info.get('device_type'):
            errors.append("Missing device type information")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }

# Initialize verifier
verifier = CertificateVerifier()

@app.route('/')
def index():
    """Main verification page"""
    return render_template('index.html')

@app.route('/verify', methods=['POST'])
def verify():
    """Verify a certificate"""
    try:
        if 'certificate_file' in request.files:
            # File upload
            file = request.files['certificate_file']
            if file.filename == '':
                return jsonify({"error": "No file selected"})
            
            try:
                certificate_data = json.load(file)
            except json.JSONDecodeError:
                return jsonify({"error": "Invalid JSON file"})
                
        elif request.is_json:
            # JSON data
            certificate_data = request.get_json()
            
        else:
            # Form data with JSON text
            cert_text = request.form.get('certificate_json', '')
            if not cert_text:
                return jsonify({"error": "No certificate data provided"})
            
            try:
                certificate_data = json.loads(cert_text)
            except json.JSONDecodeError:
                return jsonify({"error": "Invalid JSON format"})
        
        # Verify the certificate
        result = verifier.verify_certificate(certificate_data)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": f"Verification failed: {str(e)}"})

@app.route('/verify/<certificate_id>')
def verify_by_id(certificate_id):
    """Verify a certificate by ID (for QR code scanning)"""
    # In a real implementation, this would look up the certificate
    # in a database or blockchain. For now, return a placeholder.
    return render_template('verify_result.html', 
                         certificate_id=certificate_id,
                         verification_result={
                             "valid": False,
                             "error": "Certificate lookup not implemented"
                         })

@app.route('/api/verify', methods=['POST'])
def api_verify():
    """API endpoint for certificate verification"""
    return verify()

@app.route('/qr/<certificate_id>')
def generate_qr(certificate_id):
    """Generate QR code for certificate verification"""
    verification_url = f"{request.url_root}verify/{certificate_id}"
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(verification_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    
    return send_file(img_buffer, mimetype='image/png')

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "VeriWipe Certificate Verifier",
        "version": "1.0.0",
        "public_key_loaded": verifier.public_key is not None
    })

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', 
                         error_code=404,
                         error_message="Page not found"), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('error.html',
                         error_code=500, 
                         error_message="Internal server error"), 500

if __name__ == '__main__':
    # Create templates directory and basic templates
    os.makedirs('templates', exist_ok=True)
    
    # Create basic HTML templates
    create_templates()
    
    # Run the application
    app.run(host='0.0.0.0', port=5000, debug=True)

def create_templates():
    """Create basic HTML templates"""
    
    # Main index template
    index_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VeriWipe Certificate Verifier</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }
        .header {
            text-align: center;
            color: white;
            margin-bottom: 40px;
        }
        .header h1 {
            font-size: 3em;
            margin: 0;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        .header p {
            font-size: 1.2em;
            margin: 10px 0;
        }
        .card {
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            margin-bottom: 20px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            font-weight: bold;
            color: #333;
        }
        input[type="file"], textarea {
            width: 100%;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-size: 16px;
            box-sizing: border-box;
        }
        textarea {
            height: 200px;
            resize: vertical;
            font-family: 'Courier New', monospace;
        }
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 30px;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: transform 0.2s;
            width: 100%;
        }
        .btn:hover {
            transform: translateY(-2px);
        }
        .result {
            margin-top: 20px;
            padding: 20px;
            border-radius: 8px;
            display: none;
        }
        .result.success {
            background: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
        }
        .result.error {
            background: #f8d7da;
            border: 1px solid #f5c6cb;
            color: #721c24;
        }
        .loading {
            text-align: center;
            padding: 20px;
            display: none;
        }
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .feature-list {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }
        .feature {
            text-align: center;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
        }
        .feature-icon {
            font-size: 2em;
            margin-bottom: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🛡️ VeriWipe</h1>
            <p>Certificate Verification System</p>
            <p>Verify the authenticity of secure data wiping certificates</p>
        </div>
        
        <div class="card">
            <h2>Upload Certificate for Verification</h2>
            <form id="verifyForm" enctype="multipart/form-data">
                <div class="form-group">
                    <label for="certificate_file">Upload JSON Certificate File:</label>
                    <input type="file" id="certificate_file" name="certificate_file" accept=".json" />
                </div>
                
                <div style="text-align: center; margin: 20px 0; color: #666;">
                    OR
                </div>
                
                <div class="form-group">
                    <label for="certificate_json">Paste Certificate JSON:</label>
                    <textarea id="certificate_json" name="certificate_json" placeholder="Paste your VeriWipe certificate JSON here..."></textarea>
                </div>
                
                <button type="submit" class="btn">🔍 Verify Certificate</button>
            </form>
            
            <div class="loading" id="loading">
                <div class="spinner"></div>
                <p>Verifying certificate...</p>
            </div>
            
            <div class="result" id="result">
                <!-- Verification result will be displayed here -->
            </div>
        </div>
        
        <div class="card">
            <h2>Why Verify Certificates?</h2>
            <div class="feature-list">
                <div class="feature">
                    <div class="feature-icon">🔐</div>
                    <h3>Authenticity</h3>
                    <p>Confirm the certificate was generated by genuine VeriWipe software</p>
                </div>
                <div class="feature">
                    <div class="feature-icon">🛡️</div>
                    <h3>Integrity</h3>
                    <p>Ensure the certificate hasn't been tampered with or modified</p>
                </div>
                <div class="feature">
                    <div class="feature-icon">📋</div>
                    <h3>Compliance</h3>
                    <p>Verify compliance with NIST SP 800-88 standards</p>
                </div>
                <div class="feature">
                    <div class="feature-icon">⏰</div>
                    <h3>Timestamp</h3>
                    <p>Confirm when the data wiping operation was performed</p>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        document.getElementById('verifyForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const loading = document.getElementById('loading');
            const result = document.getElementById('result');
            
            loading.style.display = 'block';
            result.style.display = 'none';
            
            const formData = new FormData(this);
            
            try {
                const response = await fetch('/verify', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                loading.style.display = 'none';
                result.style.display = 'block';
                
                if (data.valid) {
                    result.className = 'result success';
                    result.innerHTML = `
                        <h3>✅ Certificate Valid</h3>
                        <p><strong>Certificate ID:</strong> ${data.certificate_id}</p>
                        <p><strong>Timestamp:</strong> ${data.timestamp}</p>
                        <p><strong>Device Type:</strong> ${data.device_info.device_type}</p>
                        <p><strong>Wipe Method:</strong> ${data.wipe_operation.method}</p>
                        <p><strong>Status:</strong> ${data.wipe_operation.status}</p>
                        <p><strong>NIST Classification:</strong> ${data.compliance_info.method_classification}</p>
                        <p><strong>Tool Version:</strong> ${data.tool_info.name} ${data.tool_info.version}</p>
                    `;
                } else {
                    result.className = 'result error';
                    result.innerHTML = `
                        <h3>❌ Certificate Invalid</h3>
                        <p><strong>Error:</strong> ${data.error || 'Certificate verification failed'}</p>
                        ${data.errors ? '<p><strong>Details:</strong> ' + data.errors.join(', ') + '</p>' : ''}
                    `;
                }
            } catch (error) {
                loading.style.display = 'none';
                result.style.display = 'block';
                result.className = 'result error';
                result.innerHTML = `
                    <h3>❌ Verification Error</h3>
                    <p>An error occurred while verifying the certificate: ${error.message}</p>
                `;
            }
        });
        
        // Clear result when file input changes
        document.getElementById('certificate_file').addEventListener('change', function() {
            document.getElementById('result').style.display = 'none';
        });
        
        document.getElementById('certificate_json').addEventListener('input', function() {
            document.getElementById('result').style.display = 'none';
        });
    </script>
</body>
</html>
    """
    
    with open('templates/index.html', 'w') as f:
        f.write(index_html)
    
    # Error template
    error_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Error - VeriWipe Certificate Verifier</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .error-container {
            background: white;
            border-radius: 15px;
            padding: 40px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            text-align: center;
            max-width: 500px;
        }
        .error-code {
            font-size: 4em;
            color: #dc3545;
            margin: 0;
        }
        .error-message {
            font-size: 1.2em;
            color: #666;
            margin: 20px 0;
        }
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 30px;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            text-decoration: none;
            display: inline-block;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="error-container">
        <h1 class="error-code">{{ error_code }}</h1>
        <p class="error-message">{{ error_message }}</p>
        <a href="/" class="btn">🏠 Return Home</a>
    </div>
</body>
</html>
    """
    
    with open('templates/error.html', 'w') as f:
        f.write(error_html)