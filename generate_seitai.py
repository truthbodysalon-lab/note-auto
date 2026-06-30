#!/usr/bin/env python3
"""クラウド用 整体（患者向け健康）記事生成（Gemini API・無料枠）
環境変数: GEMINI_API_KEY
出力: ARTICLE_DIR/note_<日付>_01.md
"""
import os, json, time, datetime, urllib.request, glob

API_KEY = os.environ["GEMINI_API_KEY"]
MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
ARTICLE_DIR = os.environ.get("ARTICLE_DIR", "articles/seitai")
os.makedirs(ARTICLE_DIR, exist_ok=True)
DATE = os.environ.get("DATE_STR") or datetime.date.today().strftime("%Y-%m-%d")
OUT = f"{ARTICLE_DIR}/note_{DATE}_01.md"
if os.path.exists(OUT):
    print(f"既存: {OUT} スキップ"); raise SystemExit

recent = []
for f in sorted(glob.glob(f"{ARTICLE_DIR}/note_*.md"))[-15:]:
    try: recent.append(open(f, encoding="utf-8").readline().strip())
    except: pass

THEMES = ["肩こり・首こり","頭痛・天気痛","腰痛・骨盤の歪み","自律神経・睡眠","栄養（鉄/マグネシウム/たんぱく質）",
          "姿勢・スマホ首","冷え性・むくみ","女性の不調（PMS・更年期）","眼精疲労","肩甲骨はがし"]

PROMPT = f"""あなたは整体院トゥルース（新潟県長岡市）の患者向け健康note記事の専門ライターです。
肩こり・頭痛などに悩む30〜50代女性に向けて、体の仕組みとセルフケアを伝える健康記事を1本書いてください。

【院情報】整体院トゥルース（新潟県長岡市）/ Google口コミ4.9・134件 / 改善率93.7% / 年間250人施術
  公式LINE https://lin.ee/GwQ0FSx / 商圏:長岡市・見附市・小千谷市・三条市・新潟市
【テーマ候補】{', '.join(THEMES)} から1つ選ぶ
【重複回避】直近タイトル: {recent}
【絶対NG】経営/集客/月商/単価などビジネス用語、誇大表現（必ず治る・100%等）、「整体院トゥルース」以外の店名表記
【SEO/MEO】タイトル前半に主要症状キーワード、本文に「長岡市」を3回以上自然に、近隣地名を1回、症状の専門用語（僧帽筋・自律神経・トリガーポイント等）を自然に使う
【構成】
# タイトル（症状キーワード＋長岡市の整体師が解説 など）
カテゴリ: ○○（読了目安：約10分）
リード文（検索で来た人の悩みに刺さる2〜3行）
## ○○（共感導入：あるある症状）
### この記事を書いた人（整体院トゥルース院長／Google4.9・改善率93.7%）
## 体験談（匿名の患者さんの変化／例:薬が月10回→2回）
---
## なぜ○○が起こるのか（解剖学・生理学で仕組み解説）
## 自宅でできるセルフケア（3つ以上・手順を具体的に）
## よくある質問（Q&A 3つ）
## 整体院トゥルースについて（長岡市・アクセス・商圏）
## 最後に（やさしい問いかけ）
固定CTA
関連リンク
ハッシュタグ（#長岡市 #肩こり #頭痛 など5〜8個）
【固定CTA】必ず末尾に:
「肩こりや頭痛が続いていて、何から始めればいいかわからない」「セルフケアを試しても変わらない、根本から見てほしい」そんな方は、公式LINEから気軽にご相談ください。お体の状態をうかがって、あなたに合った対処をお伝えします。👇 公式LINEはこちら（無料相談受付中）https://lin.ee/GwQ0FSx 友だち追加後、「note読みました」とメッセージをください。
【追加リンク】CTAの後に: 🌐公式HP https://body-salon-truth.com/ ／ 🗓ご予約 https://beauty.hotpepper.jp/kr/slnH000596246/?vos=cpahpbprosmaf131118005
【文字数】4500〜6500字
Markdown本文のみ出力。前置き不要。冒頭は必ず「# 」で始めること。"""

url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}"
payload = {"contents":[{"parts":[{"text":PROMPT}]}], "generationConfig":{"temperature":0.9,"maxOutputTokens":8192}}
req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type":"application/json"}, method="POST")
for attempt in range(3):
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            d = json.loads(r.read())
        text = d["candidates"][0]["content"]["parts"][0]["text"].strip()
        if not text.startswith("#") and "# " in text:
            text = text[text.find("# "):]
        open(OUT, "w", encoding="utf-8").write(text)
        print(f"生成完了: {OUT} ({len(text)}字)")
        break
    except Exception as e:
        print(f"試行{attempt+1}失敗: {str(e)[:80]}"); time.sleep(10)
else:
    raise SystemExit("生成失敗")
