# Secure Data Wiping for Trustworthy IT Asset Recycling (SIH 2025)

**Problem Statement ID:** 25070 — Secure Data Wiping for Trustworthy IT Asset Recycling

**Team:** 4× Cybersecurity | 1× Blockchain | 1× Quantum (6 members)

---

## Executive Summary

We propose **VeriWipe** — a user-friendly, cross-platform, tamper-evident secure data-wiping system targeting Windows, Linux and Android devices. VeriWipe combines proven sanitization techniques (NIST SP 800-88 aligned), device-level secure erase commands (ATA/NVMe crypto-erase), OS-specific flows (BitLocker/Windows PE, Linux live environment, Android factory image + crypto-erase), and cryptographic attestation and immutable anchoring (blockchain anchoring + PDF/JSON digitally signed certificates). The system will be distributable as an **installer + offline bootable ISO/USB**, operate with a one-click UX for lay users, and provide verifiable, third-party-checkable evidence of erasure.

Key differentiators:
- Cross-platform support (Windows, Linux, Android).
- Standards-compliant (NIST SP 800-88 mapping included).
- Tamper-proof certificates (PDF+JSON) signed by a private key; certificate hashes anchored on-chain (optional) for immutable proof.
- Offline-first design: full functionality without network; certificates can be signed locally; optional later anchoring when online.
- Third-party verification via public key verification and blockchain transaction.
- Support for physical/hidden areas: HPA/DCO, ATA secure erase, NVMe secure erase, crypto-erase, and secure erasure for SSDs.

---

## Goals & Requirements (from Problem Statement)
- Securely erase all user data including hidden areas (HPA/DCO, SSD sectors).
- Produce digitally-signed, tamper-proof wipe certificates (PDF + JSON).
- Intuitive one-click UI for general public.
- Offline usability (bootable ISO/USB).
- Allow third-party verification of wipe status.
- Scalable, standards-compliant (NIST SP 800-88) and transparent.

---

## High-level Architecture

1. **Device Agent / Wipe Engine** (platform-specific modules):
   - Windows Agent (GUI + WinPE-based offline mode).
   - Linux Agent (daemon + live ISO GUI).
   - Android Agent (app + recovery/fastboot offline flow).

2. **Wipe Core** — shared modules implementing sanitization primitives:
   - Block device commands: ATA Secure Erase, NVMe Secure Erase, hdparm HPA/DCO handling, blkdiscard, dd, shred fallback.
   - Crypto-erase module (destroy encryption keys for FDE).
   - Filesystem-aware secure delete for mounted filesystems.

3. **Certificate Generator**
   - Creates JSON manifest of operation (device metadata, methods, timestamps, tool hashes, operation logs, outcome).
   - Generates signed PDF certificate embedding the JSON + verification QR code.
   - Uses local private key (software/HSM/TPM) for signing.

4. **Audit & Logging**
   - Local tamper-evident logs (append-only, chained hash entries).
   - Optionally anchor certificate hash to a public blockchain (Ethereum L2 or Indian public ledger) for immutable proof.

5. **Verification Server / Public Verifier UI** (optional online component)
   - Accepts JSON + signature or uses on-chain hash to verify authenticity.
   - Displays verification result and audit trail.

6. **Distribution**
   - GUI installers for each OS.
   - Bootable ISO/USB built with Linux live environment and GUI.

---

## Device & Storage Erasure Methods (detailed)

> We map choices to NIST SP 800-88 actions: Clear, Purge, Destroy.

### HDDs (magnetic disks)
- **Purge**: Multiple overwrites (DoD 5220.22-M style or single pass depending on study) using `shred`/`dd` with randomized patterns. Provide option for 1-pass random or 3/7-pass modes for regulatory needs.
- **Verify**: Sample hashing before/after and log of overwrite completion.

