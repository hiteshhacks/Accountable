# VYOM+ Security Threat Model

**Document:** `VYOM_Security_Threat_Model.md`\
**Project:** VYOM+ --- Intelligent Voucher Classification & GST
Intelligence Platform\
**Document type:** Security research and design specification\
**Version:** 1.0\
**Date:** 9 October 2026\
**Status:** Initial threat model --- based on the supplied README;
implementation not yet inspected

------------------------------------------------------------------------

## 1. Executive Summary

VYOM+ is described as a self-hosted AI-assisted accounting and GST
intelligence platform. Its documented workflow ingests structured
transaction records, normalizes fields, classifies transactions across
27 voucher categories using dual-domain encoders and open-weight LLM
arbitration, applies deterministic GST checks, reconciles records
against GST datasets, and produces structured reports and
filing-oriented artifacts.

The security layer must protect financial confidentiality, transaction
integrity, authorized use, service availability, and auditability across
this workflow. Priority concerns include unauthorized access to
financial records, broken object- and function-level authorization,
tenant boundary failures if multiple organizations share an instance,
malicious spreadsheet inputs, misuse of LLM processing, untrusted model
outputs, training-data poisoning, resource exhaustion, and unauthorized
alteration or concealment of audit evidence.

**Evidence limitation:** this document is grounded in the supplied
README, not source code, running services, database schemas,
infrastructure configuration, or penetration-test results. It identifies
plausible threats and proposes controls; it does not assert that any
listed vulnerability exists. All security properties must be verified
during implementation and testing.

### Security objectives

1.  **Confidentiality:** prevent unauthorized disclosure of ledgers,
    GSTINs, invoice details, financial values, reconciliation data,
    credentials, and reports.
2.  **Integrity:** prevent unauthorized changes to transactions,
    classifications, tax calculations, reconciliation outcomes, training
    datasets, models, and audit records.
3.  **Availability:** protect API, database, queue, and inference
    resources against accidental overload and malicious exhaustion.
4.  **Authenticity and accountability:** identify users and services,
    enforce permissions, and record significant security-relevant
    actions.
5.  **Least privilege:** give users, application components, database
    roles, and models only the access required for their task.
6.  **Verifiability:** make security requirements testable and preserve
    evidence of test outcomes.
7.  **Privacy by design:** minimize sensitive data exposure in logs,
    prompts, caches, exports, and development environments.

------------------------------------------------------------------------

## 2. Scope and Evidence Classification

### 2.1 In scope

-   Structured `.xlsx`, `.csv`, and `.parquet` transaction ingestion, as
    described by the README.
-   FastAPI application and API endpoints.
-   Input normalization and feature engineering.
-   Dual-domain encoders, contrastive learning, hard-negative queue,
    pseudo-labeling, and retraining workflow.
-   Local open-weight LLM inference through vLLM.
-   Deterministic GST validation and filing-oriented output generation.
-   Book-to-GST reconciliation and discrepancy reporting.
-   PostgreSQL, Redis, FAISS, model artifacts, generated reports, Docker
    deployment, secrets, logs, and dependencies where applicable.
-   Security tests and integration requirements for a future
    implementation.

### 2.2 Out of scope or not established

-   OCR and scanned-document processing: the README explicitly says OCR
    is decoupled from the current architecture.
-   Direct GST portal submission: the README discusses filing-ready
    artifacts and describes direct sandbox adapters as future scope.
-   Actual frontend implementation, identity provider, user
    provisioning, tenant model, network topology, cloud or on-premises
    environment, backup architecture, and production deployment details:
    not supplied.
-   Confirmation of regulatory compliance or certification: no audit
    evidence is provided.
-   Confirmation that the stated model benchmarks or privacy claims have
    been achieved: these are documented targets or design claims, not
    independently verified measurements.

### 2.3 Evidence labels

  -----------------------------------------------------------------------
  Label                               Meaning
  ----------------------------------- -----------------------------------
  **Documented (D)**                  Explicitly stated in the supplied
                                      VYOM+ README.

  **Inferred (I)**                    Plausible risk derived from the
                                      documented design; requires
                                      validation.

  **Proposed (P)**                    Recommended security control or
                                      design requirement.

  **Unverified (U)**                  Cannot be confirmed without source
                                      code, configuration, or test
                                      evidence.
  -----------------------------------------------------------------------

Use these labels when discussing the architecture so that assumptions
are not presented as implementation facts.

------------------------------------------------------------------------

## 3. System Overview and Trust Boundaries

### 3.1 Documented architecture

The README documents the following general pipeline:

1.  Ingest structured spreadsheets and tabular transaction records.
2.  Normalize columns, dates, numeric values, and GSTIN formats.
3.  Engineer accounting features, party roles, cash-flow indicators, tax
    vectors, and temporal signals.
4.  Generate global and boundary embeddings through dual-domain
    encoders.
5.  Evaluate confidence and use LLM arbitration for uncertain
    classifications.
6.  Validate tax computations and statutory rules with a deterministic
    GST engine.
7.  Reconcile internal records against external or imported GST
    datasets.
8.  Generate JSON, Excel, and filing-oriented reports.

The documented technology stack includes Python, FastAPI, Pydantic,
PyTorch, Hugging Face Transformers, vLLM, FAISS, PostgreSQL, Redis,
SQLAlchemy, and Docker. The README states an intention to use
self-hosted, open-weight models and avoid cloud API dependencies.

### 3.2 Proposed trust-boundary view

