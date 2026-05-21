"""
wiki/ 디렉터리의 리포트 목록으로 Home.md 인덱스 갱신.

실행:
    python scripts/update_wiki_index.py wiki/
"""
import re
import sys
from pathlib import Path


def main(wiki_dir: str) -> None:
    wiki = Path(wiki_dir)
    reports = sorted(wiki.glob("*-weekly.md"), reverse=True)

    lines = [
        "# 주간 트레이딩 리포트",
        "",
        "| 날짜 | 리포트 |",
        "|------|------|",
    ]
    for r in reports:
        m = re.match(r"(\d{4}-\d{2}-\d{2})-weekly", r.stem)
        if m:
            date = m.group(1)
            lines.append(f"| {date} | [[{r.stem}]] |")

    home = wiki / "Home.md"
    home.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"✓ Home.md 업데이트: 리포트 {len(reports)}개")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/update_wiki_index.py <wiki_dir>")
        sys.exit(1)
    main(sys.argv[1])