### SSDs & eMMC / NVMe
- Avoid naive multiple overwrites — use device-supported methods:
  - **ATA Secure Erase** (`hdparm --security-erase`), when supported.
  - **NVMe Secure Erase / Format** (`nvme format` with secure-erase or crypto-erase flags).
  - **Cryptographic Erase (recommended)**: If full-disk encryption is enabled (LUKS, BitLocker, FileVault-like), destroy the encryption key (fast, effective). For drives without encryption, offer an on-the-fly encryption step followed by crypto-erase (write new key, then delete) when user consents.
- **HPA/DCO**: Detect & remove using `hdparm --read-sector` and `--dco` / `--hpa` controls; resize to full capacity and run secure erase.

### Logical/OS-level (mounted filesystems)
- Filesystem secure delete tools for loose files (srm-like), wiping metadata, journaling areas; then unmount and run block-level purge.

### Android devices
- **Unencrypted devices**: Force factory reset may leave remnants. Our offline recommended path: boot into custom recovery (signed by OEM or using unlocked bootloader) and run block-level secure erase (if allowed) or apply full-disk on-the-fly encryption then crypto-erase.
- **Encrypted devices**: Factory reset + key deletion (cryptographic erase) is effective. For devices with hardware-backed key stores, perform keystore wipe.
- Use `fastboot` / `adb` pathways in unlocked devices; for locked devices rely on OS factory reset + clear encryption keys where possible.

### Windows
- If **BitLocker** enabled: Use `manage-bde -Forcerecovery -on` or key deletion flows to crypto-erase.
- Windows PE environment: run `diskpart clean all` (for HDD) or `diskpart` secure erase commands, or call ATA/NVMe secure erase utilities.

---

## Certificate & Tamper-Proofing Design

Certificate contains:
- Device metadata: make, model, serial (user-consent), unique device fingerprint (non-sensitive salted hash), storage type, capacity.
- Pre-wipe manifest: optional hashed snapshot (salted) and tool version hashes.
- Wipe method(s) used and parameters.
- Start & end timestamps (UTC) and operation logs.
- Outcome: success/failure + verification checksums.
- Signature by the tool's private key (ECDSA with P-256 recommended).

Outputs:
- **JSON**: canonical machine-readable manifest and signature.
- **PDF**: human-friendly certificate with embedded QR code linking to online verification page or containing the JSON hash and signature.

Tamper-evidence techniques:
- **Digital Signature**: Certificate JSON signed with private key. Verifier uses public key (bundled or published) to validate.
- **Chained Logs**: Append-only log where each log entry contains previous entry hash (blockchain-like local chain) making deletion/insertion detectable.
- **Optional Blockchain Anchoring**: Post certificate-hash to a public chain (or an Indian government-backed registry) to provide immutable timestamped proof. The blockchain tx ID is included on the PDF.
- **TPM integration**: When available, sign using TPM-resident keys and perform remote attestation of tool code integrity.

Privacy considerations:
- Do **not** expose raw pre-wipe data; only hashes salted with ephemeral nonce under user control to avoid leakage.
- Provide user controls to redact serials or use partial identifiers for public certificates while storing full details in encrypted local logs (user-controlled access).

---

## Third-party Verification Flow

1. Verifier obtains the JSON certificate (or scans PDF QR). The certificate includes the signature and optionally blockchain tx ID.
2. Verifier downloads the public key (or checks known public key fingerprints published by the project / ministry) and verifies the signature.
3. If blockchain anchoring used: verifier checks the chain to make sure certificate hash matches the on-chain anchor.
4. Verifier can check operation log hashes (chained) to confirm no tampering.

This enables independent auditors, recyclers, or buyers to confirm a wipe was performed by a trusted tool.

---

## User Experience (One-click flow)