``` text
[User / Client / Integration]
            |
            v
[API Entry Point: authentication, authorization, quotas]
            |
            v
[Upload and Schema Validation]
            |
            v
[Normalization and Feature Engineering]
            |
            v
[Encoders / FAISS / LLM Inference]
            |
            v
[Validated Classification Output]
            |
            v
[Deterministic GST Rules and Reconciliation]
            |
            v
[Protected Database and Report Export]
            |
            v
[Authorized Consumer]

Cross-cutting controls:
- Identity and permission enforcement
- Tenant and record-level isolation, if multi-tenant
- Secrets and cryptographic key management
- Audit events and security monitoring
- Resource limits and queue controls
- Dependency, image, model, and dataset integrity
```

This is a proposed logical security view, not a verified deployment
diagram. The exact trust boundaries must be revised after inspecting the
real application and deployment.

### 3.3 Trust boundaries to validate

-   **TB-1: Client to API.** All incoming requests, tokens, identifiers,
    files, and fields are untrusted.
-   **TB-2: API to storage.** Queries and mutations must enforce
    permissions and organization scope.
-   **TB-3: Application to AI components.** Transaction text is
    untrusted data; model output is not an authorization decision or a
    trusted command.
-   **TB-4: Inference to training workflow.** Inference samples must not
    automatically become trusted training data without safeguards.
-   **TB-5: Internal system to imported reconciliation data.** Imported
    datasets may be malformed, stale, inconsistent, or malicious.
-   **TB-6: Application to export.** Reports may contain sensitive
    information and require authorization and safe file handling.
-   **TB-7: Runtime to dependencies and artifacts.** Packages,
    containers, model weights, configuration, and datasets require
    provenance and integrity controls.

------------------------------------------------------------------------

## 4. Assets, Security Properties, and Potential Impact

  -----------------------------------------------------------------------
  Asset                   Security property       Potential impact if
                                                  compromised
  ----------------------- ----------------------- -----------------------
  Transaction ledgers and Confidentiality,        Exposure or alteration
  spreadsheet uploads     integrity               of commercial and
                                                  financial records

  GSTINs, party names,    Confidentiality,        Privacy loss, fraud,
  invoice numbers and     integrity               incorrect
  dates                                           reconciliation

  Voucher predictions and Integrity, authenticity Incorrect accounting
  confidence scores                               categorization or
                                                  misleading downstream
                                                  decisions

  GST calculations and    Integrity, traceability Incorrect tax reporting
  eligibility flags                               or ITC decisions

  Reconciliation data and Confidentiality,        Concealed discrepancies
  exception reports       integrity               or disclosure of
                                                  financial positions

  Generated JSON, Excel,  Confidentiality,        Unauthorized disclosure
  and filing artifacts    integrity               or use of tampered
                                                  reports

  User identities,        Confidentiality,        Account takeover and
  password hashes,        integrity               privilege escalation
  tokens, signing keys                            

  PostgreSQL data and     Confidentiality,        Broad data compromise
  credentials             integrity, availability or service disruption

  Redis jobs, queues, and Integrity,              Job tampering,
  cache entries           availability,           overload, or cross-user
                          confidentiality where   data leakage
                          data is cached          

  FAISS indexes and       Confidentiality,        Sensitive similarity
  embeddings              integrity               leakage, corrupted
                                                  retrieval, or degraded
                                                  classification

  Hard-negative queue,    Integrity, provenance   Training-data poisoning
  pseudo-labels, datasets                         and model quality
  and model artifacts                             degradation

  Audit logs              Integrity,              Inability to
                          availability,           investigate actions or
                          confidentiality         prove what occurred

  Application secrets and Confidentiality,        Token forgery, data
  encryption keys         integrity               exposure, or compromise
                                                  of protected services

  Container images and    Integrity               Introduction of
  dependencies                                    vulnerable or malicious
                                                  code
  -----------------------------------------------------------------------

The impact statements are risk analysis, not evidence of an observed
incident.

------------------------------------------------------------------------

## 5. Threat Actors and Assumptions

### 5.1 Threat actors

-   **External unauthenticated attacker:** probes exposed endpoints,
    uploads malicious files, or attempts resource exhaustion.
-   **Authenticated low-privilege user:** attempts to access other
    users' records or perform unauthorized actions.
-   **Malicious or compromised tenant user:** attempts
    cross-organization access if the deployment supports multiple
    organizations.
-   **Compromised application credential or service:** accesses data or
    operations beyond its intended scope.
-   **Malicious data provider:** supplies crafted transaction text,
    malformed tabular data, or poisoned training examples.
-   **Insider or compromised administrator:** misuses privileged access
    or alters data and logs.
-   **Supply-chain attacker:** compromises a dependency, container
    image, model artifact, or dataset.
-   **Accidental operator error:** misconfigures secrets, permissions,
    network exposure, retention, or deployment settings.

### 5.2 Working assumptions

1.  The intended backend uses Python and FastAPI, with Pydantic
    validation.
2.  PostgreSQL, Redis, FAISS, vLLM, and Docker are part of the proposed
    stack, but their actual configuration is unknown.
3.  Input records and imported reconciliation datasets may be untrusted.
4.  Financial and tax data are sensitive and should be
    access-restricted.
5.  Local inference reduces reliance on external model APIs but does
    not, by itself, secure the host, internal network, logs, or model
    endpoint.
6.  If multiple organizations use one deployment, strict tenant
    isolation is required. If deployment is single-tenant,
    organization-level controls may instead be implemented as user and
    record-level authorization.
7.  The LLM should not be granted direct authority to execute database
    mutations, submit filings, or override deterministic tax checks.
8.  No source code, live deployment, database schema, user-role
    definitions, or test evidence has been provided.

These assumptions must be confirmed with the project owner before
production design decisions are finalized.

