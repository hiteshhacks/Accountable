import csv
import io
import re
import zipfile
from dataclasses import dataclass
from xml.etree import ElementTree


SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".parquet"}
MAX_UPLOAD_BYTES = 1_000_000
MAX_CSV_ROWS = 1_000
MAX_CSV_COLUMNS = 80
MAX_ZIP_ENTRIES = 200
MAX_ZIP_UNCOMPRESSED_BYTES = 5_000_000
FORMULA_PREFIXES = ("=", "+", "-", "@")
OPTIONAL_HEADER_ALIASES = {"discount", "discount_amount"}
REQUIRED_HEADER_GROUPS = {
    "seller_supplier": {"seller", "supplier", "vendor"},
    "buyer_customer": {"buyer", "customer", "recipient"},
    "invoice_number": {"invoice_number", "invoice_no", "invoice_id", "bill_number", "document_number",
                       "export_invoice_no", "import_bill_no", "consignment_invoice", "buyer_invoice",
                       "against_invoice", "original_invoice_ref"},
    "invoice_date": {"invoice_date", "date", "bill_date", "document_date", "po_date", "payment_date",
                     "receipt_date", "entry_date", "claim_date", "order_date", "dispatch_date",
                     "date_of_dispatch", "date_of_receipt", "transaction_date", "so_date"},
    "item_description": {"item_description", "description", "item", "particulars", "product", "material",
                         "material_description", "item_name", "item_received", "item_dispatched",
                         "export_item", "import_item"},
    "quantity": {"quantity", "qty", "units", "quantity_required", "quantity_received", "quantity_rejected",
                 "quantity_shipped", "quantity_sent", "quantity_ordered", "units_returned",
                 "units_exported", "units_imported"},
    "taxable_value": {"taxable_value", "taxable_amount", "taxable", "base_amount", "total_value", "amount",
                      "payment_amount", "received_amount", "amount_claimed", "free_on_board_value",
                      "cost_insurance_freight", "transfer_amount"},
    "gst": {"gst", "gst_amount", "tax", "tax_amount", "import_gst"},
    "freight": {"freight", "shipping", "transport", "freight_charges", "transport_cost", "courier_transport",
                "other_charges"},
    "payment_information": {"payment_information", "payment_info", "payment_status", "payment_mode",
                            "mode_of_payment", "payment_method", "payment_type", "payment_terms",
                            "bank_details", "bank_ifsc_code"},
    "currency": {"currency", "currency_code"},
    "import_export_details": {"import_export_details", "import_export", "export_details", "import_details",
                              "destination_country", "originating_country", "exporter", "importer",
                              "customs_duty", "export_incentive", "original_currency", "payment_currency"},
    "payroll_information": {"payroll_information", "payroll", "salary", "wages", "payroll_period",
                            "gross_salary", "net_payable", "dearness_allowance", "other_benefits",
                            "professional_tax", "income_tax_deduction", "employee_code",
                            "employee_full_name"},
    "debit_credit_information": {"debit_credit_information", "debit_credit", "debit", "credit",
                                 "debit_side", "credit_side", "source_account", "destination_account",
                                 "contra_id", "journal_id", "journal_type"},
    "return_information": {"return_information", "return", "refund", "reason_for_return", "units_returned",
                           "rejection_note_no", "rejection_date", "item_rejected", "rejection_reason",
                           "dn_reference", "original_doc_ref"},
    "order_references": {"order_references", "order_reference", "po_number", "purchase_order", "po_ref",
                         "po_reference", "reference_po", "so_number", "so_reference", "reference_number",
                         "original_doc_ref", "grn_reference", "jwoo_ref", "jwio_ref"},
    "delivery_information": {"delivery_information", "delivery", "delivery_date", "dispatch", "delivery_ref",
                             "delivery_challan_no", "delivery_address", "promised_delivery",
                             "expected_arrival", "storage_location", "storage", "storage_area",
                             "storage_facility"},
    "metadata": {"metadata", "notes", "remarks", "tags"},
}


class UploadRejected(ValueError):
    def __init__(self, reason: str, diagnostics: dict | None = None):
        super().__init__(reason)
        self.reason = reason
        self.diagnostics = diagnostics or {}


@dataclass(frozen=True)
class UploadValidationResult:
    filename: str
    extension: str
    size_bytes: int
    detected_type: str
    row_count: int | None = None
    warning_count: int = 0
    diagnostics: dict | None = None


def _extension(filename: str) -> str:
    lowered = filename.lower().strip()
    for extension in SUPPORTED_EXTENSIONS:
        if lowered.endswith(extension):
            return extension
    raise UploadRejected("unsupported_file_type")


def _reject_formula_cells(rows: list[list[str]]) -> None:
    for row in rows:
        for cell in row:
            if cell.strip().startswith(FORMULA_PREFIXES):
                raise UploadRejected("spreadsheet_formula_cell")


