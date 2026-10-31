#!/usr/bin/env python3
"""articles/seitai/note_*.md をアメブロ品質ゲート（tools/ameba_gate.py の check_note）で検査する。
使い方: python3 tools/check_seitai_articles.py  → NGの記事と理由を表示し、NG件数を終了コードにする（0=全件OK）
ameba_gate.py の正本は Mac の ~/.ameba-auto/ameba_gate.py（2026-10-31 コピー）。"""
import glob, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ameba_gate
root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "articles", "seitai")
ng = 0
for f in sorted(glob.glob(os.path.join(root, "note_*.md"))):
    why = ameba_gate.check_note(open(f, encoding="utf-8").read())
    if why:
        ng += 1
        print(f"NG {os.path.basename(f)}: {why}")
print(f"NG {ng}件")
sys.exit(min(ng, 255))
