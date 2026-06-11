from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

from docx import Document


ROLE_RX = re.compile(r"^\s*(?P<role>agent|customer|sales(?:person)?|user)\s*[:\-]\s*(?P<text>.+?)\s*$", re.IGNORECASE)
SPACE_RX = re.compile(r"\s+")


def normalize_text(value: str) -> str:
    return SPACE_RX.sub(" ", value).strip()


def iter_docx_conversations(path: Path) -> list[dict[str, str]]:
    document = Document(path)
    rows: list[dict[str, str]] = []
    current_turns: list[str] = []
    conversation_index = 1

    def flush() -> None:
        nonlocal conversation_index, current_turns
        text = normalize_text(" ".join(current_turns))
        if text:
            rows.append(
                {
                    "file": f"{path.stem}_{conversation_index:03d}.docx",
                    "source_file": path.name,
                    "conversation_id": f"{path.stem}_{conversation_index:03d}",
                    "text": text,
                }
            )
            conversation_index += 1
        current_turns = []

    for paragraph in document.paragraphs:
        line = normalize_text(paragraph.text)
        if not line:
            flush()
            continue

        if line.lower().startswith(("conversation ", "call ", "transcript ")):
            flush()
            continue

        match = ROLE_RX.match(line)
        if match:
            role = match.group("role").lower()
            role = "Agent" if role in {"agent", "sales", "salesperson"} else "Customer"
            current_turns.append(f"{role}: {match.group('text')}")
        else:
            current_turns.append(line)

    flush()
    return rows


def write_csv(rows: list[dict[str, str]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["file", "source_file", "conversation_id", "text"]
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert Agent/Customer Word transcripts into a CSV for extraction benchmarking.")
    parser.add_argument("input", type=Path, help="Path to one .docx file or a folder containing .docx files.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/raw/word_conversations.csv"),
        help="CSV output path. Defaults to data/raw/word_conversations.csv.",
    )
    args = parser.parse_args()

    inputs = sorted(args.input.glob("*.docx")) if args.input.is_dir() else [args.input]
    rows: list[dict[str, str]] = []
    for path in inputs:
        if path.suffix.lower() != ".docx":
            raise SystemExit(f"Only .docx files are supported: {path}")
        rows.extend(iter_docx_conversations(path))

    write_csv(rows, args.output)
    print(f"Wrote {len(rows)} conversation(s) to {args.output}")


if __name__ == "__main__":
    main()
