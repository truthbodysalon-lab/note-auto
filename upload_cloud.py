#!/usr/bin/env python3
"""クラウド用 note投稿（Cookie認証・プロファイル不要）
環境変数:
  NOTE_COOKIES_JSON : Cookie配列のJSON文字列（GitHub Secretから）
  ARTICLE_DIR       : 記事mdのフォルダ
  PATTERN           : 例 'note_*.md'
  UPLOADED_FILE     : 投稿済み記録ファイル（リポジトリにコミットして重複防止）
  LABEL             : ラベル
"""
import os, re, json, time, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

COOKIES = json.loads(os.environ["NOTE_COOKIES_JSON"])
ARTICLE_DIR = os.environ["ARTICLE_DIR"]
PATTERN = os.environ.get("PATTERN", "*.md")
UPLOADED_FILE = os.environ["UPLOADED_FILE"]
LABEL = os.environ.get("LABEL", "note")

uploaded = []
if os.path.exists(UPLOADED_FILE):
    try: uploaded = json.load(open(UPLOADED_FILE, encoding="utf-8"))
    except: uploaded = []

files = sorted([f for f in Path(ARTICLE_DIR).glob(PATTERN) if f.name not in uploaded])
print(f"[{LABEL}] 未投稿:{len(files)} / 済み:{len(uploaded)}")
if not files:
    print(f"[{LABEL}] 新規なし。終了"); sys.exit(0)


def md_to_plain(p):
    c = open(p, encoding="utf-8").read()
    title = ""
    for ln in c.splitlines():
        if ln.startswith("# "):
            title = ln[2:].strip(); break
    out = []
    for ln in c.splitlines():
        if ln.startswith("# ") or ln.startswith("!["): continue
        ln = re.sub(r"^#{1,4}\s+", "", ln)
        ln = re.sub(r"\*\*(.+?)\*\*", r"\1", ln)
        ln = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", ln)
        ln = re.sub(r"^[-*]\s+", "・", ln)
        out.append(ln)
    return title, "\n".join(out).strip()


with sync_playwright() as pw:
    b = pw.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
    ctx = b.new_context(viewport={"width":1280,"height":900},
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")
    ctx.add_cookies(COOKIES)
    page = ctx.new_page()
    page.goto("https://note.com/notes", wait_until="domcontentloaded"); time.sleep(3)
    if "/login" in page.url:
        print(f"❌ [{LABEL}] Cookie失効。ローカルで再エクスポートしてSecret更新が必要"); sys.exit(1)
    print(f"✅ [{LABEL}] ログインOK")
    ok = 0
    for i, md in enumerate(files, 1):
        title, body = md_to_plain(str(md))
        try:
            page.goto("https://note.com/notes/new", wait_until="domcontentloaded"); time.sleep(4)
            page.wait_for_selector('textarea[placeholder*="タイトル"], [data-placeholder*="タイトル"]', timeout=10000)
            page.click('textarea[placeholder*="タイトル"], [data-placeholder*="タイトル"]'); time.sleep(0.3)
            page.keyboard.insert_text(title); time.sleep(0.5)
            page.wait_for_selector('div.ProseMirror, div[contenteditable="true"]:not([data-placeholder*="タイトル"])', timeout=8000)
            page.click('div.ProseMirror, div[contenteditable="true"]:not([data-placeholder*="タイトル"])'); time.sleep(0.3)
            page.keyboard.insert_text(body); time.sleep(2)
            page.keyboard.press("Meta+s"); time.sleep(3)
            if "editor.note.com" in page.url and "/edit" in page.url:
                uploaded.append(md.name); ok += 1; print(f"  [{i:02d}] ✅ {title[:30]}")
            else:
                page.locator('button:has-text("下書き"), button:has-text("保存")').first.click(timeout=3000)
                time.sleep(2); uploaded.append(md.name); ok += 1; print(f"  [{i:02d}] ✅(btn) {title[:26]}")
        except Exception as e:
            print(f"  [{i:02d}] ❌ {title[:22]} {str(e)[:40]}")
        json.dump(uploaded, open(UPLOADED_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        time.sleep(1)
    b.close()
    print(f"[{LABEL}] 完了 成功{ok}/{len(files)}")
