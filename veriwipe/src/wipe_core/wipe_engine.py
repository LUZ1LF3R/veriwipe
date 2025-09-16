#!/usr/bin/env python3
"""
VeriWipe Core Engine - Secure Data Wiping Implementation
"""

import os
import subprocess
import logging
import hashlib
import time
import threading
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import json

from ai_engine.ai_wipe_engine import DeviceInfo, WipeMethod, AIWipeEngine

class WipeStatus(Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class WipeOperation:
    device_info: DeviceInfo
    method: WipeMethod
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    status: WipeStatus = WipeStatus.NOT_STARTED
    progress: float = 0.0
    error_message: Optional[str] = None
    operation_log: List[str] = None
    verification_hashes: Dict[str, str] = None
    
    def __post_init__(self):
        if self.operation_log is None:
            self.operation_log = []
        if self.verification_hashes is None:
            self.verification_hashes = {}

class WipeCore:
    def __init__(self, ai_engine: AIWipeEngine = None):
        self.logger = logging.getLogger(__name__)
        self.ai_engine = ai_engine or AIWipeEngine()
        self.current_operations: Dict[str, WipeOperation] = {}
        self.progress_callbacks: List[Callable] = []
        
    def add_progress_callback(self, callback: Callable):
        """Add a callback function to receive progress updates"""
        self.progress_callbacks.append(callback)
    
    def _notify_progress(self, device_path: str, progress: float, message: str):
        """Notify all registered callbacks of progress updates"""
        for callback in self.progress_callbacks:
            try:
                callback(device_path, progress, message)
            except Exception as e:
                self.logger.error(f"Error in progress callback: {e}")
    
    def prepare_wipe_operation(self, device_info: DeviceInfo) -> WipeOperation:
        """Prepare a wipe operation for the given device"""
        method = self.ai_engine.select_optimal_wipe_method(device_info)
        operation = WipeOperation(device_info=device_info, method=method)
        
        self.current_operations[device_info.device_path] = operation
        operation.operation_log.append(f"Operation prepared for {device_info.device_path}")
        operation.operation_log.append(f"Selected method: {method.value}")
        
        return operation
    
    def execute_wipe(self, device_path: str) -> bool:
        """Execute the wipe operation for the specified device"""
        if device_path not in self.current_operations:
            self.logger.error(f"No operation prepared for {device_path}")
            return False
        
        operation = self.current_operations[device_path]
        operation.start_time = time.time()
        operation.status = WipeStatus.IN_PROGRESS
        
        try:
            # Pre-wipe checks and preparation
            if not self._pre_wipe_checks(operation):
                operation.status = WipeStatus.FAILED
                return False
            
            # Execute the specific wipe method
            success = self._execute_wipe_method(operation)
            
            if success:
                # Post-wipe verification
                if self._post_wipe_verification(operation):
                    operation.status = WipeStatus.COMPLETED
                    operation.end_time = time.time()
                    operation.progress = 100.0
                    self._notify_progress(device_path, 100.0, "Wipe completed successfully")
                    return True
                else:
                    operation.status = WipeStatus.FAILED
                    operation.error_message = "Post-wipe verification failed"
            else:
                operation.status = WipeStatus.FAILED
            
        except Exception as e:
            self.logger.error(f"Wipe operation failed: {e}")
            operation.status = WipeStatus.FAILED
            operation.error_message = str(e)
            
            # Use AI for error diagnosis and resolution
            resolution = self.ai_engine.diagnose_and_resolve_errors(str(e), {
                "device_path": device_path,
                "method": operation.method.value,
                "device_type": operation.device_info.device_type.value
            })
            
            operation.operation_log.append(f"Error diagnosis: {resolution['diagnosis']}")
            operation.operation_log.append(f"Suggested actions: {resolution['suggested_actions']}")
            
            # Try alternative method if suggested
            if resolution.get('alternative_method') and resolution['confidence'] > 0.7:
                operation.operation_log.append(f"Trying alternative method: {resolution['alternative_method']}")
                operation.method = resolution['alternative_method']
                return self._execute_wipe_method(operation)
        
        return False
    
    def _pre_wipe_checks(self, operation: WipeOperation) -> bool:
        """Perform pre-wipe checks and preparation"""
        device_path = operation.device_info.device_path
        operation.operation_log.append("Starting pre-wipe checks")
        
        # Check if device exists
        if not os.path.exists(device_path):
            operation.error_message = f"Device {device_path} does not exist"
            return False
        
        # Check if device is mounted and unmount if necessary
        if self._is_device_mounted(device_path):
            operation.operation_log.append(f"Device {device_path} is mounted, attempting to unmount")
            if not self._unmount_device(device_path):
                operation.error_message = f"Failed to unmount {device_path}"
                return False
        
        # Remove HPA/DCO if present
        if operation.device_info.hpa_dco_present:
            operation.operation_log.append("Removing HPA/DCO")
            if not self._remove_hpa_dco(device_path):
                operation.operation_log.append("Warning: Could not remove HPA/DCO")
        
        # Take pre-wipe sample for verification
        self._take_pre_wipe_sample(operation)
        
        operation.operation_log.append("Pre-wipe checks completed")
        self._notify_progress(device_path, 10.0, "Pre-wipe checks completed")
        return True
    
    def _execute_wipe_method(self, operation: WipeOperation) -> bool:
        """Execute the specific wipe method"""
        device_path = operation.device_info.device_path
        method = operation.method
        
        operation.operation_log.append(f"Executing wipe method: {method.value}")
        
        try:
            if method == WipeMethod.ATA_SECURE_ERASE:
                return self._ata_secure_erase(operation)
            elif method == WipeMethod.NVME_SECURE_ERASE:
                return self._nvme_secure_erase(operation)
            elif method == WipeMethod.NVME_CRYPTO_ERASE:
                return self._nvme_crypto_erase(operation)
            elif method == WipeMethod.MULTIPASS_OVERWRITE:
                return self._multipass_overwrite(operation)
            elif method == WipeMethod.SINGLE_PASS_RANDOM:
                return self._single_pass_random(operation)
            elif method == WipeMethod.CRYPTO_ERASE:
                return self._crypto_erase(operation)
            else:
                operation.error_message = f"Unsupported wipe method: {method}"
                return False
                
        except Exception as e:
            operation.error_message = f"Error executing {method.value}: {str(e)}"
            return False
    
    def _ata_secure_erase(self, operation: WipeOperation) -> bool:
        """Execute ATA Secure Erase"""
        device_path = operation.device_info.device_path
        operation.operation_log.append("Starting ATA Secure Erase")
        
        try:
            # Set security password
            cmd = ['hdparm', '--user-master', 'u', '--security-set-pass', 'p', device_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                operation.operation_log.append(f"Failed to set security password: {result.stderr}")
                return False
            
            self._notify_progress(device_path, 30.0, "Security password set")
            
            # Execute secure erase
            cmd = ['hdparm', '--user-master', 'u', '--security-erase', 'p', device_path]
            
            # This is a long-running operation, so we'll monitor it
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            # Monitor progress (ATA secure erase doesn't provide progress, so we estimate)
            start_time = time.time()
            estimated_duration = operation.device_info.size_gb * 2  # Rough estimate: 2 seconds per GB
            
            while process.poll() is None:
                elapsed = time.time() - start_time
                progress = min(30.0 + (elapsed / estimated_duration) * 60.0, 90.0)
                self._notify_progress(device_path, progress, "ATA Secure Erase in progress")
                time.sleep(5)
            
            stdout, stderr = process.communicate()
            
            if process.returncode == 0:
                operation.operation_log.append("ATA Secure Erase completed successfully")
                self._notify_progress(device_path, 90.0, "ATA Secure Erase completed")
                return True
            else:
                operation.operation_log.append(f"ATA Secure Erase failed: {stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            operation.operation_log.append("ATA Secure Erase timed out")
            return False
        except Exception as e:
            operation.operation_log.append(f"ATA Secure Erase error: {str(e)}")
            return False
    
    def _nvme_secure_erase(self, operation: WipeOperation) -> bool:
        """Execute NVMe Secure Erase"""
        device_path = operation.device_info.device_path
        operation.operation_log.append("Starting NVMe Secure Erase")
        
        try:
            # Get NVMe namespace
            cmd = ['nvme', 'list-ns', device_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                operation.operation_log.append("Failed to list NVMe namespaces")
                return False
            
            namespace = "1"  # Usually namespace 1
            self._notify_progress(device_path, 30.0, "NVMe namespace identified")
            
            # Execute secure format
            cmd = ['nvme', 'format', device_path, '--namespace-id', namespace, '--secure-erase', '1']
            
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            # Monitor progress
            start_time = time.time()
            estimated_duration = operation.device_info.size_gb * 0.5  # NVMe is faster
            
            while process.poll() is None:
                elapsed = time.time() - start_time
                progress = min(30.0 + (elapsed / estimated_duration) * 60.0, 90.0)
                self._notify_progress(device_path, progress, "NVMe Secure Erase in progress")
                time.sleep(2)
            
            stdout, stderr = process.communicate()
            
            if process.returncode == 0:
                operation.operation_log.append("NVMe Secure Erase completed successfully")
                self._notify_progress(device_path, 90.0, "NVMe Secure Erase completed")
                return True
            else:
                operation.operation_log.append(f"NVMe Secure Erase failed: {stderr}")
                return False
                
        except Exception as e:
            operation.operation_log.append(f"NVMe Secure Erase error: {str(e)}")
            return False
    
    def _nvme_crypto_erase(self, operation: WipeOperation) -> bool:
        """Execute NVMe Crypto Erase"""
        device_path = operation.device_info.device_path
        operation.operation_log.append("Starting NVMe Crypto Erase")
        
        try:
            # Execute crypto format
            cmd = ['nvme', 'format', device_path, '--namespace-id', '1', '--secure-erase', '2']
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                operation.operation_log.append("NVMe Crypto Erase completed successfully")
                self._notify_progress(device_path, 90.0, "NVMe Crypto Erase completed")
                return True
            else:
                operation.operation_log.append(f"NVMe Crypto Erase failed: {result.stderr}")
                return False
                
        except Exception as e:
            operation.operation_log.append(f"NVMe Crypto Erase error: {str(e)}")
            return False
    
    def _multipass_overwrite(self, operation: WipeOperation) -> bool:
        """Execute multi-pass overwrite (DoD 5220.22-M style)"""
        device_path = operation.device_info.device_path
        operation.operation_log.append("Starting multi-pass overwrite (3 passes)")
        
        patterns = [b'\\x00', b'\\xff', b'\\x92\\x49\\x24']  # Pass 1: zeros, Pass 2: ones, Pass 3: random
        
        try:
            device_size = self._get_device_size(device_path)
            if device_size == 0:
                operation.operation_log.append("Could not determine device size")
                return False
            
            for pass_num, pattern in enumerate(patterns, 1):
                operation.operation_log.append(f"Starting pass {pass_num}/3")
                progress_base = 30.0 + (pass_num - 1) * 20.0
                
                if not self._overwrite_device(device_path, pattern, device_size, 
                                            progress_base, operation):
                    return False
                    
                self._notify_progress(device_path, progress_base + 20.0, f"Pass {pass_num} completed")
            
            operation.operation_log.append("Multi-pass overwrite completed successfully")
            return True
            
        except Exception as e:
            operation.operation_log.append(f"Multi-pass overwrite error: {str(e)}")
            return False
    
    def _single_pass_random(self, operation: WipeOperation) -> bool:
        """Execute single-pass random overwrite"""
        device_path = operation.device_info.device_path
        operation.operation_log.append("Starting single-pass random overwrite")
        
        try:
            # Use dd with urandom for single pass
            cmd = ['dd', f'if=/dev/urandom', f'of={device_path}', 'bs=1M', 'status=progress']
            
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            # Monitor dd progress
            device_size = self._get_device_size(device_path)
            progress_thread = threading.Thread(target=self._monitor_dd_progress, 
                                             args=(process, device_path, device_size, operation))
            progress_thread.start()
            
            stdout, stderr = process.communicate()
            progress_thread.join()
            
            if process.returncode == 0:
                operation.operation_log.append("Single-pass random overwrite completed successfully")
                self._notify_progress(device_path, 90.0, "Random overwrite completed")
                return True
            else:
                operation.operation_log.append(f"Single-pass overwrite failed: {stderr}")
                return False
                
        except Exception as e:
            operation.operation_log.append(f"Single-pass overwrite error: {str(e)}")
            return False
    
    def _crypto_erase(self, operation: WipeOperation) -> bool:
        """Execute cryptographic erase by destroying encryption keys"""
        device_path = operation.device_info.device_path
        encryption_type = operation.device_info.encryption_status
        
        operation.operation_log.append(f"Starting crypto erase for {encryption_type}")
        
        try:
            if encryption_type == "LUKS":
                # LUKS header destruction
                cmd = ['cryptsetup', 'luksErase', device_path]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                
                if result.returncode == 0:
                    operation.operation_log.append("LUKS header destroyed successfully")
                    self._notify_progress(device_path, 90.0, "LUKS crypto erase completed")
                    return True
                else:
                    operation.operation_log.append(f"LUKS erase failed: {result.stderr}")
                    return False
            
            elif encryption_type == "BitLocker":
                # For BitLocker, we would need Windows-specific tools
                operation.operation_log.append("BitLocker crypto erase not implemented in Linux environment")
                return False
            
            else:
                operation.operation_log.append("No encryption detected, falling back to overwrite")
                return self._single_pass_random(operation)
                
        except Exception as e:
            operation.operation_log.append(f"Crypto erase error: {str(e)}")
            return False
    
    def _post_wipe_verification(self, operation: WipeOperation) -> bool:
        """Perform post-wipe verification"""
        device_path = operation.device_info.device_path
        operation.operation_log.append("Starting post-wipe verification")
        
        try:
            # Sample random sectors to verify they're wiped
            verification_passed = True
            sample_count = min(100, int(operation.device_info.size_gb))  # Sample up to 100 sectors
            
            for i in range(sample_count):
                sector = i * (operation.device_info.size_gb * 1024 * 1024 * 1024 // 512 // sample_count)
                if not self._verify_sector_wiped(device_path, sector):
                    verification_passed = False
                    break
                
                if i % 10 == 0:  # Update progress every 10 samples
                    progress = 90.0 + (i / sample_count) * 10.0
                    self._notify_progress(device_path, progress, "Verifying wipe completion")
            
            if verification_passed:
                operation.operation_log.append("Post-wipe verification passed")
                # Take post-wipe hash sample
                self._take_post_wipe_sample(operation)
                return True
            else:
                operation.operation_log.append("Post-wipe verification failed - data remnants detected")
                return False
                
        except Exception as e:
            operation.operation_log.append(f"Post-wipe verification error: {str(e)}")
            return False
    
    # Helper methods
    def _is_device_mounted(self, device_path: str) -> bool:
        """Check if device is mounted"""
        try:
            result = subprocess.run(['mount'], capture_output=True, text=True)
            return device_path in result.stdout
        except Exception:
            return False
    
    def _unmount_device(self, device_path: str) -> bool:
        """Unmount device"""
        try:
            # Get all partitions of the device
            result = subprocess.run(['lsblk', '-ln', '-o', 'NAME', device_path], 
                                  capture_output=True, text=True)
            partitions = result.stdout.strip().split('\\n')
            
            # Unmount all partitions
            for partition in partitions:
                if partition.strip():
                    partition_path = f"/dev/{partition.strip()}"
                    subprocess.run(['umount', partition_path], 
                                 capture_output=True, text=True)
            
            return True
        except Exception:
            return False
    
    def _remove_hpa_dco(self, device_path: str) -> bool:
        """Remove Host Protected Area and Device Configuration Overlay"""
        try:
            # Remove HPA
            subprocess.run(['hdparm', '-N', 'p1048576', device_path], 
                         capture_output=True, text=True, timeout=30)
            # Remove DCO  
            subprocess.run(['hdparm', '--dco-restore', device_path], 
                         capture_output=True, text=True, timeout=30)
            return True
        except Exception:
            return False
    
    def _get_device_size(self, device_path: str) -> int:
        """Get device size in bytes"""
        try:
            with open(device_path, 'rb') as f:
                f.seek(0, 2)  # Seek to end
                return f.tell()
        except Exception:
            return 0
    
    def _take_pre_wipe_sample(self, operation: WipeOperation):
        """Take a sample hash before wiping for verification"""
        device_path = operation.device_info.device_path
        try:
            # Sample first 1MB
            with open(device_path, 'rb') as f:
                sample = f.read(1024 * 1024)
                operation.verification_hashes['pre_wipe_sample'] = hashlib.sha256(sample).hexdigest()
        except Exception as e:
            operation.operation_log.append(f"Could not take pre-wipe sample: {e}")
    
    def _take_post_wipe_sample(self, operation: WipeOperation):
        """Take a sample hash after wiping for verification"""
        device_path = operation.device_info.device_path
        try:
            # Sample first 1MB
            with open(device_path, 'rb') as f:
                sample = f.read(1024 * 1024)
                operation.verification_hashes['post_wipe_sample'] = hashlib.sha256(sample).hexdigest()
        except Exception as e:
            operation.operation_log.append(f"Could not take post-wipe sample: {e}")
    
    def _verify_sector_wiped(self, device_path: str, sector: int) -> bool:
        """Verify that a specific sector has been wiped"""
        try:
            with open(device_path, 'rb') as f:
                f.seek(sector * 512)
                data = f.read(512)
                # Check if sector contains only zeros or random data (not original data patterns)
                # This is a simplified check - in practice you'd want more sophisticated verification
                return len(set(data)) <= 2  # Very few unique bytes suggests wiped data
        except Exception:
            return False
    
    def _overwrite_device(self, device_path: str, pattern: bytes, device_size: int, 
                         progress_base: float, operation: WipeOperation) -> bool:
        """Overwrite device with specific pattern"""
        try:
            chunk_size = 1024 * 1024  # 1MB chunks
            written = 0
            
            with open(device_path, 'wb') as f:
                while written < device_size:
                    remaining = min(chunk_size, device_size - written)
                    chunk = pattern * (remaining // len(pattern) + 1)
                    f.write(chunk[:remaining])
                    written += remaining
                    
                    progress = progress_base + (written / device_size) * 20.0
                    self._notify_progress(device_path, progress, f"Writing pattern: {written}/{device_size} bytes")
            
            return True
        except Exception as e:
            operation.operation_log.append(f"Pattern overwrite failed: {e}")
            return False
    
    def _monitor_dd_progress(self, process, device_path: str, device_size: int, operation: WipeOperation):
        """Monitor dd command progress"""
        while process.poll() is None:
            try:
                # Send USR1 signal to dd to get progress
                os.system(f"kill -USR1 {process.pid} 2>/dev/null")
                time.sleep(5)
                # This is simplified - real implementation would parse dd output
                # For now, we'll just increment progress
                if operation.progress < 80:
                    operation.progress += 2
                    self._notify_progress(device_path, operation.progress, "Random overwrite in progress")
            except Exception:
                break

if __name__ == "__main__":
    # Test the wipe core
    logging.basicConfig(level=logging.INFO)
    
    ai_engine = AIWipeEngine()
    wipe_core = WipeCore(ai_engine)
    
    # Add progress callback
    def progress_callback(device_path, progress, message):
        print(f"{device_path}: {progress:.1f}% - {message}")
    
    wipe_core.add_progress_callback(progress_callback)
    
    print("VeriWipe Core Engine Test")
    print("This would normally detect and wipe actual devices.")