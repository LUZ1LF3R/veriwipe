#!/usr/bin/env python3
"""
VeriWipe AI Engine - Adaptive Wipe Method Selection and Error Resolution
"""

import json
import logging
import subprocess
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import pickle
import os

class DeviceType(Enum):
    HDD = "hdd"
    SSD_SATA = "ssd_sata"
    SSD_NVME = "ssd_nvme"
    EMMC = "emmc"
    USB = "usb"
    UNKNOWN = "unknown"

class WipeMethod(Enum):
    ATA_SECURE_ERASE = "ata_secure_erase"
    NVME_SECURE_ERASE = "nvme_secure_erase"
    NVME_CRYPTO_ERASE = "nvme_crypto_erase"
    MULTIPASS_OVERWRITE = "multipass_overwrite"
    SINGLE_PASS_RANDOM = "single_pass_random"
    CRYPTO_ERASE = "crypto_erase"
    FACTORY_RESET = "factory_reset"

@dataclass
class DeviceInfo:
    device_path: str
    device_type: DeviceType
    model: str
    serial: str
    size_gb: float
    interface: str
    encryption_status: str
    hpa_dco_present: bool
    secure_erase_supported: bool
    features: Dict[str, any]

class AIWipeEngine:
    def __init__(self, model_path: str = None):
        self.logger = logging.getLogger(__name__)
        self.model_path = model_path or "/opt/veriwipe/models/wipe_method_selector.pkl"
        self.device_classifier = None
        self.method_selector = None
        self.load_models()
        
    def load_models(self):
        """Load pre-trained AI models for device classification and method selection"""
        try:
            if os.path.exists(self.model_path):
                with open(self.model_path, 'rb') as f:
                    models = pickle.load(f)
                    self.device_classifier = models.get('device_classifier')
                    self.method_selector = models.get('method_selector')
                self.logger.info("AI models loaded successfully")
            else:
                self.logger.warning("No pre-trained models found. Using rule-based fallback.")
                self.initialize_fallback_models()
        except Exception as e:
            self.logger.error(f"Error loading AI models: {e}")
            self.initialize_fallback_models()
    
    def initialize_fallback_models(self):
        """Initialize simple rule-based models as fallback"""
        # Create basic classifiers - in production these would be pre-trained
        self.device_classifier = RandomForestClassifier(n_estimators=10, random_state=42)
        self.method_selector = RandomForestClassifier(n_estimators=10, random_state=42)
        
        # Train with minimal synthetic data for demo purposes
        X_device = np.random.rand(100, 5)  # Features: size, interface_type, etc.
        y_device = np.random.randint(0, 5, 100)  # Device types
        
        X_method = np.random.rand(100, 6)  # Features: device_type, size, encryption, etc.
        y_method = np.random.randint(0, 7, 100)  # Wipe methods
        
        self.device_classifier.fit(X_device, y_device)
        self.method_selector.fit(X_method, y_method)
    
    def detect_devices(self) -> List[DeviceInfo]:
        """Detect all storage devices and classify them using AI"""
        devices = []
        
        try:
            # Get block devices
            result = subprocess.run(['lsblk', '-J', '-o', 'NAME,TYPE,SIZE,MODEL,SERIAL,TRAN'], 
                                  capture_output=True, text=True, check=True)
            block_devices = json.loads(result.stdout)
            
            for device in block_devices.get('blockdevices', []):
                if device.get('type') == 'disk':
                    device_info = self._analyze_device(device)
                    if device_info:
                        devices.append(device_info)
                        
        except Exception as e:
            self.logger.error(f"Error detecting devices: {e}")
        
        return devices
    
    def _analyze_device(self, device_data: Dict) -> Optional[DeviceInfo]:
        """Analyze individual device using AI classification"""
        try:
            device_path = f"/dev/{device_data['name']}"
            
            # Extract basic information
            model = device_data.get('model', 'Unknown')
            serial = device_data.get('serial', 'Unknown')
            size_str = device_data.get('size', '0B')
            interface = device_data.get('tran', 'unknown')
            
            # Parse size
            size_gb = self._parse_size_to_gb(size_str)
            
            # Get detailed device information
            features = self._get_device_features(device_path)
            
            # Classify device type using AI
            device_type = self._classify_device_type(features)
            
            # Check for encryption, HPA/DCO
            encryption_status = self._check_encryption(device_path)
            hpa_dco_present = self._check_hpa_dco(device_path)
            secure_erase_supported = self._check_secure_erase_support(device_path, device_type)
            
            return DeviceInfo(
                device_path=device_path,
                device_type=device_type,
                model=model,
                serial=serial,
                size_gb=size_gb,
                interface=interface,
                encryption_status=encryption_status,
                hpa_dco_present=hpa_dco_present,
                secure_erase_supported=secure_erase_supported,
                features=features
            )
            
        except Exception as e:
            self.logger.error(f"Error analyzing device {device_data}: {e}")
            return None
    
    def _get_device_features(self, device_path: str) -> Dict:
        """Extract detailed device features for AI analysis"""
        features = {}
        
        try:
            # Get SMART data
            smart_result = subprocess.run(['smartctl', '-a', device_path], 
                                        capture_output=True, text=True)
            features['smart_data'] = smart_result.stdout
            
            # Get detailed device info
            hdparm_result = subprocess.run(['hdparm', '-I', device_path], 
                                         capture_output=True, text=True)
            features['hdparm_info'] = hdparm_result.stdout
            
            # Check if it's NVMe
            if 'nvme' in device_path:
                nvme_result = subprocess.run(['nvme', 'id-ctrl', device_path], 
                                           capture_output=True, text=True)
                features['nvme_info'] = nvme_result.stdout
                
        except Exception as e:
            self.logger.debug(f"Could not get all features for {device_path}: {e}")
        
        return features
    
    def _classify_device_type(self, features: Dict) -> DeviceType:
        """Use AI to classify device type based on features"""
        # Extract numerical features for AI model
        feature_vector = self._extract_feature_vector(features)
        
        if self.device_classifier and len(feature_vector) >= 5:
            try:
                prediction = self.device_classifier.predict([feature_vector])[0]
                device_types = list(DeviceType)
                if 0 <= prediction < len(device_types):
                    return device_types[prediction]
            except Exception as e:
                self.logger.debug(f"AI classification failed: {e}")
        
        # Fallback to rule-based classification
        return self._rule_based_device_classification(features)
    
    def _rule_based_device_classification(self, features: Dict) -> DeviceType:
        """Fallback rule-based device classification"""
        smart_data = features.get('smart_data', '').lower()
        hdparm_info = features.get('hdparm_info', '').lower()
        nvme_info = features.get('nvme_info', '').lower()
        
        if nvme_info or 'nvme' in smart_data:
            return DeviceType.SSD_NVME
        elif 'solid state' in smart_data or 'ssd' in hdparm_info:
            return DeviceType.SSD_SATA
        elif 'emmc' in smart_data or 'mmc' in hdparm_info:
            return DeviceType.EMMC
        elif 'usb' in smart_data:
            return DeviceType.USB
        elif 'rotating' in smart_data or 'disk' in hdparm_info:
            return DeviceType.HDD
        else:
            return DeviceType.UNKNOWN
    
    def _extract_feature_vector(self, features: Dict) -> List[float]:
        """Extract numerical features for AI model"""
        vector = []
        
        smart_data = features.get('smart_data', '')
        hdparm_info = features.get('hdparm_info', '')
        
        # Feature 1: Rotation speed (0 for SSD, >0 for HDD)
        rotation_match = re.search(r'(\d+)\s*rpm', smart_data.lower())
        rotation_speed = float(rotation_match.group(1)) if rotation_match else 0.0
        vector.append(rotation_speed)
        
        # Feature 2: Has TRIM support (1 for SSD, 0 for HDD)
        trim_support = 1.0 if 'trim' in hdparm_info.lower() else 0.0
        vector.append(trim_support)
        
        # Feature 3: Interface speed indicator
        interface_speed = 0.0
        if 'sata 6' in smart_data.lower():
            interface_speed = 6.0
        elif 'sata 3' in smart_data.lower():
            interface_speed = 3.0
        elif 'nvme' in smart_data.lower():
            interface_speed = 32.0  # PCIe indicator
        vector.append(interface_speed)
        
        # Feature 4: Power-on hours (age indicator)
        power_hours_match = re.search(r'power.on.hours.*?(\d+)', smart_data.lower())
        power_hours = float(power_hours_match.group(1)) if power_hours_match else 0.0
        vector.append(power_hours)
        
        # Feature 5: Temperature (operational indicator)
        temp_match = re.search(r'temperature.*?(\d+)', smart_data.lower())
        temperature = float(temp_match.group(1)) if temp_match else 25.0
        vector.append(temperature)
        
        # Pad vector to required length
        while len(vector) < 5:
            vector.append(0.0)
        
        return vector[:5]  # Ensure exactly 5 features
    
    def _parse_size_to_gb(self, size_str: str) -> float:
        """Parse size string to GB"""
        size_str = size_str.upper()
        multipliers = {'K': 1e-6, 'M': 1e-3, 'G': 1, 'T': 1e3}
        
        for unit, multiplier in multipliers.items():
            if unit in size_str:
                number = re.findall(r'[\d.]+', size_str)
                if number:
                    return float(number[0]) * multiplier
        return 0.0
    
    def _check_encryption(self, device_path: str) -> str:
        """Check if device is encrypted"""
        try:
            # Check for LUKS
            luks_result = subprocess.run(['cryptsetup', 'isLuks', device_path], 
                                       capture_output=True)
            if luks_result.returncode == 0:
                return "LUKS"
            
            # Check for BitLocker (when mounted)
            mount_result = subprocess.run(['mount'], capture_output=True, text=True)
            if device_path in mount_result.stdout and 'bitlocker' in mount_result.stdout.lower():
                return "BitLocker"
            
            return "None"
        except Exception:
            return "Unknown"
    
    def _check_hpa_dco(self, device_path: str) -> bool:
        """Check for Host Protected Area (HPA) or Device Configuration Overlay (DCO)"""
        try:
            result = subprocess.run(['hdparm', '-N', device_path], 
                                  capture_output=True, text=True)
            output = result.stdout.lower()
            return 'hpa' in output or 'dco' in output or 'protected' in output
        except Exception:
            return False
    
    def _check_secure_erase_support(self, device_path: str, device_type: DeviceType) -> bool:
        """Check if device supports secure erase"""
        try:
            if device_type == DeviceType.SSD_NVME:
                result = subprocess.run(['nvme', 'id-ctrl', device_path], 
                                      capture_output=True, text=True)
                return 'format' in result.stdout.lower()
            else:
                result = subprocess.run(['hdparm', '-I', device_path], 
                                      capture_output=True, text=True)
                return 'erase_unit_max' in result.stdout.lower()
        except Exception:
            return False
    
    def select_optimal_wipe_method(self, device_info: DeviceInfo) -> WipeMethod:
        """Use AI to select the optimal wipe method for the device"""
        # Create feature vector for method selection
        method_features = [
            device_info.device_type.value.__hash__() % 10,  # Device type encoding
            device_info.size_gb,
            1.0 if device_info.encryption_status != "None" else 0.0,
            1.0 if device_info.secure_erase_supported else 0.0,
            1.0 if device_info.hpa_dco_present else 0.0,
            device_info.interface.__hash__() % 10  # Interface encoding
        ]
        
        if self.method_selector:
            try:
                prediction = self.method_selector.predict([method_features])[0]
                methods = list(WipeMethod)
                if 0 <= prediction < len(methods):
                    selected_method = methods[prediction]
                    self.logger.info(f"AI selected method: {selected_method}")
                    return selected_method
            except Exception as e:
                self.logger.debug(f"AI method selection failed: {e}")
        
        # Fallback to rule-based selection
        return self._rule_based_method_selection(device_info)
    
    def _rule_based_method_selection(self, device_info: DeviceInfo) -> WipeMethod:
        """Fallback rule-based method selection"""
        # Encryption-first approach
        if device_info.encryption_status in ["LUKS", "BitLocker"]:
            return WipeMethod.CRYPTO_ERASE
        
        # Device-specific optimal methods
        if device_info.device_type == DeviceType.SSD_NVME:
            if device_info.secure_erase_supported:
                return WipeMethod.NVME_SECURE_ERASE
            else:
                return WipeMethod.NVME_CRYPTO_ERASE
        
        elif device_info.device_type in [DeviceType.SSD_SATA, DeviceType.EMMC]:
            if device_info.secure_erase_supported:
                return WipeMethod.ATA_SECURE_ERASE
            else:
                return WipeMethod.SINGLE_PASS_RANDOM
        
        elif device_info.device_type == DeviceType.HDD:
            if device_info.secure_erase_supported:
                return WipeMethod.ATA_SECURE_ERASE
            else:
                return WipeMethod.MULTIPASS_OVERWRITE
        
        else:
            return WipeMethod.SINGLE_PASS_RANDOM
    
    def diagnose_and_resolve_errors(self, error_message: str, context: Dict) -> Dict:
        """AI-powered error diagnosis and resolution"""
        resolution = {
            "diagnosis": "Unknown error",
            "suggested_actions": ["Check system logs", "Retry operation"],
            "alternative_method": None,
            "confidence": 0.5
        }
        
        error_lower = error_message.lower()
        
        # Pattern matching for common errors
        if "permission denied" in error_lower:
            resolution.update({
                "diagnosis": "Insufficient permissions",
                "suggested_actions": ["Run as root/administrator", "Check device permissions"],
                "confidence": 0.9
            })
        
        elif "device busy" in error_lower or "resource busy" in error_lower:
            resolution.update({
                "diagnosis": "Device is mounted or in use",
                "suggested_actions": ["Unmount device", "Stop processes using device", "Kill fuser processes"],
                "confidence": 0.95
            })
        
        elif "not supported" in error_lower:
            resolution.update({
                "diagnosis": "Operation not supported by device",
                "suggested_actions": ["Try alternative wipe method"],
                "alternative_method": WipeMethod.SINGLE_PASS_RANDOM,
                "confidence": 0.8
            })
        
        elif "timeout" in error_lower:
            resolution.update({
                "diagnosis": "Operation timeout",
                "suggested_actions": ["Increase timeout", "Check device health", "Try slower method"],
                "confidence": 0.7
            })
        
        return resolution

if __name__ == "__main__":
    # Test the AI engine
    logging.basicConfig(level=logging.INFO)
    engine = AIWipeEngine()
    
    print("Detecting devices...")
    devices = engine.detect_devices()
    
    for device in devices:
        print(f"\nDevice: {device.device_path}")
        print(f"Type: {device.device_type}")
        print(f"Model: {device.model}")
        print(f"Size: {device.size_gb:.2f} GB")
        
        method = engine.select_optimal_wipe_method(device)
        print(f"Recommended method: {method}")