- **Launch**: Simple welcome screen explaining irreversible consequences.
- **Device detection & pre-checks**: Show storage devices found, recommend the best wipe method (e.g., ATA secure erase, NVMe crypto-erase). Show warnings and require explicit consent (checkboxes).
- **One-Click Wipe**: "Wipe & Certify" button triggers automatic pre-checks, issues the selected method, monitors progress, and produces the certificate.
- **Progress & Safety**: Progress bar with clear estimated completion steps (no time estimates for unknown hardware; instead '% complete based on stages'), cancel allowed before key irreversible step.
- **Output**: PDF + JSON certificate saved to USB / displayed / printable. QR code for verification.

Offline mode: identical but no blockchain anchoring; the signed certificate can be anchored later when network available.

---

## Security & Key Management

- Use **ECDSA P-256** or Ed25519 for signatures.
- Private signing key options:
  - **Local software key** (for prototype) stored encrypted with passphrase.
  - **TPM/HSM-backed key** (preferred) for production to prevent key extraction.
- Key rotation & revocation plan: publish key fingerprints and maintain a simple revocation list if keys are compromised.

---

## NIST SP 800-88 Compliance Mapping

We provide a table mapping each sanitization step to NIST SP 800-88 recommendations (Clear, Purge, Destroy). (Detailed table included in annex of this doc.)

---

## Prototype Plan & Minimum Viable Product (MVP)

**MVP scope (for SIH submission/demo):**
1. Linux live ISO with GUI providing:
   - ATA secure erase, NVMe secure erase, blkdiscard for supported devices.
   - HPA/DCO detection & removal.
   - One-click wipe and local JSON+PDF certificate signed by a local key.
2. Windows Agent (installer) supporting:
   - Detection of BitLocker and crypto-erase; invoke WinPE for offline block-level erase.
   - PDF/JSON certificate generation and signature verification tool.
3. Android companion doc & demo on an unlocked test device showing factory reset + key destruction.
4. Verification web page to check JSON signature and (optionally) show blockchain anchor status.

**Deliverables for demo:** Bootable USB with live GUI, sample devices wiped in demo, generated PDF certificates, verification webpage, and a short recorded or live demo script.

---

## Technical Stack & Tools

- **Language:** Rust / Go for Wipe Core (safety + speed). Python for orchestration and prototype GUI (PyQt/Tkinter) or Electron/React for nicer UX. Windows components might use C#/.NET for tight OS integration.
- **Live ISO:** Ubuntu-based minimal live with systemd, GTK or lightweight Electron UI.
- **Disk utilities:** `hdparm`, `nvme-cli`, `sg3_utils`, `cryptsetup` (LUKS), `blkdiscard`, `dd`, `shred` (as fallback).
- **Certificates & signing:** `openssl`, or libs (ring/ed25519) for in-app signing.
- **PDF generation:** wkhtmltopdf or reportlab to compose PDF with QR code.
- **Blockchain anchoring (optional):** Ethereum L2 or a permissioned Indian ledger (choose low-cost L2 like Polygon or a simple OP stack) — anchor certificate hash via minimal tx.
- **Verification server:** Node.js/Flask simple API to verify signatures and resolve tx IDs.

---

## Test Plan & Metrics

- **Functional tests:** Secure erase success on supported HDD, SATA SSD, NVMe, eMMC; HPA/DCO removal; BitLocker/LUKS crypto-erase.
- **Performance metrics:** Time to wipe (per GB) for different methods; time to generate certificate.
- **Verification tests:** Signature verification, blockchain anchor verification, tampering attempts.
- **Usability:** 5 non-technical users perform the one-click flow; measure success and comprehension.

---

## Demo Script & Use Cases

1. Personal laptop (Windows with BitLocker) — show BitLocker crypto-erase and certificate.
2. Old NVMe SSD — show secure NVMe format and certificate.
3. Android phone (encrypted) — factory reset + keystore wipe demonstration.
4. Verifier scans QR from printed certificate and validates signature and on-chain anchor.

---

## Roadmap & Team Roles (6 members — leverage strengths)