------------------------------------------------------------------------

## 6. Threat Prioritization Method

Use a qualitative scale until likelihood and exposure can be assessed
against a real deployment.

-   **Critical:** could expose or alter large volumes of sensitive
    financial data, enable privileged compromise, or undermine
    consequential tax outputs.
-   **High:** could compromise sensitive records, tenant boundaries,
    model/data integrity, or service availability.
-   **Medium:** has bounded impact or requires additional preconditions.
-   **Low:** limited impact with effective compensating controls.

Initial priorities below are **provisional design priorities**, not
measured risk scores. Reassess after identifying public exposure, user
roles, data volume, deployment topology, and existing controls.

------------------------------------------------------------------------

## 7. Prioritized Threat Register

### T-01 --- Broken object-level authorization / cross-tenant data access

-   **Priority:** Critical (provisional)
-   **Evidence:** Inferred from the financial data and API-oriented
    architecture; tenant model and authorization code are unverified.
-   **Scenario:** An authenticated user changes an invoice, transaction,
    report, or job identifier in a request and retrieves or modifies a
    record belonging to another user or organization.
-   **Impact:** Confidentiality breach, financial-data manipulation,
    unauthorized exports.
-   **Proposed controls:**
    -   Establish a canonical authorization check for every record
        access and mutation.
    -   Derive user and tenant identity from the authenticated
        principal, not from client-supplied tenant fields.
    -   Scope database queries by the authorized organization or owner.
    -   Enforce ownership on list, detail, update, delete, download, and
        asynchronous job-status endpoints.
    -   Consider PostgreSQL row-level security as defense in depth where
        appropriate; do not treat it as a substitute for correct
        application authorization.
-   **Acceptance criteria:**
    -   Tests create records for organizations A and B.
    -   A token for A cannot read, update, delete, export, or infer
        protected details about B's records.
    -   Changing an object ID never bypasses authorization.
    -   Negative tests cover direct object lookup, list filters, report
        downloads, and background-job results.

### T-02 --- Broken authentication and token misuse

-   **Priority:** Critical (provisional)
-   **Evidence:** Inferred; the README does not document an identity
    provider or authentication implementation.
-   **Scenario:** Weak password storage, token forgery, token reuse
    after expiry, leaked signing secrets, or brute-force login attempts
    enable account takeover.
-   **Impact:** Unauthorized access and potential privilege escalation.
-   **Proposed controls:**
    -   Use a maintained authentication implementation with a reviewed
        password-hashing scheme such as Argon2.
    -   Validate token signature, algorithm, expiry, issuer, audience,
        and relevant claims.
    -   Use short-lived access tokens and a documented
        revocation/refresh strategy where needed.
    -   Store secrets outside source control and rotate them under a
        defined procedure.
    -   Rate-limit authentication attempts and return generic failure
        messages.
    -   Require stronger authentication for privileged roles where the
        product's identity model supports it.
-   **Acceptance criteria:**
    -   Missing, malformed, expired, tampered, wrongly issued, or
        wrongly addressed tokens are rejected.
    -   Passwords are never stored in plaintext.
    -   Repeated failed logins trigger the configured throttling or
        protective control.
    -   Production configuration fails closed when required secrets are
        absent.

### T-03 --- Broken function-level authorization / privilege escalation

-   **Priority:** Critical (provisional)
-   **Evidence:** Inferred; no user-role implementation is supplied.
-   **Scenario:** A read-only user invokes an administrative endpoint,
    changes role fields in a request, modifies a GST result, or accesses
    training and model-management operations.
-   **Impact:** Unauthorized changes to financial records, compliance
    results, or system configuration.
-   **Proposed controls:**
    -   Define roles and action-level permissions centrally.
    -   Enforce authorization on the server for every privileged
        operation.
    -   Never trust client-provided role, permission, owner, or approval
        fields.
    -   Separate inference permissions from dataset approval,
        retraining, model deployment, and administration.
    -   Require explicit human approval for high-impact business
        actions.
-   **Acceptance criteria:**
    -   A permission matrix is implemented and tested for every
        protected endpoint.
    -   Users cannot elevate their own role by changing request
        payloads.
    -   Administrative and training endpoints reject unauthorized roles.
    -   Permission-denial events are recorded without exposing secrets.

### T-04 --- Sensitive financial data exposure

-   **Priority:** Critical (provisional)
-   **Evidence:** Documented sensitive data classes include GSTINs,
    party identifiers, invoice numbers, values, tax amounts,
    reconciliation information, and generated reports. Existing
    protections are unverified.
-   **Scenario:** Sensitive fields appear in logs, error traces, caches,
    prompts, exports, development data, or backups accessible to
    unauthorized parties.
-   **Impact:** Confidentiality loss, fraud, reputational damage, and
    possible legal or contractual consequences.
-   **Proposed controls:**
    -   Classify data and minimize collection, logging, retention, and
        output fields.
    -   Use TLS for network traffic and appropriate encryption at rest
        for databases, storage, and backups.
    -   Restrict access to logs, caches, backups, and exports.
    -   Redact secrets and unnecessary personal/financial fields from
        logs.
    -   Avoid sending transaction data to external services unless
        explicitly approved and assessed.
    -   Apply download permissions, retention rules, and secure
        temporary-file handling.
-   **Acceptance criteria:**
    -   Logs and exception traces contain no passwords, bearer tokens,
        signing keys, or unnecessary full ledger rows.
    -   Unauthorized users cannot download protected reports.
    -   Storage, transport, backup, and retention controls are
        documented and tested in the target deployment.
    -   No unapproved external API receives financial records.

### T-05 --- Malicious or malformed spreadsheet input

