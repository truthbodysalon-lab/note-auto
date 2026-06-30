#!/usr/bin/env python3
"""クラウド用 マーケ記事生成（Gemini API・無料枠）
環境変数: GEMINI_API_KEY
出力: ARTICLE_DIR/mk_<日付>_01.md
"""
import os, json, time, datetime, urllib.request, glob

API_KEY = os.environ["GEMINI_API_KEY"]
MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
ARTICLE_DIR = os.environ.get("ARTICLE_DIR", "articles/consul")
os.makedirs(ARTICLE_DIR, exist_ok=True)
DATE = os.environ.get("DATE_STR") or datetime.date.today().strftime("%Y-%m-%d")
OUT = f"{ARTICLE_DIR}/mk_{DATE}_01.md"
if os.path.exists(OUT):
    print(f"既存: {OUT} スキップ"); raise SystemExit

recent = []
for f in sorted(glob.glob(f"{ARTICLE_DIR}/mk_*.md"))[-15:]:
    try: recent.append(open(f, encoding="utf-8").readline().strip())
    except: pass

PROMPT = f"""あなたは整体師・サロン経営者向けのマーケティングnote有料記事の専門ライターです。
整体院トゥルース院長（新潟県長岡市・Google4.9・改善率93.7%・年間250人）の実体験を語る形で、経営者向けの記事を1本書いてください。

【読者】月商100万前後で停滞する整体師・サロン経営者
【テーマ候補】継続コース設計/リピート率向上/高単価化/オファー設計/MEO・Googleマップ集客/SNS導線/紹介の仕組み化/ホットペッパー脱依存/価格設計/時間設計 から1つ
【重複回避】直近タイトル: {recent}
【売れるタイトルの型(必ず踏襲)】「{{読者が言いたい変化後のセリフ}}」——{{対象者}}が{{具体的手段}}で{{達成した結果}}にした完全手順
  例: 「広告費ゼロで新規が来た」——整体師がGoogleマップをたった5つの設定で地域No.1にした完全手順
【構成(UCCHAN型・全文無料)】# タイトル → ##共感導入(あるある) → ##院長の体験・気づき → ##第1章〜第5章(仕組み/手順/数字/テンプレ/ロードマップ) → ##あなたへの問い → 固定CTA
  ※「ここから有料」等の有料分離マーカーは入れない(全文無料)
【固定CTA】末尾に必ず:
「集客の何から手をつければいいかわからない」「自分の投稿の何がズレているか見てほしい」そんな方は、公式LINEから気軽に相談してください。個別で一緒に整理します。👇 公式LINEはこちら（無料相談受付中）https://lin.ee/GwQ0FSx 友だち追加後、「note読みました」とメッセージをください。
【追加リンク】CTA後に: 🌐公式HP https://body-salon-truth.com/ ／ 🗓ご予約 https://beauty.hotpepper.jp/kr/slnH000596246/?vos=cpahpbprosmaf131118005
【スタイル】ストーリー型・対話型。「あなた」「先生」への語りかけ。具体的数字・事例・テンプレ。誇大表現NG。
【文字数】4500〜6500字
Markdown本文のみ出力。前置き不要。冒頭は必ず「# 」で始めること。"""

url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}"
payload = {"contents":[{"parts":[{"text":PROMPT}]}], "generationConfig":{"temperature":0.9,"maxOutputTokens":16384,"thinkingConfig":{"thinkingBudget":0}}}
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
