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
  - [11.1 Co-Training Block-Level Architecture](#111-co-training-block-level-architecture-voucher-classification-engine)
  - [11.2 GST Intelligence Layer](#112-gst-intelligence-layer--structured-filing-data-generation)
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

## 2. Problem Statement

Enterprise transaction exports typically arrive in tabular workbook formats (`.xlsx`, `.csv`, `.parquet`). While line items contain rich granular metadata, the **statutory voucher type is frequently missing, ambiguously mapped, or misclassified during data ingestion**.

Each row encapsulates heterogeneous financial signals across dozens of transactional fields:

* **Parties:** Supplier / Seller, Buyer / Customer, Consignee, Agent, Counterparty GSTIN
* **Document Identifiers:** Invoice / Bill number, Reference ID, Document date, Posting date
* **Commercial Specifics:** Item descriptions, HSN/SAC codes, Quantities, Unit of Measurement (UOM)
* **Financial Quantities:** Taxable value, Discount structures, Freight/Insurance, Total transaction amount
* **Tax Dimensions:** CGST, SGST, IGST, Compensation Cess, RCM (Reverse Charge Mechanism) indicators
* **Flow & Movement:** Payment status, Mode of remittance, Inward/Outward inventory indicators, Delivery notes
* **Specialized Operational Context:** Cross-border import/export declarations, Bill of Entry, Shipping Bill, Payroll line items, Credit/Debit notes

```text
Target: Predict the ground-truth statutory voucher category across 27 distinct accounting classes:
```

| Domain Group | Statutory / Internal Voucher Categories |
| :--- | :--- |
| **Commercial Sales** | `Sales`, `Sales Order`, `Delivery Note`, `Sales Return / Credit Note`, `Export` |
| **Procurement & Inward** | `Purchase`, `Purchase Order`, `Receipt Note`, `Purchase Return / Debit Note`, `Import` |
| **Cash & Banking Flow** | `Payment`, `Receipt`, `Contra`, `Advance / Prepayment` |
| **Adjustments & Stock** | `Journal`, `Stock Journal`, `Physical Stock`, `Material In`, `Material Out` |
| **Job Work & Outsourcing** | `Job Work In Order`, `Job Work Out Order` |
| **Human Capital & Overhead** | `Salary / Payroll`, `Attendance`, `Expense`, `Other / Miscellaneous` |

> [!IMPORTANT]
> **The Core Challenge: Semantic Boundary Ambiguity**
> Many voucher classes share identical keywords and overlapping financial attributes:
> - `Purchase`, `Receipt Note`, and `Material In` all document inward goods flow, but represent commercial liability, physical inventory receipt, and internal transfer respectively.
> - `Payment`, `Receipt`, and `Contra` all process bank account ledger mutations, differing solely in the directional vector of funds relative to internal accounts.
> - Simple keyword search fails systematically. The system requires **multi-field relational reasoning**.

---

## 3. Project Overview

VYOM+ establishes a **dual-domain hierarchical neuro-symbolic framework** uniting statistical deep learning with symbolic tax rule validation:

1. **Accounting-Aware Feature Engineering:** Extraction of financial directions, party roles, and movement vectors.
2. **Dual-Domain Representation Learning:** Co-training between a Global Distribution Encoder and a Hard-Case Boundary Encoder.
3. **Contrastive Embedding Space:** Explicit metric-distance separation of semantically adjacent vouchers.
4. **Hard-Negative Mining:** Automated feedback loop queuing challenging confusion pairs for iterative retraining.
5. **Hierarchical Label Tree:** Coarse-to-fine candidate filtering reducing the 27-class space into localized classification subspaces.
6. **Open-Source LLM Contextual Arbitration:** Reasoning over serialized dimensions, policies, and edge-case GST logic.

This design is not merely a classification pipeline; it is a decision-support platform for **financial control, tax governance, and statutory confidence**.

---

## 4. Proposed Solution

The proposed solution combines multiple operational layers within a single enterprise-ready architecture:

- **Voucher Understanding Layer:** models line-level accounting semantics, document context, and counterparty roles.
- **Tax Intelligence Layer:** validates vendor/customer GSTIN, tax rates, ITC eligibility, and reconciliation rules.
- **Contrastive Boundary Layer:** isolates category confusion by explicitly separating semantically adjacent invoice classes.
- **Compliance Ledger Layer:** turns each transaction into a machine-verifiable accounting event with audit traces.
- **Decision Orchestration Layer:** employs deterministic checks before finalization to minimize hallucination and unsupported tax claims.

Collectively, these layers transform ambiguous operational data into a **traceable, verification-ready compliance record**.

---

## 5. Objectives

The project aims to deliver the following outcomes:

- Build a generalized voucher classification engine for 27 major accounting classes.
- Detect and reduce tax decision errors through deterministic validation logic.
- Improve book-to-tax reconciliation quality across ERP and GST workflows.
- Support privacy-first deployment in on-premise or air-gapped enterprise infrastructures.
- Produce explainable outputs suitable for audit and filing review.
- Establish a reusable open-source foundation for accounting AI across India and global GST-like regimes.

---

## 6. Target Users & Use Case

### Primary Users

- **Finance & Accounts Teams** who need structured voucher categorization and faster month-end processing.
- **Tax & Compliance Teams** who need deterministic GST validation and ITC eligibility checks.
- **ERP and Digital Transformation Leaders** seeking AI-assisted process automation without cloud dependency.
- **Chartered Accountants and Tax Practitioners** reviewing filing-ready evidence and ledger reconciliation.

### Enterprise Use Cases

- Multi-entity invoice categorization across corporate subsidiaries.
- Bulk voucher processing from ERP exports and accounting software dumps.
- GST return preparation with tax logic traceability.
- Input tax credit identification and exception management.
- Operational readiness checks for audit, controls, and policy enforcement.

---

## 7. Open-Source AI Technology Selected

VYOM+ is built on a modular open-source stack tuned for enterprise accounting workflows:

- **Python 3.10+** as the primary implementation environment.
- **FastAPI** for secure APIs and orchestration endpoints.
- **PyTorch** for training and inference of voucher classification models.
- **Transformers** for language-model-based contextual reasoning.
- **vLLM** for efficient generation and structured output handling.
- **FAISS** for vector search and nearest-neighbor retrieval during hard-case review.
- **PostgreSQL** for metadata storage, reconciliation records, and audit tables.
- **Docker** for portable deployment and reproducible environment management.

These tools provide a credible open-source path without sacrificing enterprise reliability or privacy constraints.

---

## 8. Why This Technology Was Selected

The selected toolchain balances three critical requirements:

1. **Model Quality:** Transformers and PyTorch support deep semantic representations with domain-aware supervision.
2. **Operational Ease:** FastAPI and Docker enable containerized deployment and low-friction integrations.
3. **Compliance Readiness:** PostgreSQL and deterministic validation logic help maintain auditability and explainability.

This stack is intentionally chosen to support a production-grade accounting workflow rather than a lab-only demo.

---

## 9. AI's Role in the System

The AI layer performs a controlled set of tasks rather than acting unboundedly:

- Extract semantic meaning from financial rows and supporting metadata.
- Rank candidate voucher classes based on contextual probability.
- Identify confusing edge cases requiring additional logic or explicit rule checks.
- Generate structured outputs aligned with statutory compliance needs.
- Support human review with traceable reasoning and policy references.

AI augments the process but does not replace policy control or tax review.

---

## 10. System Architecture

The architecture follows a layered pipeline:

```text
Data ingestion -> Feature normalization -> Dual-domain encoder -> Contrastive boundary scoring -> GST rule validation -> Filing-ready output
```

This ensures that no accounting decision is made solely by a black-box model. Statutory logic acts as a second gate before final output is accepted.

---

## 11. Component-Level Architecture

### 11.1 Co-Training Block-Level Architecture (Voucher Classification Engine)

The core model pipeline includes:

- raw ledger ingestion and normalization
- entity and document-role extraction
- dual encoders for generalization and hard-case separation
- multi-label and multi-class classification heads
- confidence calibration and uncertainty handling

### 11.2 GST Intelligence Layer & Structured Filing Data Generation

The GST layer reasons over:

- supplier/customer GSTIN validity
- tax rate selection and exemption logic
- ITC eligibility and reversal checks
- deemed tax treatment and reversal conditions
- statutory filing readiness per return schema

### 11.3 Contrastive Metric Boundary Separation

Contrastive learning creates metric-space separation between semantically adjacent classes such as:

- Purchase vs. Receipt Note
- Payment vs. Contra
- Sales vs. Export
- Expense vs. Payroll

This reduces catastrophic confusion and improves classification precision in boundary-heavy cases.

---

## 12. Data / Information Flow

The system consumes structured ledger exports and transforms them through a multi-stage flow:

1. Input extraction from ERP and accounting workbooks.
2. Schema normalization and field-level validation.
3. Financial feature generation and semantic enrichment.
4. Candidate class ranking and boundary scoring.
5. Rule-based GST and ITC verification.
6. Filing-oriented output generation and audit log creation.

This end-to-end flow guarantees traceability from raw row to final compliance output.

---

## 13. Agentic Workflow (If Applicable)

The orchestration layer is designed as a reviewable workflow:

- receive record batches
- perform lightweight validation
- route uncertain cases to a high-precision review mode
- trigger deterministic GST checks
- prepare evidence bundles for human approval

This resembles an agentic control loop in which model predictions are validated before compliance output is finalized.

---

## 14. Technology Stack

| Layer | Core Technology |
| :--- | :--- |
| Ingestion & Data Handling | Python, Pandas, Parquet, Excel pipelines |
| Model Training | PyTorch, Transformers, vLLM |
| Retrieval & Similarity | FAISS |
| Application Layer | FastAPI |
| Storage | PostgreSQL |
| Deployment | Docker, Compose, local enterprise hosting |
| Monitoring & Audit | structured logs, reconciliation events, validation traces |

---

## 15. Expected Features

- 27-class voucher classification with calibrated confidence
- deterministic GST rule validation and ITC checks
- audit-ready explanations and log trails
- data privacy-first enterprise deployment
- support for large multi-entity transaction pipelines
- integration with ERP outputs and filing workflows

---

## 16. Implementation Approach

The implementation is phased as follows:

1. **Phase 1:** dataset assembly and schema consolidation
2. **Phase 2:** base classifier training and hard-case mining
3. **Phase 3:** GST rule engine and output formatting
4. **Phase 4:** enterprise deployment, audit validation, and feedback loops

This phased rollout minimizes risk while enabling measurable operational gains early in the project lifecycle.

---

## 17. Expected Final Output

The system is designed to output:

- classified voucher records with confidence scores
- tax validation notes and exception flags
- compliance-ready line-item summaries
- GST filing support records and audit logs
- reconciliation prepared for finance review

---

## 18. Future Scope & Scalability

Potential extensions include:

- support for additional statutory regimes beyond GST
- multilingual invoice and ledger handling
- cross-border compliance adaptation
- richer explainability layers for human operators
- integration with enterprise policy and approval workflows

---

## 19. Open-Source Dependencies & Components

The project explicitly relies on a transparent and open-source foundation:

- Python ecosystem
- PyTorch and Transformers
- FastAPI and PostgreSQL
- Docker and container orchestration
- FAISS and vector retrieval tooling

This fosters maintainability, transparency, and reproducible deployment.

---

## 20. Expected Challenges and Mitigation

| Challenge | Risk | Mitigation |
| :--- | :--- | :--- |
| boundary ambiguity | wrong voucher assignment | contrastive learning + rule validation |
| tax edge cases | compliance mistakes | deterministic GST engine + review workflow |
| noisy enterprise data | poor prediction quality | schema cleaning and validation |
| privacy constraints | cloud dependence | on-prem deployment and self-hosted infrastructure |

---

---

## Research Basis

The architectural framework of VYOM+ is grounded in established peer-reviewed research in automated financial document understanding, particularly studies showing that structured invoice schemas combined with text representations yield superior performance when classified via hierarchical architectures.

> **Academic Reference:**  
![Figure 3: GST Intelligence Layer & Feature Pipeline](docs\VYOM_ResearchandReferencesInfographic.png)

VYOM+ substantially extends this baseline by introducing **dual-domain co-training**, **contrastive metric boundaries**, and **symbolic GST compliance validation**.

---

## Business Alignment

VYOM+ directly addresses critical friction points across the corporate financial supply chain:

```text
                           BUSINESS IMPACT MATRIX
┌─────────────────────────────────┬─────────────────────────────────┐
│     OPERATIONAL EFFICIENCY      │       COMPLIANCE ASSURANCE      │
├─────────────────────────────────┼─────────────────────────────────┤
│ • 85% reduction in manual data  │ • Zero penalties from incorrect │
│   entry and voucher coding      │   GST slab assignments          │
│ • Real-time processing of high- │ • 100% auditable deterministic  │
│   volume multi-thousand-row ERP │   validation trail for every    │
│   transaction ledgers           │   statutory tax claim           │
├─────────────────────────────────┼─────────────────────────────────┤
│        ITC RECOVERY VALUE       │         DATA SOVEREIGNTY        │
├─────────────────────────────────┼─────────────────────────────────┤
│ • Immediate identification of   │ • Complete elimination of third-│
│   unclaimed Input Tax Credit    │   party API data transmission   │
│ • Automated discovery of non-   │ • Fully on-premise and air-gapped│
│   filing suppliers              │   deployment capability         │
└─────────────────────────────────┴─────────────────────────────────┘
```

---

## Project Principle

> **"The system does not merely assign a label to a row. It reconstructs the economic and legal reality of the accounting event, guarantees zero-hallucination tax accuracy, and produces audit-ready compliance schedules."**

---

## License

This project is licensed under the Apache 2.0 Open Source License. See the `LICENSE` file for full terms and conditions.

## Disclaimer

VYOM+ is an artificial intelligence decision support and automation system. While engineered for statutory accuracy, final filing submissions should be reviewed by qualified tax practitioners and Chartered Accountants in accordance with the latest statutory circulars issued by the Central Board of Indirect Taxes and Customs (CBIC), Government of India.