-   **Priority:** High
-   **Evidence:** Documented `.xlsx`, `.csv`, and `.parquet` ingestion;
    exact parser and upload implementation unverified.
-   **Scenario:** An attacker submits oversized, malformed, deceptive,
    or resource-intensive files to trigger parser failures, memory
    exhaustion, unexpected values, or unsafe export behavior.
-   **Impact:** Service disruption, corrupted transaction data,
    downstream classification errors.
-   **Proposed controls:**
    -   Allowlist expected file formats and verify file structure rather
        than trusting filenames or MIME types alone.
    -   Enforce maximum file size, row count, column count, cell length,
        processing time, and decompression limits where relevant.
    -   Parse in a constrained worker process with bounded resources.
    -   Validate canonical schemas and numeric/date ranges; reject or
        quarantine invalid rows with safe error messages.
    -   Treat all cell content as untrusted.
    -   Neutralize formula-leading content when exporting untrusted text
        to spreadsheet formats.
-   **Acceptance criteria:**
    -   Oversized and malformed files are rejected before unbounded
        processing.
    -   Invalid schemas and extreme numeric/date values fail safely.
    -   Resource limits are exercised by automated tests.
    -   Export tests demonstrate that untrusted values cannot become
        executable spreadsheet formulas.

### T-06 --- Prompt injection through transaction fields

-   **Priority:** High
-   **Evidence:** Documented LLM arbitration of serialized transaction
    data; exact prompt templates, model permissions, and context
    boundaries are unverified.
-   **Scenario:** A transaction description, party field, imported note,
    or retrieved example contains instructions designed to override the
    intended classification task or elicit protected information.
-   **Impact:** Misclassification, disclosure of contextual data, or
    unsafe downstream behavior if the model is connected to privileged
    tools.
-   **Proposed controls:**
    -   Delimit and label transaction values as untrusted data, separate
        from system instructions.
    -   Keep the model's task narrow and avoid granting direct database,
        filesystem, shell, or filing capabilities.
    -   Do not use model-generated text as authorization policy.
    -   Validate all model output against a strict schema and allowed
        voucher categories.
    -   Apply deterministic GST validation independently of model
        reasoning.
    -   Test adversarial transaction fields and monitor unexpected
        output patterns.
-   **Acceptance criteria:**
    -   A prompt-injection test suite cannot make the model access
        another tenant's data or invoke unauthorized operations.
    -   Unexpected output formats and invalid voucher labels are
        rejected or quarantined.
    -   Tax calculations and authorization checks remain enforced
        regardless of model output.
    -   Residual model error is measured and documented; zero
        prompt-injection risk is not claimed.

### T-07 --- Unsafe LLM output handling

-   **Priority:** High
-   **Evidence:** Documented structured JSON output and downstream
    GST/reporting pipeline; runtime enforcement details are unverified.
-   **Scenario:** Model output contains invalid fields, unexpected
    labels, malicious strings, excessive output, or values that
    downstream code treats as trusted instructions.
-   **Impact:** Incorrect records, report corruption, unsafe rendering,
    or injection into downstream components.
-   **Proposed controls:**
    -   Parse outputs into strict Pydantic models with explicit types,
        bounds, enums, and required fields.
    -   Reject unknown or invalid values where the schema requires it.
    -   Treat model-generated text as untrusted when rendering HTML or
        exporting reports.
    -   Recompute all monetary arithmetic in deterministic code.
    -   Separate model suggestions from approved financial or compliance
        state.
-   **Acceptance criteria:**
    -   Invalid JSON, unknown voucher categories, out-of-range
        confidence values, and malformed monetary values do not enter
        trusted storage.
    -   Tax values are recalculated or verified by deterministic rules.
    -   Model output cannot directly trigger privileged mutations.
    -   Failure paths are logged without storing unnecessary sensitive
        output.

### T-08 --- Resource exhaustion and inference denial of service

-   **Priority:** High
-   **Evidence:** Documented high-throughput FastAPI, vLLM inference,
    spreadsheet processing, Redis queue, and vector search components;
    operational limits are unverified.
-   **Scenario:** Large uploads, repeated ambiguous records, large
    prompts, excessive concurrent inference, or queue flooding consume
    CPU, memory, GPU VRAM, database connections, or disk space.
-   **Impact:** Service degradation, outages, delayed processing, and
    resource-cost escalation.
-   **Proposed controls:**
    -   Enforce request and upload quotas, row limits, request timeouts,
        concurrency caps, and bounded queues.
    -   Apply per-user or per-tenant limits where identity is available.
    -   Limit prompt length, generated tokens, batch size, and inference
        duration.
    -   Monitor queue depth, resource utilization, failures, and
        latency.
    -   Define backpressure and safe rejection behavior.
-   **Acceptance criteria:**
    -   Requests beyond configured limits are rejected or deferred
        predictably.
    -   A load test confirms bounded queue and concurrency behavior.
    -   One user cannot consume all inference capacity under the defined
        test conditions.
    -   The service recovers cleanly after overload tests.

### T-09 --- Training-data poisoning and hard-negative queue manipulation

-   **Priority:** High
-   **Evidence:** Documented hard-negative queue, pseudo-labeling, and
    iterative retraining; data provenance and approval controls are
    unverified.
-   **Scenario:** Incorrect or adversarial examples enter the training
    queue, agreement-based pseudo-labeling amplifies errors, or a
    malicious actor alters datasets or model artifacts.
-   **Impact:** Reduced classification accuracy, biased predictions,
    systematic voucher confusion, and loss of model integrity.
