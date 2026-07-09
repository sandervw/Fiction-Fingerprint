"""Generate seed_authors.csv from the corpus folder tree.

One work per corpus/<Author>/*.md; metadata from AUTHOR_META, title from
frontmatter or first heading, work_id from the filename. The seed IS the dbt
manifest the extractor reads, so re-run after adding or removing files.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CORPUS = REPO_ROOT / "corpus"
SEED = REPO_ROOT / "prose_fingerprint" / "seeds" / "seed_authors.csv"

FIELDS = ["work_id", "title", "author", "tradition", "era", "is_self", "path"]

# folder name -> (author, tradition, era, is_self); insertion order = row order.
AUTHOR_META: dict[str, tuple[str, str, str, bool]] = {
    "Sander-VanWilligen": ("Sander VanWilligen", "speculative fiction", "contemporary", True),
    "Clark-Ashton-Smith": ("Clark Ashton Smith", "weird fiction", "1930s", False),
    "Diana-Wynne-Jones": ("Diana Wynne Jones", "children's fantasy", "1986", False),
    "E-R-Eddison": ("E. R. Eddison", "heroic high fantasy", "1922", False),
    "Jack-Vance": ("Jack Vance", "science fantasy (Dying Earth)", "1950s-80s", False),
    "J-R-R-Tolkien": ("J. R. R. Tolkien", "high fantasy", "1937-1955", False),
    "Karl-Edward-Wagner": ("Karl Edward Wagner", "sword & sorcery / dark fantasy", "1970s-80s", False),
    "Mervyn-Peake": ("Mervyn Peake", "gothic fantasy", "1946-1959", False),
    "R-A-Salvatore": ("R. A. Salvatore", "heroic fantasy (Forgotten Realms)", "1988-present", False),
    "Robert-E-Howard": ("Robert E. Howard", "sword & sorcery (Conan)", "1930s", False),
    "William-Hope-Hodgson": ("William Hope Hodgson", "weird / cosmic horror", "1900s-10s", False),
}

_FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
_FM_TITLE = re.compile(r'(?m)^title:\s*"?(.*?)"?\s*$')
_H1 = re.compile(r"(?m)^#\s+(.*?)\s*$")


def slugify(stem: str) -> str:
    """Filename stem -> clean work_id: lowercase, hyphen-collapsed."""
    s = stem.lower().replace("'", "").replace("’", "")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def title_of(text: str, stem: str) -> str:
    """Frontmatter title, else first heading, else titleized filename."""
    fm = _FRONTMATTER.match(text)
    if fm:
        m = _FM_TITLE.search(fm.group(1))
        if m:
            return m.group(1)
    m = _H1.search(text)
    return m.group(1) if m else stem.replace("-", " ").title()


def main() -> None:
    # Every corpus subdirectory needs a metadata entry or its works are skipped.
    unknown = sorted(
        d.name for d in CORPUS.iterdir() if d.is_dir() and d.name not in AUTHOR_META
    )
    if unknown:
        print("WARNING: corpus folders with no AUTHOR_META entry (skipped):")
        for name in unknown:
            print(f"  {name}")

    rows: list[dict[str, str]] = []
    seen: dict[str, Path] = {}
    for folder, (author, tradition, era, is_self) in AUTHOR_META.items():
        for md in sorted((CORPUS / folder).glob("*.md")):
            if md.name.startswith(("_", ".")):
                continue
            work_id = slugify(md.stem)
            if work_id in seen:
                raise SystemExit(f"Duplicate work_id {work_id!r}: {md} vs {seen[work_id]}")
            seen[work_id] = md
            text = md.read_text(encoding="utf-8").replace("\r\n", "\n")
            rows.append({
                "work_id": work_id,
                "title": title_of(text, md.stem),
                "author": author,
                "tradition": tradition,
                "era": era,
                "is_self": "true" if is_self else "false",
                "path": md.relative_to(REPO_ROOT).as_posix(),
            })

    with SEED.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} works to {SEED.relative_to(REPO_ROOT).as_posix()}")
    for folder, (author, *_rest) in AUTHOR_META.items():
        n = sum(1 for r in rows if r["author"] == author)
        print(f"  {n:3d}  {author}")


if __name__ == "__main__":
    main()
