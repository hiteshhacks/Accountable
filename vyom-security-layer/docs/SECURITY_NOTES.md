# Security Notes and Implementation Boundaries

## Implemented in this prototype
- JWT access-token issuance and verification with fixed HS256 allowlist, issuer, audience, and time claims.
- Password hashing through Argon2 via `argon2-cffi`.
- Central permission matrix for invoice read/create/update/delete and audit viewing.
- Tenant scoping on invoice list/detail/update/delete queries.
- Pydantic request validation with forbidden extra fields.
- Basic request content-length check, configurable request limit, and response security headers.
- In-memory failed-login throttling for the local prototype.
- Minimal audit events for login, token failures, authorization denials, and invoice access/create/update/delete.
- Soft deletion for invoices so destructive actions remain traceable in audit history.
- Upload validation for `.csv`, `.xlsx`, and `.parquet` with size, row, column, archive, magic-byte, external-link, formula-cell, and mandatory business-header checks.
- LLM boundary validation that rejects prompt-injection text and malformed/out-of-schema classification outputs.
- Deterministic GST arithmetic for supported GST slabs with fixed rule version, source URL, trace ID, and repeatable rounding.
- Integrated `/pipeline/validate` route that requires RBAC, validates upload content, validates model output, evaluates GST, preserves tenant scope, and writes audit events.

## Tested controls
- Missing, tampered, and stale credentials are rejected.
- Demo role users can authenticate and are allowed or denied according to the role matrix.
- Cross-tenant invoice reads and updates are blocked.
- Unexpected payload fields, control characters, malformed GSTINs, missing mandatory upload headers, malicious upload formulas, oversized CSV row counts, prompt-injection text, and malformed LLM outputs are rejected.
- GST calculations are deterministic for repeated equivalent inputs and include `rule_version`, `source_url`, and `trace_id`.
- The integrated pipeline permits `finance_analyst` and denies `auditor`, while recording audit evidence.

## Not implemented
- Full VYOM+ integration.
- MFA, password reset, refresh-token rotation, persistent account lockout, distributed rate limiting.
- Cryptographically tamper-evident audit logging or external SIEM.
- Full spreadsheet parsing, business-level schema mapping, quarantine storage, antivirus scanning, training-data poisoning defense, reconciliation, report export controls, or live GST portal integration.
- Production secrets management, TLS termination, database-level row security, backup controls, or compliance certification.
- Live HSN/SAC rate lookup and legal/tax advisory validation. The demo GST module enforces deterministic arithmetic only for caller-supplied supported rates.

## Assumptions
- The API remains a standalone security-layer prototype, not the full VYOM+ production backend.
- Demo GST source metadata points to the CBIC GST goods/services rates page, but this prototype does not scrape or continuously update statutory rate tables.
- `.csv` and `.xlsx` validation require mandatory business headers covering seller/supplier, buyer/customer, invoice number/date, item details, quantities, taxable value, GST, freight, payment, currency, import/export, payroll, debit/credit, return, order, delivery, and metadata fields. Discount is recognized when present but is not mandatory.
- `.xlsx` validation inspects archive structure and worksheet XML for formulas/external links; it does not fully evaluate workbook semantics.
- `.parquet` is recognized by magic bytes but rejected until a schema parser is integrated, because mandatory headers cannot be verified safely without reading the schema.
- LLM validation protects the boundary around model input/output; no model is invoked by this prototype.

## Design constraints
- Do not trust client-supplied `organization_id` or `role`.
- Do not allow an LLM to decide access permissions.
- Keep GST arithmetic and statutory rules in deterministic, tested code.
- Treat imported rows and model output as untrusted.
- Never log passwords, access tokens, signing secrets, or complete financial records.
- Do not expose interactive API docs publicly without an explicit decision.
- Audit records share the prototype database; a privileged database operator could alter them.

## Residual risks
- Upload validation reduces risk but does not replace sandboxed parsing, malware scanning, content disarm/reconstruction, or gateway-level size limits.
- Prompt-injection detection is pattern based and must be supplemented with constrained prompts, tool isolation, monitoring, and adversarial test suites in production.
- GST rule correctness still depends on verified, current legal source data and qualified review.
- Audit events are structured but not tamper-evident.
- In-memory rate limiting resets on restart and does not protect multi-process deployments.