-   **Proposed controls:**
    -   Separate prediction-time permissions from training-data approval
        and retraining permissions.
    -   Record dataset provenance, label source, timestamps, review
        status, and version.
    -   Require review or quality gates for suspicious and high-impact
        training samples.
    -   Track model versions and training data versions; retain rollback
        capability.
    -   Evaluate models against fixed validation sets and adversarial
        cases before deployment.
    -   Do not treat agreement between two models as proof that a
        pseudo-label is correct.
-   **Acceptance criteria:**
    -   Every promoted training sample has traceable provenance.
    -   Unreviewed or unauthorized samples cannot silently enter the
        approved training set.
    -   Model deployment requires a documented evaluation result and
        authorized approval.
    -   A prior model version can be restored under the rollback
        procedure.

### T-10 --- Unauthorized modification or concealment of audit evidence

-   **Priority:** High
-   **Evidence:** PostgreSQL is documented for audit logs and
    reconciliation storage; log schema, retention, immutability, and
    access model are unverified.
-   **Scenario:** A privileged or compromised account alters or deletes
    records to conceal data access, classification changes, or exports.
-   **Impact:** Loss of accountability and inability to reconstruct
    consequential actions.
-   **Proposed controls:**
    -   Define an audit event schema with actor, action, target
        identifier, timestamp, outcome, and correlation ID.
    -   Record authentication failures, access denials, privileged
        changes, exports, dataset approvals, and model deployments.
    -   Restrict log access and deletion permissions; separate audit
        administration from ordinary application roles.
    -   Forward critical logs to a separately controlled destination
        when available.
    -   Consider tamper-evident chaining or write-once storage based on
        threat model and operational needs.
    -   Avoid logging tokens, passwords, or complete financial payloads.
-   **Acceptance criteria:**
    -   Required events are emitted for both successful and denied
        privileged actions.
    -   Ordinary application roles cannot modify or delete retained
        audit records.
    -   Tests verify sensitive fields are redacted.
    -   Retention, access, monitoring, and recovery procedures are
        documented.

### T-11 --- PostgreSQL, Redis, FAISS, or internal service exposure

-   **Priority:** High
-   **Evidence:** These technologies are documented in the proposed
    stack; network and service configurations are unverified.
-   **Scenario:** A database, cache, vector index, or inference service
    is exposed to an untrusted network or accessible with excessive
    privileges.
-   **Impact:** Data disclosure, job tampering, unauthorized retrieval,
    or service compromise.
-   **Proposed controls:**
    -   Bind internal services to private interfaces and restrict
        network access.
    -   Require strong authentication and access controls for
        PostgreSQL, Redis, and model-serving endpoints.
    -   Use separate service identities and least-privilege database
        roles.
    -   Restrict administrative ports and disable unnecessary services.
    -   Do not assume that a service is safe merely because it is
        self-hosted or containerized.
-   **Acceptance criteria:**
    -   Network scans from an untrusted segment cannot reach internal
        services.
    -   Unauthorized service credentials fail.
    -   Application database roles cannot perform unnecessary
        administrative operations.
    -   Deployment configuration and service exposure are reviewed
        before release.

### T-12 --- Secrets, cryptographic key, and configuration exposure

-   **Priority:** High
-   **Evidence:** No actual secret-management configuration is provided.
-   **Scenario:** Signing keys, database passwords, API credentials, or
    encryption keys are committed to version control, included in
    images, exposed in logs, or reused across environments.
-   **Impact:** Token forgery, database compromise, data disclosure, or
    persistent access.
-   **Proposed controls:**
    -   Use a secret manager or protected runtime configuration.
    -   Keep `.env` files out of version control and provide only
        placeholder values in `.env.example`.
    -   Generate cryptographically strong secrets and rotate compromised
        keys.
    -   Use separate development, test, and production secrets.
    -   Restrict who can read secrets and avoid embedding them in
        container images.
-   **Acceptance criteria:**
    -   Secret scanning finds no live credentials in tracked files.
    -   Production startup fails safely when mandatory secrets are
        missing or invalid.
    -   Secret rotation and incident response procedures are documented.
    -   Test and production credentials are demonstrably separate.

### T-13 --- Dependency, container, model, and artifact supply-chain compromise

-   **Priority:** High
-   **Evidence:** The README lists many third-party packages, Docker,
    and downloaded open-weight model families; pinning, scanning,
    signatures, and provenance are unverified.
-   **Scenario:** A vulnerable or compromised dependency, base image,
    model checkpoint, tokenizer, or dataset is introduced into the
    deployment or training process.
-   **Impact:** Code execution, data compromise, model manipulation, or
    service outage.
-   **Proposed controls:**
    -   Pin dependencies and maintain a software bill of materials
        (SBOM).
    -   Scan dependencies and container images for known
        vulnerabilities.
    -   Use trusted sources and verify artifact checksums or signatures
        when available.
    -   Review model licenses, provenance, loading behavior, and
        serialization formats.
    -   Avoid unsafe deserialization of untrusted model or data
        artifacts.
    -   Run containers as non-root where practical, drop unnecessary
        capabilities, and restrict writable filesystems.
-   **Acceptance criteria:**
    -   Build outputs include dependency and image versions.
    -   The release process produces a vulnerability scan report and
        SBOM.
    -   Model artifacts have documented source and integrity checks.
    -   Container configuration passes the project's defined hardening
        checks.

### T-14 --- Incorrect reconciliation, duplicate matching, or financial-state tampering

-   **Priority:** High
-   **Evidence:** The README documents composite-key matching, duplicate
    detection, GST arithmetic checks, ITC indicators, and
    filing-oriented reports. The exact matching and approval logic is
    unverified.