def _normalize_header(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def inspect_headers(headers: list[str]) -> dict:
    normalized = {_normalize_header(header) for header in headers if header and header.strip()}
    matched = {
        group: sorted(normalized.intersection(aliases))
        for group, aliases in REQUIRED_HEADER_GROUPS.items()
        if not normalized.isdisjoint(aliases)
    }
    missing = [
        group
        for group, aliases in REQUIRED_HEADER_GROUPS.items()
        if normalized.isdisjoint(aliases)
    ]
    known_aliases = set().union(*REQUIRED_HEADER_GROUPS.values()).union(OPTIONAL_HEADER_ALIASES)
    abrupt = sorted(header for header in normalized if header and header not in known_aliases)
    return {
        "raw_headers": headers,
        "normalized_headers": sorted(normalized),
        "matched_required_groups": matched,
        "missing_required_groups": missing,
        "abrupt_or_unmapped_headers": abrupt,
    }


def _validate_required_headers(headers: list[str]) -> dict:
    diagnostics = inspect_headers(headers)
    missing = diagnostics["missing_required_groups"]
    if missing:
        raise UploadRejected("missing_required_headers", diagnostics)
    return diagnostics


def _xlsx_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
    strings = []
    for item in root.iter():
        if item.tag.endswith("}si") or item.tag == "si":
            text_parts = [
                text_node.text or ""
                for text_node in item.iter()
                if text_node.tag.endswith("}t") or text_node.tag == "t"
            ]
            strings.append("".join(text_parts))
    return strings


def _xlsx_first_row_headers(archive: zipfile.ZipFile, shared_strings: list[str]) -> list[str]:
    worksheet_names = sorted(
        name for name in archive.namelist()
        if name.startswith("xl/worksheets/") and name.endswith(".xml")
    )
    if not worksheet_names:
        raise UploadRejected("xlsx_missing_worksheet")
    root = ElementTree.fromstring(archive.read(worksheet_names[0]))
    first_row = None
    for row in root.iter():
        if row.tag.endswith("}row") or row.tag == "row":
            first_row = row
            break
    if first_row is None:
        raise UploadRejected("xlsx_missing_header_row")
    headers = []
    for cell in first_row:
        if not (cell.tag.endswith("}c") or cell.tag == "c"):
            continue
        cell_type = cell.attrib.get("t")
        raw_value = ""
        for child in cell:
            if child.tag.endswith("}v") or child.tag == "v":
                raw_value = child.text or ""
                break
            if child.tag.endswith("}is") or child.tag == "is":
                raw_value = "".join(text_node.text or "" for text_node in child.iter()
                                    if text_node.tag.endswith("}t") or text_node.tag == "t")
                break
        if cell_type == "s" and raw_value.isdigit() and int(raw_value) < len(shared_strings):
            headers.append(shared_strings[int(raw_value)])
        else:
            headers.append(raw_value)
    return headers


def _validate_csv(filename: str, content: bytes) -> UploadValidationResult:
    try:
        decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise UploadRejected("csv_must_be_utf8") from exc
    sample = decoded[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample) if sample else csv.excel
    except csv.Error:
        dialect = csv.excel
    rows = list(csv.reader(io.StringIO(decoded), dialect))
    if len(rows) > MAX_CSV_ROWS:
        raise UploadRejected("too_many_rows")
    if any(len(row) > MAX_CSV_COLUMNS for row in rows):
        raise UploadRejected("too_many_columns")
    _reject_formula_cells(rows)
    if not rows:
        raise UploadRejected("missing_header_row")
    diagnostics = _validate_required_headers(rows[0])
    return UploadValidationResult(filename=filename, extension=".csv", size_bytes=len(content),
                                  detected_type="text/csv", row_count=len(rows), diagnostics=diagnostics)


def _validate_xlsx(filename: str, content: bytes) -> UploadValidationResult:
    if not zipfile.is_zipfile(io.BytesIO(content)):
        raise UploadRejected("invalid_xlsx_zip")
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        entries = archive.infolist()
        if len(entries) > MAX_ZIP_ENTRIES:
            raise UploadRejected("too_many_archive_entries")
        total_uncompressed = sum(entry.file_size for entry in entries)
        if total_uncompressed > MAX_ZIP_UNCOMPRESSED_BYTES:
            raise UploadRejected("archive_uncompressed_size_too_large")
        for entry in entries:
            if entry.file_size and entry.compress_size and entry.file_size / entry.compress_size > 100:
                raise UploadRejected("suspicious_compression_ratio")
            if entry.filename.startswith("/") or ".." in entry.filename.split("/"):
                raise UploadRejected("unsafe_archive_path")
            if entry.filename.startswith("xl/externalLinks/"):
                raise UploadRejected("external_workbook_link")
            if entry.filename.startswith("xl/worksheets/") and entry.filename.endswith(".xml"):
                data = archive.read(entry.filename, pwd=None)[:200_000]
                if b"<f" in data:
                    raise UploadRejected("spreadsheet_formula_cell")
        diagnostics = _validate_required_headers(_xlsx_first_row_headers(archive, _xlsx_shared_strings(archive)))
    return UploadValidationResult(filename=filename, extension=".xlsx", size_bytes=len(content),
                                  detected_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                  diagnostics=diagnostics)


def _validate_parquet(filename: str, content: bytes) -> UploadValidationResult:
    if len(content) < 8 or not (content.startswith(b"PAR1") and content.endswith(b"PAR1")):
        raise UploadRejected("invalid_parquet_magic")
    raise UploadRejected("parquet_header_validation_requires_schema_parser")
    return UploadValidationResult(filename=filename, extension=".parquet", size_bytes=len(content),
                                  detected_type="application/vnd.apache.parquet")


def validate_upload(filename: str, content: bytes) -> UploadValidationResult:
    if not filename or len(filename) > 180:
        raise UploadRejected("invalid_filename")
    if len(content) == 0:
        raise UploadRejected("empty_file")
    if len(content) > MAX_UPLOAD_BYTES:
        raise UploadRejected("file_too_large")
    extension = _extension(filename)
    if extension == ".csv":
        return _validate_csv(filename, content)
    if extension == ".xlsx":
        return _validate_xlsx(filename, content)
    return _validate_parquet(filename, content)
