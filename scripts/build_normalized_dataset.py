import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from src.data_pipeline import (
    NormalizedQuery,
    QualityReport,
    deduplicate,
    normalize_record,
    print_dataset_statistics,
    save_statistics,
    split_records,
    validate_record,
)
from src.data_pipeline.config import BIRD_DIR, PROCESSED_DIR, RAW_DIR, SPIDER_DIR, SYNTHETIC_DIR


def load_raw_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if not line_str:
                continue
            records.append(json.loads(line_str))
    return records


def load_raw_json(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
        if isinstance(data, list):
            return data
        return [data]


def load_raw_records(path: Path) -> list[dict[str, Any]]:
    if path.suffix == ".jsonl":
        return load_raw_jsonl(path)
    elif path.suffix == ".json":
        return load_raw_json(path)
    return []


def process_source(
    source: str,
    path: Path,
    report: QualityReport,
) -> list[NormalizedQuery]:
    """Normalize raw records from a single source file, updating report in-place."""
    raw_records = load_raw_records(path)
    if not raw_records:
        print(f"[{source.upper()}] No raw records found at {path}")
        return []

    # Check if a sibling schema.sql file exists
    schema_file = path.parent / "schema.sql"
    default_ddl = ""
    if schema_file.exists():
        try:
            default_ddl = schema_file.read_text(encoding="utf-8").strip()
        except Exception:
            default_ddl = ""

    normalized = []
    for index, record in enumerate(raw_records):
        report.total_records += 1

        # Track missing fields on the raw record before normalization
        if not record.get("ddl") and not default_ddl:
            report.missing_ddl += 1
        if not record.get("sql") and not record.get("query") and not record.get("SQL"):
            report.missing_sql += 1
        if not record.get("question") and not record.get("prompt"):
            report.missing_question += 1

        try:
            # Inject ddl from schema.sql if record doesn't have it
            if not record.get("ddl") and default_ddl:
                record["ddl"] = default_ddl

            # Inject database_id from folder name if missing
            if not record.get("database_id") and not record.get("db_id"):
                record["database_id"] = path.parent.name

            result = normalize_record(source, record, index)
            errors = validate_record(result)

            if errors:
                print(f"Skipping {source} record {index}: {errors}")
                report.invalid_records += 1
                continue

            report.valid_records += 1
            normalized.append(result)
        except Exception as e:
            print(f"Failed {source} record {index}: {e}")
            report.invalid_records += 1

    print(
        f"[{source.upper()}] Successfully normalized "
        f"{len(normalized)}/{len(raw_records)} records from {path.name}"
    )
    return normalized


def discover_source_files() -> list[tuple[str, Path]]:
    sources = []

    # 1. Synthetic datasets (search all subfolders for examples.jsonl)
    if SYNTHETIC_DIR.exists():
        for sub in SYNTHETIC_DIR.iterdir():
            if sub.is_dir():
                jsonl_file = sub / "examples.jsonl"
                if jsonl_file.exists():
                    sources.append(("synthetic", jsonl_file))

    # 2. Spider dataset
    if SPIDER_DIR.exists():
        for fname in ["train.json", "examples.jsonl", "spider.json"]:
            p = SPIDER_DIR / fname
            if p.exists():
                sources.append(("spider", p))
                break

    # 3. BIRD dataset
    if BIRD_DIR.exists():
        for fname in ["train.json", "examples.jsonl", "bird.json"]:
            p = BIRD_DIR / fname
            if p.exists():
                sources.append(("bird", p))
                break

    return sources


def write_split(records: list[NormalizedQuery], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")
    print(f"  Wrote {len(records):>6,} records -> {path.name}")


def main() -> None:
    report = QualityReport()
    all_records: list[NormalizedQuery] = []

    # 1. Discover source files
    source_files = discover_source_files()

    if source_files:
        for source, path in source_files:
            records = process_source(source, path, report)
            all_records.extend(records)
    else:
        # Fallback to direct paths for standalone dataset files
        for source, fname in [
            ("spider", "spider.jsonl"),
            ("bird", "bird.jsonl"),
            ("synthetic", "synthetic.jsonl"),
        ]:
            records = process_source(source, RAW_DIR / fname, report)
            all_records.extend(records)

    print(f"\nBefore deduplication: {len(all_records)}")
    pre_dedup_count = len(all_records)

    all_records = deduplicate(all_records)
    report.duplicates_removed = pre_dedup_count - len(all_records)

    print(f"After deduplication:  {len(all_records)}\n")

    # 2. Print formatted statistics
    print_dataset_statistics(all_records)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # 3. Write normalized.jsonl
    normalized_path = PROCESSED_DIR / "normalized.jsonl"
    write_split(all_records, normalized_path)

    # 4. Split into train / validation / test
    train, val, test = split_records(all_records)
    print("\nSplits:")
    write_split(train, PROCESSED_DIR / "train.jsonl")
    write_split(val, PROCESSED_DIR / "validation.jsonl")
    write_split(test, PROCESSED_DIR / "test.jsonl")

    # 5. Save statistics.json
    stats_path = PROCESSED_DIR / "statistics.json"
    save_statistics(all_records, stats_path)
    print(f"\n  Wrote statistics       -> {stats_path.name}")

    # 6. Save quality_report.json
    quality_path = PROCESSED_DIR / "quality_report.json"
    report.save(quality_path)
    print(f"  Wrote quality report   -> {quality_path.name}")

    print(f"\nSUCCESS: All outputs saved to {PROCESSED_DIR}")


if __name__ == "__main__":
    main()