-   **Scenario:** Crafted or inconsistent records cause a false match, a
    duplicate is overlooked, or an unauthorized user alters a
    reconciliation status or eligibility flag.
-   **Impact:** Incorrect compliance decisions, misleading reports, or
    inaccurate financial summaries.
-   **Proposed controls:**
    -   Treat model classification and reconciliation suggestions as
        inputs to controlled validation, not authorization.
    -   Validate data types, currency precision, dates, identifiers, and
        matching criteria.
    -   Preserve original imported values and record normalization
        decisions.
    -   Use deterministic, versioned rules for calculations and
        reconciliation.
    -   Require authorized review for exceptions and consequential
        filing decisions.
    -   Maintain a traceable relationship between source records and
        generated outputs.
-   **Acceptance criteria:**
    -   Tests cover duplicate invoices, conflicting dates, mismatched
        GSTINs, rounding boundaries, and missing fields.
    -   Changes to reconciliation state are attributable to an
        authorized actor or documented system process.
    -   The system can explain which source records and rule versions
        produced a result.
    -   No model confidence score alone can authorize a tax or filing
        action.

### T-15 --- Spreadsheet formula injection in exported reports

-   **Priority:** Medium
-   **Evidence:** Excel report generation is documented; the exact
    writer and escaping behavior are not verified.
-   **Scenario:** Untrusted transaction text is written into spreadsheet
    cells and interpreted as a formula by spreadsheet software.
-   **Impact:** When a recipient opens a report, the spreadsheet may
    execute unintended formulas or external references.
-   **Proposed controls:**
    -   Neutralize formula-leading content in untrusted text fields
        before spreadsheet export.
    -   Use a well-maintained spreadsheet library and verify its
        behavior.
    -   Keep numeric values typed as numeric data and text values typed
        as text where possible.
    -   Include export-specific adversarial test cases.
-   **Acceptance criteria:**
    -   Inputs beginning with formula-significant characters are safely
        represented as text.
    -   Generated workbooks pass export security tests in the chosen
        library and target spreadsheet software.

### T-16 --- Unsafe error handling and information leakage

-   **Priority:** Medium
-   **Evidence:** FastAPI and Pydantic are documented; error handlers
    and logging policy are not supplied.
-   **Scenario:** Exceptions disclose filesystem paths, SQL details,
    model prompts, internal hostnames, credentials, or sensitive
    transaction fields.
-   **Impact:** Information disclosure that assists further attacks.
-   **Proposed controls:**
    -   Return stable, generic error messages to clients with
        correlation IDs.
    -   Keep detailed diagnostics in access-controlled logs after
        redaction.
    -   Disable debug mode in production.
    -   Ensure exception paths do not expose prompts, credentials, or
        full financial records.
-   **Acceptance criteria:**
    -   Negative tests do not return stack traces or internal
        configuration.
    -   Logs contain sufficient diagnostic context without secrets or
        unnecessary financial payloads.

### T-17 --- Backup, recovery, and retention failure

-   **Priority:** Medium
-   **Evidence:** Database and report storage are part of the documented
    architecture; backup and retention arrangements are not specified.
-   **Scenario:** Sensitive backups are exposed, backups cannot be
    restored, or data is retained longer than intended.
-   **Impact:** Data loss, prolonged outage, and unnecessary exposure of
    historic financial records.
-   **Proposed controls:**
    -   Define backup scope, encryption, access, retention, and deletion
        policies.
    -   Test restoration and document recovery objectives.
    -   Include relevant databases, configuration, audit data, and
        model/dataset artifacts in recovery planning.
    -   Restrict backup access separately from ordinary application
        access.
-   **Acceptance criteria:**
    -   A documented restore test succeeds in the target environment.
    -   Backup access is restricted and encryption is verified.
    -   Retention and deletion behavior is documented and tested where
        applicable.

------------------------------------------------------------------------

## 8. Security Control Matrix

  -------------------------------------------------------------------------------------------------------
  Control ID     Requirement              Implementation area   Priority       Verification evidence
  -------------- ------------------------ --------------------- -------------- --------------------------
  SEC-01         Authenticate protected   FastAPI auth          Critical       Authentication tests
                 API requests             dependency                           

  SEC-02         Enforce action-level     Authorization module  Critical       Role/endpoint matrix tests
                 permissions                                                   

  SEC-03         Enforce owner/tenant     Service and           Critical       Cross-tenant isolation
                 scope on all records     repository layer                     tests

  SEC-04         Validate tokens and      Auth/configuration    Critical       Invalid-token and config
                 manage secrets securely                                       tests

  SEC-05         Validate and bound       Ingestion layer       High           Malformed/oversized-file
                 uploads                                                       tests

  SEC-06         Bound API and inference  API, queue, model     High           Load and limit tests
                 resource use             server                               

  SEC-07         Treat transaction text   AI orchestration      High           Prompt-injection test
                 as untrusted in LLM                                           suite
                 prompts                                                       

  SEC-08         Validate model outputs   AI boundary and       High           Adversarial output tests
                 against strict schemas   Pydantic schemas                     

  SEC-09         Recompute tax arithmetic GST engine            Critical       Tax-rule unit tests
                 deterministically                                             

  SEC-10         Protect training data    Training pipeline     High           Provenance and approval
                 and model promotion                                           tests

  SEC-11         Log sensitive actions    Audit subsystem       High           Event and redaction tests
                 safely                                                        

  SEC-12         Restrict internal        Deployment/database   High           Configuration review and
                 services and database                                         network tests
                 roles                                                         

  SEC-13         Scan and track           Build and release     High           SBOM and scan report
                 dependencies/artifacts   pipeline                             

  SEC-14         Secure exports and       Report builder        High           Export authorization and
                 temporary files                                               formula tests

  SEC-15         Secure backups and       Operations            Medium         Restore-test evidence
                 recovery                                                      

  SEC-16         Return safe errors and   API configuration     Medium         Error-path tests
                 disable debug mode                                            
  -------------------------------------------------------------------------------------------------------

