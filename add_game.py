#!/usr/bin/env python3
"""한입게임에 새 게임 추가 자동화.

사용법:
  # Drive 파일 ID로 추가
  ./add_game.py drive:1ph8o7VZui0Uv3vNgkbi0Y9DAppheoRbo "고객 만족을 향하여" \
      --emoji "🏃‍♀️" \
      --desc "상담사 횡스크롤 러너 · 양해와 공감을 모아 만족 100% 도달" \
      --controls "좌우 화살표 / 스페이스 점프 · 모바일 터치 OK" \
      --slug customer_satisfaction

  # 로컬 HTML 파일로 추가
  ./add_game.py path/to/game.html "퍼즐 메모리" --emoji 🧠 --desc "..." --slug memory

자동으로:
  1. HTML 다운로드/복사 → bitegames/<slug>.html
  2. index.html에 카드 추가
  3. README.md 표 업데이트
  4. git commit + push
"""
import argparse, re, subprocess, sys, urllib.request, shutil
from pathlib import Path

REPO = Path(__file__).resolve().parent
INDEX = REPO / "index.html"
README = REPO / "README.md"


def fetch_drive(file_id: str) -> bytes:
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def add_card(slug: str, title: str, emoji: str, desc: str, controls: str):
    html = INDEX.read_text(encoding="utf-8")
    card = f'''      <a class="game-card" href="{slug}.html">
        <div class="game-title">{title} {emoji}</div>
        <div class="game-desc">{desc}</div>
        <div class="game-meta">조작: {controls}</div>
      </a>'''
    # 마지막 </div> 바로 위에 끼움 (games 컨테이너 닫기 직전)
    pattern = re.compile(r'(<div class="games">[\s\S]*?)(\n    </div>\s*<footer)')
    m = pattern.search(html)
    if not m:
        sys.exit("!! index.html games 컨테이너 못 찾음")
    games_block = m.group(1)
    if f'href="{slug}.html"' in games_block:
        print(f"  index.html에 이미 {slug} 카드 있음, 스킵")
        return
    new = games_block + "\n" + card + m.group(2)
    INDEX.write_text(html.replace(m.group(0), new), encoding="utf-8")
    print(f"  ✓ index.html 업데이트")


def add_readme_row(slug: str, title: str, desc: str):
    text = README.read_text(encoding="utf-8")
    if f"]({slug}.html)" in text:
        print(f"  README에 이미 {slug} 줄 있음, 스킵")
        return
    # 마지막 게임 행 다음에 추가
    lines = text.splitlines()
    # 표 마지막 행 찾기
    last_table_idx = -1
    for i, line in enumerate(lines):
        if line.startswith("|") and "](" in line and ".html)" in line:
            last_table_idx = i
    if last_table_idx == -1:
        print("  README 표 못 찾음, 스킵")
        return
    # 다음 번호 계산
    num = sum(1 for line in lines if line.startswith("|") and re.match(r"\| \d+", line)) + 1
    new_row = f"| {num} | {title} | {desc} | [▶]({slug}.html) |"
    lines.insert(last_table_idx + 1, new_row)
    README.write_text("\n".join(lines) + ("\n" if not text.endswith("\n") else ""), encoding="utf-8")
    print(f"  ✓ README.md 업데이트")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source", help="drive:<file_id> 또는 로컬 HTML 경로")
    ap.add_argument("title", help="게임 제목 (한국어)")
    ap.add_argument("--emoji", default="🎮", help="제목 옆 이모지")
    ap.add_argument("--desc", required=True, help="한 줄 설명")
    ap.add_argument("--controls", default="좌우 / 스페이스 / 마우스 · 모바일 터치", help="조작 안내")
    ap.add_argument("--slug", required=True, help="파일명 (영문 소문자, 하이픈/언더스코어)")
    ap.add_argument("--no-push", action="store_true", help="git push 스킵 (로컬 테스트용)")
    args = ap.parse_args()

    target = REPO / f"{args.slug}.html"
    if target.exists():
        sys.exit(f"!! {target.name} 이미 있음. 다른 slug 쓰거나 먼저 지워.")

    # 다운로드 / 복사
    if args.source.startswith("drive:"):
        fid = args.source.split(":", 1)[1]
        print(f"  Drive에서 받기: {fid}")
        data = fetch_drive(fid)
        target.write_bytes(data)
        print(f"  ✓ {target.name} ({len(data)//1024} KB)")
    else:
        src = Path(args.source).expanduser().resolve()
        if not src.exists():
            sys.exit(f"!! 파일 없음: {src}")
        shutil.copy(src, target)
        print(f"  ✓ {target.name} 복사 ({target.stat().st_size//1024} KB)")

    # index.html / README 업데이트
    add_card(args.slug, args.title, args.emoji, args.desc, args.controls)
    add_readme_row(args.slug, args.title, args.desc)

    # git
    subprocess.run(["git", "-C", str(REPO), "add", target.name, "index.html", "README.md"], check=True)
    msg = f"Add: {args.title} ({args.slug})"
    subprocess.run(["git", "-C", str(REPO), "commit", "-m", msg], check=True)
    print(f"  ✓ commit: {msg}")
    if not args.no_push:
        subprocess.run(["git", "-C", str(REPO), "push"], check=True)
        print(f"  ✓ push 완료")
        print(f"\n🎮 라이브 (1~2분 후): https://manzojunior.github.io/bitegames/{args.slug}.html")
    else:
        print("  (push 스킵)")


if __name__ == "__main__":
    main()
