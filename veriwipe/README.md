# VeriWipe: AI-Powered Secure Data Wiping Bootable ISO

## Overview

VeriWipe is a cross-platform, AI-powered secure data wiping solution designed for trustworthy IT asset recycling. This implementation focuses on a bootable Linux ISO/USB with offline capabilities.

## Features

- **AI-Powered Adaptive Wiping**: Automatically selects optimal wipe method based on device type
- **Cross-Platform Support**: Windows, Linux, Android
- **Offline-First Design**: Full functionality without network connectivity
- **Tamper-Proof Certificates**: Digitally signed PDF + JSON certificates
- **Standards Compliant**: NIST SP 800-88 aligned
- **Secure Hardware Support**: ATA/NVMe secure erase, HPA/DCO handling

## Project Structure

```
veriwipe/
├── src/
│   ├── wipe_core/          # Core wiping engine
│   ├── ai_engine/          # AI modules for adaptive selection
│   ├── certificate_engine/ # Certificate generation
│   └── gui/               # User interface
├── iso_builder/           # ISO creation scripts
├── verification/          # Certificate verification tools
├── models/               # AI models (offline)
├── config/               # Configuration files
└── docs/                 # Documentation
```

## Quick Start

1. Build the ISO: `./iso_builder/build_iso.sh`
2. Flash to USB: `dd if=veriwipe.iso of=/dev/sdX bs=4M`
3. Boot from USB and follow the one-click interface

## License

Open Source - to be determined based on project requirements
