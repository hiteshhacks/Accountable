[![Python 3.10+](https://img.shields.io/badge/PYTHON-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FASTAPI-0.110+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PyTorch](https://img.shields.io/badge/PYTORCH-2.2+-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)](https://pytorch.org/)
[![Hugging Face](https://img.shields.io/badge/HUGGING%20FACE-TRANSFORMERS-FFD21E?style=for-the-badge&logo=huggingface&logoColor=black)](https://huggingface.co/)
[![vLLM](https://img.shields.io/badge/INFERENCE-vLLM-4F46E5?style=for-the-badge&logo=accelerate&logoColor=white)](https://vllm.ai/)
[![FAISS](https://img.shields.io/badge/FAISS-VECTOR%20SEARCH-0284C7?style=for-the-badge&logo=meta&logoColor=white)](https://github.com/facebookresearch/faiss)
[![PostgreSQL](https://img.shields.io/badge/POSTGRESQL-16+-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/DOCKER-READY-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)

# 📑 VYOM+ — Intelligent Voucher Classification & GST Intelligence Platform

**An end-to-end neuro-symbolic AI system for structured financial transaction understanding, 27-class voucher classification, deterministic GST validation, book-to-tax reconciliation, and filing preparation — powered by open-source LLMs, dual-domain contrastive co-training, and automated compliance intelligence.**

---

| 🎯 Core Capability | 🧠 AI Architecture | 🏛️ Model Layer | 📊 Compliance Engine | 🔒 Privacy & Deployment |
| :--- | :--- | :--- | :--- | :--- |
| **27-Class Voucher Inference** | Dual-Domain Co-Training + Contrastive Learning | Open-Source LLMs (Qwen / LLaMA / Mistral) | Deterministic GST & ITC Engine | 100% Self-Hosted & Local |

---

## Table of Contents

- [1. Project Name & Overview](#1-project-name)
- [2. Problem Statement](#2-problem-statement)
- [3. Project Overview](#3-project-overview)
- [4. Proposed Solution](#4-proposed-solution)
- [5. Objectives](#5-objectives)
- [6. Target Users & Enterprise Use Cases](#6-target-users--use-case)
- [7. Open-Source AI Technology Selected](#7-open-source-ai-technology-selected)
- [8. Technology Selection Justification](#8-why-this-technology-was-selected)
- [9. Multi-Tier AI Architecture & Roles](#9-ais-role-in-the-system)
- [10. System Architecture & End-to-End Pipeline](#10-system-architecture)
- [11. Component-Level Architecture](#11-component-level-architecture)
  - [11.1 Co-Training Block-Level Architecture (Voucher Classification Engine)](#111-co-training-block-level-architecture-voucher-classification-engine)
  - [11.2 GST Intelligence Layer & Structured Filing Data Generation](#112-gst-intelligence-layer--structured-filing-data-generation)
  - [11.3 Contrastive Metric Boundary Separation](#113-contrastive-metric-boundary-separation)
- [12. End-to-End Data & Information Flow](#12-data--information-flow)
- [13. Controlled Orchestration & Verification Workflow](#13-agentic-workflow-if-applicable)
- [14. Production Technology Stack](#14-technology-stack)
- [15. System Capabilities & Feature Matrix](#15-expected-features)
- [16. Implementation Roadmap & Phased Execution](#16-implementation-approach)
- [17. Expected Output Specifications & Reports](#17-expected-final-output)
- [18. Future Scope & System Scalability](#18-future-scope--scalability)
- [19. Open-Source Dependencies & Software Bill of Materials](#19-open-source-dependencies--components)
- [20. Risk Matrix & Engineering Mitigations](#20-expected-challenges-and-mitigation)
- [Research Basis & Academic Citations](#research-basis)
- [Business Alignment & Enterprise Value](#business-alignment)
- [Core Engineering Principles](#project-principle)
- [License & Legal Disclaimer](#license)

---

## 1. Project Name

### **VYOM+ — Intelligent Voucher Classification & GST Intelligence Platform Using Open-Source LLMs**

**VYOM+** is an enterprise-grade accounting intelligence system designed to ingest **already-structured transactional records** (such as general ledgers, daybooks, and raw ERP tables) and transform them into standardized statutory accounting events, calibrated voucher classifications, and GST filing-ready schedules.

Traditional accounting automation relies heavily on rigid regex heuristics or isolated keyword search, both of which collapse under complex multi-field contexts. **VYOM+** addresses this vulnerability by treating voucher identification as a **multi-field semantic transaction reasoning problem**. It bridges the gap between raw transaction data and statutory tax compliance by pairing representation learning with deterministic GST validation rules.

---

