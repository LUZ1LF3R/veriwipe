# 🔧 VeriWipe Ubuntu VM Troubleshooting Guide

## 🎯 **Quick Fix Commands**

If you're getting "missing dependencies" errors, run these commands in your Ubuntu VM:

### **Step 1: Navigate to VeriWipe Directory**

```bash
cd /path/to/your/veriwipe  # Replace with your actual path
```

### **Step 2: Run Auto-Setup Script**

```bash
chmod +x setup_ubuntu.sh
./setup_ubuntu.sh
```

### **Step 3: Manual Dependency Installation (if auto-setup fails)**

#### **System Dependencies:**

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-dev python3-venv build-essential

# PyQt5 system packages
sudo apt install -y python3-pyqt5 python3-pyqt5.qtcore python3-pyqt5.qtgui python3-pyqt5.qtwidgets

# Cryptography dependencies
sudo apt install -y libssl-dev libffi-dev libcairo2-dev

# Disk utilities
sudo apt install -y hdparm nvme-cli smartmontools parted
```

#### **Python Dependencies:**

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python packages
pip install --upgrade pip
pip install PyQt5>=5.15.4
pip install cryptography>=3.4.8
pip install reportlab>=3.6.0
pip install "qrcode[pil]>=7.3.1"
pip install scikit-learn>=1.0.0
pip install numpy scipy psutil pycryptodome flask pillow
```

### **Step 4: Test VeriWipe**

```bash
# Activate virtual environment
source venv/bin/activate

# Test dependencies
python3 -c "import PyQt5, cryptography, reportlab, qrcode, sklearn; print('✅ All dependencies OK')"

# Run VeriWipe
sudo ./venv/bin/python veriwipe.py --gui
```

---

## 🐛 **Common Issues & Solutions**

### **Issue 1: "ModuleNotFoundError: No module named 'PyQt5'"**

**Solution:**

```bash
# Install system PyQt5 first
sudo apt install -y python3-pyqt5 python3-pyqt5.qtcore python3-pyqt5.qtgui python3-pyqt5.qtwidgets

# Then install via pip in virtual environment
source venv/bin/activate
pip install PyQt5
```

### **Issue 2: "ImportError: libffi.so.6: cannot open shared object file"**

**Solution:**

```bash
sudo apt install -y libffi-dev libssl-dev
source venv/bin/activate
pip uninstall cryptography
pip install cryptography
```

### **Issue 3: "Permission denied" when running VeriWipe**

**Solution:**

```bash
# VeriWipe needs root for disk operations
sudo ./venv/bin/python veriwipe.py --gui

# Or make script executable
chmod +x veriwipe.py
sudo ./veriwipe.py --gui
```

### **Issue 4: "Could not find Qt platform plugin"**

**Solution:**

```bash
# Install Qt5 platform plugins
sudo apt install -y qt5-default qtbase5-dev qtbase5-dev-tools

# Set Qt plugin path
export QT_QPA_PLATFORM_PLUGIN_PATH=/usr/lib/x86_64-linux-gnu/qt5/plugins/platforms
```

### **Issue 5: Virtual environment not working**

**Solution:**

```bash
# Remove old venv and recreate
rm -rf venv
python3 -m venv venv --system-site-packages
source venv/bin/activate
pip install -r requirements.txt
```

---

## 🔍 **Debugging Steps**

### **1. Check Python Version**

```bash
python3 --version  # Should be 3.9+
```

### **2. Check Virtual Environment**

```bash
source venv/bin/activate
which python  # Should point to venv/bin/python
```

### **3. List Installed Packages**

```bash
source venv/bin/activate
pip list | grep -E "(PyQt5|cryptography|reportlab|qrcode|sklearn)"
```

### **4. Test Individual Imports**

```bash
source venv/bin/activate
python3 -c "import PyQt5; print('PyQt5 OK')"
python3 -c "import cryptography; print('cryptography OK')"
python3 -c "import reportlab; print('reportlab OK')"
python3 -c "import qrcode; print('qrcode OK')"
python3 -c "import sklearn; print('sklearn OK')"
```

### **5. Check System Dependencies**

```bash
dpkg -l | grep -E "(python3-pyqt5|libssl|libffi)"
```

---

## 🚀 **Running VeriWipe**

### **GUI Mode (Recommended for Demo):**

```bash
cd /path/to/veriwipe
source venv/bin/activate
sudo ./venv/bin/python veriwipe.py --gui
```

### **CLI Mode:**

```bash
cd /path/to/veriwipe
source venv/bin/activate
sudo ./venv/bin/python veriwipe.py --help
sudo ./venv/bin/python veriwipe.py --list-devices
```

### **Development Mode:**

```bash
cd /path/to/veriwipe
source venv/bin/activate
sudo ./venv/bin/python veriwipe.py --debug --gui
```

---

## 📋 **VM-Specific Notes**

### **VM Display Issues:**

```bash
# If GUI doesn't display properly
export DISPLAY=:0
xhost +local:

# For headless VM with X11 forwarding
ssh -X user@vm-ip
```

### **VM Performance:**

- Allocate at least 2GB RAM to VM
- Enable hardware acceleration if available
- Ensure VM has access to USB devices for testing

### **Storage Access:**

```bash
# Check if VM can see storage devices
lsblk
sudo fdisk -l
```

---

## ✅ **Success Indicators**

You know VeriWipe is working when:

- [ ] No import errors when launching
- [ ] GUI window opens successfully
- [ ] Device detection finds storage devices
- [ ] No Python traceback errors

---

## 🆘 **Emergency Demo Setup**

If all else fails for your demo:

```bash
# Quick system Python approach (not recommended for production)
sudo apt install -y python3-pyqt5 python3-pip
sudo pip3 install cryptography reportlab qrcode scikit-learn numpy scipy psutil pycryptodome flask pillow
sudo python3 veriwipe.py --gui
```

**Note:** This installs globally and may cause conflicts, but works for demonstrations.

---

Let me know which specific error message you're getting, and I can provide more targeted help!