------------------------------------------------------------------------

## 9. Proposed Identity and Authorization Model

The README does not define user roles. The following is a proposed
starting point to review with the project owner.

  -------------------------------------------------------------------------------------------------
  Role                     Read   Classify/reconcile       Export           Manage          Approve
                    transaction                           reports   users/settings   training/model
                           data                                                             changes
  --------------- ------------- -------------------- ------------ ---------------- ----------------
  Administrator      Explicitly          If required  If required              Yes          Only if
                         scoped                                                          separately
                                                                                         authorized

  Finance Analyst        Scoped    Yes, within scope      Limited               No               No

  Chartered              Scoped       Review/approve   Authorized               No               No
  Accountant /                          within scope      reports                  
  Reviewer                                                                         

  Read-Only             Scoped,         No mutations   Explicitly               No               No
  Auditor             read-only                         permitted                  

  Training/ML           Minimum    Run approved jobs        No by               No   Submit/retrain
  Operator            necessary                           default                           only as
                           data                                                        specifically
                                                                                          permitted

  Service                Narrow        Only required         Only   No interactive        No unless
  identity        service scope              actions     required   administration       explicitly
                                                          outputs                          assigned
  -------------------------------------------------------------------------------------------------

Important design rules:

-   Roles are not enough by themselves; resource ownership and
    organization scope must also be checked.
-   Default to deny when a permission is missing or cannot be evaluated.
-   Use separate service identities for API, worker, database migration,
    inference, and training tasks where practical.
-   Treat model output as untrusted. The model must not grant
    permissions or decide who can access records.
-   The proposed roles must be validated against actual business
    workflows before implementation.

------------------------------------------------------------------------

## 10. Proposed Audit Event Schema

Audit events should be structured and append-oriented. A proposed event
can contain:

``` json
{
  "event_id": "unique-event-id",
  "timestamp_utc": "ISO-8601 timestamp",
  "actor_id": "authenticated-user-or-service-id",
  "organization_id": "authorized-scope-if-applicable",
  "action": "report.export",
  "resource_type": "reconciliation_report",
  "resource_id": "opaque-resource-id",
  "outcome": "denied",
  "reason_code": "insufficient_permission",
  "request_id": "correlation-id"
}
```

This is an illustrative schema, not a schema found in the supplied
project. Do not include passwords, bearer tokens, signing keys, full
prompts, or complete ledger rows by default. Minimize identifiers and
financial details according to the investigation and retention
requirements.

Events should cover authentication successes and failures, authorization
denials, sensitive reads where warranted, uploads, exports, privileged
mutations, reconciliation approvals, training-data promotion, model
deployment, configuration changes, and administrative actions.

------------------------------------------------------------------------

## 11. Implementation and Verification Plan

### Phase 1 --- Research and specification

1.  Confirm the project owner's expected threat model and security
    deliverables.
2.  Identify whether the deployment is single-tenant or multi-tenant.
3.  Obtain the actual source repository, API routes, schemas, and
    deployment files when available.
4.  Map assets, trust boundaries, actors, data flows, and privilege
    transitions.
5.  Review the current OWASP API and GenAI/LLM risk guidance.
6.  Finalize the threat register and acceptance criteria.

**Exit criteria:** architecture assumptions are labeled, high-priority
threats are reviewed, and security requirements are testable.

### Phase 2 --- Security foundation

1.  Implement configuration validation and secret handling.
2.  Implement authentication and token validation.
3.  Define roles, permissions, and default-deny authorization.
4.  Add tenant/owner-scoped access patterns.
5.  Add structured audit events and safe error handling.

**Exit criteria:** authentication, permission, ownership, and audit
tests pass.

### Phase 3 --- Data and AI protection

1.  Add upload format and resource limits.
2.  Harden inference request boundaries and output validation.
3.  Add prompt-injection and malicious-field test cases.
4.  Protect hard-negative data, pseudo-labels, datasets, and model
    promotion.
5.  Verify deterministic tax validation and report export protections.

**Exit criteria:** malicious inputs fail safely, model output cannot
bypass authorization, and consequential tax calculations remain
deterministic.

### Phase 4 --- Deployment and operations

1.  Review container hardening and network exposure.
2.  Restrict PostgreSQL, Redis, and model endpoints.
3.  Generate an SBOM and dependency/container scan report.
4.  Document backup, restore, key rotation, and incident response
    procedures.
5.  Run integration and load tests in a controlled environment.

**Exit criteria:** deployment review is complete, test evidence is
recorded, and known residual risks have owners and mitigation plans.

------------------------------------------------------------------------

## 12. Acceptance Criteria and Test Evidence