- **Cybersecurity x4:** Wipe Core dev, platform agents, test & NIST mapping, QA.
- **Blockchain:** Anchor design, verification server, key rotation/management, cost analysis for anchoring.
- **Quantum person:** Research-proofing signatures (post-quantum readiness plan), investigate hybrid signing by 2026 PQC migration—produce recommendation annex.

Sprint suggestions (6–8 weeks):
- Week 1–2: Design, hardware lab setup, sample devices procurement.
- Week 3–4: Wipe Core prototype (Linux) + Live ISO build.
- Week 5: Windows agent basic flows + Android guidance.
- Week 6: Certificate generator, verification page, demo prep.
- Week 7: Testing, usability, final polish and documentation.

---

## Competitive Advantages & Winning Points

- Addresses the social problem (hoarding & e-waste) with practical UX.
- Strong technical approach to SSD/NVMe secure erase — addresses common weak tools.
- Tamper-evident, auditable certificates with blockchain anchoring add trust for recyclers and buyers.
- Offline-first design, suitable for low-connectivity and field use in India.
- Aligns with NIST SP 800-88 (international standard) and can be extended for Indian regulatory needs.

---

## Risks & Mitigations

- **Hardware diversity** — test across many devices; provide graceful fallbacks and clearly inform users when secure-erase is unsupported.
- **Key compromise** — use TPM/HSM for production; implement revocation list and allow re-signing.
- **Legal/privacy concerns** — minimize stored sensitive data; use salted hashes and user-consent flow.
- **Anchoring costs** — make anchoring optional; batch multiple certificate hashes into single tx to save costs.

---

## Annexes

- Detailed NIST SP 800-88 mapping table.
- Sample JSON certificate schema.
- Example PDF layout mockup text.
- List of commands & expected responses for ATA/NVMe/HPA handling.

---

### Next steps (technical tasks to start immediately)
1. Procure 6–8 test devices (HDD, SATA SSD, NVMe, eMMC phone, Windows laptop with BitLocker, Android phone locked/unlocked).
2. Build minimal Linux live ISO with `hdparm`, `nvme-cli`, `cryptsetup` and a simple GTK front-end.
3. Implement JSON certificate schema and local signing using a passphrase-protected private key.
4. Prepare demo script and verification web page.

---

### Uniqueness Beyond Certificates

This solution goes beyond traditional wiping tools, offering trust, usability, and future-proofing:

- Cross-Platform One-Click Tool

   - Unlike DBAN (Linux-only) or Windows-only tools, ours unifies Windows, Linux, and Android under one simple, one-click interface.

- Tamper-Evident Logs

   - We don’t just issue certificates. Every wipe operation is chained in a hash-linked log (like a mini-blockchain).

   - This makes alteration of wipe history mathematically detectable.

- Offline-First Design

   - Works fully offline via bootable USB/ISO.

   - Optional blockchain anchoring can be done later, ensuring usability even in low-connectivity areas — crucial for India’s recycling ecosystem.

- Hidden Areas Handling (HPA/DCO)

   - Most existing tools skip hidden sectors on HDDs.

   - Our solution detects and wipes HPA/DCO, covering overlooked attack surfaces.

- Adaptive Method Selection

   - Tool auto-detects best wipe method for each device:

      - ATA Secure Erase for HDDs

      - Crypto-erase for SSDs/BitLocker

      - Factory reset + key deletion for Android

   -  This eliminates guesswork for end users.

- Privacy-Preserving Proofs

   - Certificates & logs store only hashed identifiers, never raw personal data.

   - Users can prove erasure without exposing sensitive info.

- Post-Quantum Readiness

   - With our quantum teammate’s input, our signing system is designed to be upgradable to post-quantum algorithms.

   - Certificates remain valid even in a quantum-threat future.

- Usability for the General Public

   - Unlike technical, command-line tools, our UI is designed for non-technical users and recyclers — one click, clear progress, easy verification.