The security layer should not be considered complete until the relevant
tests have been run and their results recorded.

  ------------------------------------------------------------------------------
  Test ID           Test               Expected result   Evidence to retain
  ----------------- ------------------ ----------------- -----------------------
  AT-01             Request a          Rejected          Automated test output
                    protected endpoint                   
                    without                              
                    credentials                          

  AT-02             Submit expired or  Rejected          Automated test output
                    tampered access                      
                    token                                

  AT-03             Change an object   No unauthorized   Cross-tenant test
                    ID to another      data access or    
                    tenant's record    mutation          

  AT-04             Read-only user     Rejected          Role-permission test
                    attempts                             
                    privileged                           
                    operation                            

  AT-05             Submit malformed   Rejected or       Upload test results
                    and oversized      safely            
                    files              quarantined       
                                       within configured 
                                       limits            

  AT-06             Submit adversarial No unauthorized   LLM adversarial test
                    prompt-injection   data access or    report
                    text in            tool action;      
                    transaction fields unsafe output     
                                       rejected          

  AT-07             Submit malformed   Rejected or       Schema validation tests
                    or out-of-schema   quarantined       
                    model output                         

  AT-08             Send requests      Throttled or      Load-test report
                    beyond configured  rejected          
                    quotas             predictably       

  AT-09             Attempt            Denied            Audit access-control
                    unauthorized                         test
                    audit-log                            
                    modification                         

  AT-10             Export text        Safely encoded as Workbook
                    beginning with     text              inspection/test
                    spreadsheet                          
                    formula characters                   

  AT-11             Inspect logs after No credentials or Redaction test
                    failed             unnecessary       
                    authentication and sensitive         
                    malformed input    payloads          

  AT-12             Attempt to reach   Blocked according Network/configuration
                    internal services  to deployment     test
                    from an untrusted  design            
                    network                              

  AT-13             Inspect            Versions tracked  SBOM and scan report
                    dependencies and   and scan results  
                    container images   reviewed          

  AT-14             Restore protected  Restore completes Restore-test record
                    data from backup   within defined    
                                       objectives        

  AT-15             Change a GST       Rejected;         Integrity and
                    amount or          permitted changes authorization test
                    reconciliation     are traceable     
                    flag without                         
                    authorization                        
  ------------------------------------------------------------------------------

Test evidence should include the test environment, date, software
version, expected result, actual result, pass/fail status, and issue
reference. Do not mark a control as implemented based only on a design
statement.

------------------------------------------------------------------------

## 13. Residual Risks and Limitations

Even after implementing the proposed controls:

-   Prompt injection and model misclassification cannot be guaranteed to
    be eliminated; they must be constrained, tested, and monitored.
-   Self-hosted inference does not automatically protect data from
    compromised hosts, privileged insiders, misconfigured networks, or
    insecure logs.
-   Encryption does not replace authorization, key management, or access
    monitoring.
-   JWT authentication does not replace object-level and function-level
    authorization.
-   Agreement between two encoders does not prove that a pseudo-label is
    correct.
-   Deterministic tax arithmetic can still be wrong if the applicable
    business rules, input assumptions, or statutory rules are incorrect
    or outdated.
-   Security test results are evidence for the tested configuration and
    version, not a universal guarantee.
-   Legal, tax, privacy, retention, and sector-specific obligations
    require confirmation by the appropriate project owner or qualified
    advisor.

### Open questions requiring project-owner input

1.  Is VYOM+ intended for one organization or multiple organizations?
2.  Which user roles and approval workflows are required?
3.  Will the API be exposed publicly, only internally, or through a
    private network?
4.  Where will PostgreSQL, Redis, uploaded files, model weights, and
    audit logs be stored?
5.  Will model inference or any supporting telemetry ever call external
    services?
6.  What are the expected maximum file size, row count, concurrency, and
    inference latency?
7.  What retention and deletion policies apply to ledgers, exports,
    logs, and backups?
8.  Which operations can change approved financial or tax state, and who
    may approve them?
9.  What is the source of truth for current GST rules and external
    reconciliation datasets?
10. What recovery and incident-response expectations apply?

------------------------------------------------------------------------

## 14. Research References

The following primary references inform the proposed controls. They
provide general security guidance; they do not prove that VYOM+ has a
specific vulnerability.

1.  **OWASP Foundation --- OWASP API Security Top 10 (2023).** Covers
    broken object-level authorization, broken authentication,
    property-level authorization, unrestricted resource consumption,
    function-level authorization, security misconfiguration, and related
    API risks.\
    https://owasp.org/www-project-api-security/\
    https://api-security.owasp.org/editions/2023/en/0x11-t10/

2.  **OWASP GenAI Security Project --- OWASP Top 10 for LLM Applications
    (2026).** Current guidance includes prompt injection, sensitive
    information disclosure, excessive agency, supply-chain
    vulnerabilities, data/model poisoning, unbounded consumption, hidden
    context exposure, vector and embedding weaknesses, and improper
    output handling.\
    https://owasp.github.io/www-project-top-10-for-large-language-model-applications/\
    https://github.com/GenAI-Security-Project/GenAI-LLM-Top10

3.  **FastAPI --- OAuth2 with Password (and hashing), Bearer with JWT
    tokens.** Practical implementation guidance for signed JWTs, token
    expiration, password hashing, and the use of PyJWT and pwdlib. JWT
    payloads are signed, not inherently encrypted, and should not
    contain secrets.\
    https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/

4.  **VYOM+ project README supplied for this task.** Primary source for
    the documented system pipeline, stated technology stack, intended
    self-hosted architecture, GST validation, reconciliation,
    hard-negative queue, and reporting capabilities. The README is
    design documentation rather than implementation or audit evidence.

------------------------------------------------------------------------

## 15. Conclusion

The initial VYOM+ security strategy should prioritize identity and
authorization, financial data isolation, safe ingestion, AI trust
boundaries, deterministic GST integrity, and auditability. Resource
limits, deployment hardening, and supply-chain controls should be
included in the same security design.

The next implementation milestone is a standalone FastAPI security
prototype with automated tests. Integration claims should remain
provisional until the actual VYOM+ repository and deployment
configuration are available. This threat model should be updated as
those details are verified and as test evidence changes the risk
assessment.
