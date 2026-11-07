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

_titles = []
for f in sorted(glob.glob(f"{ARTICLE_DIR}/mk_*.md"))[-3:]:
    try: _titles.append(open(f, encoding="utf-8").readline())
    except: pass
# 3日に1回AI活用回(2026-09-23 masa指示)。直近3本のタイトルに「AI」が無ければAI回。タイトルに必ず「AI」を入れる＝次回判定キー

# 反応データ（Mac側 tools/note_stats.py が毎日 insights/ に保存）を読み、反応の良い記事を参考にする（2026-11-07 masa指示）
# 無い・14日以上古い時は従来のタイトルの型で書く（生成は止めない）
TITLE_RULE = """【タイトルの付け方】具体的な数字／院長の一人称の体験／思い込みをひっくり返す一言のどれかを入れる。直近タイトルと同じ書き出しは使わない。「もう〜」——月商100万で停滞する整体師が〜完全手順 の型は乱発して反応が落ちたので使わない。
  例: なぜ私の整体院は「7回接触」で予約が止まらなくなったのか／「高いから売れない」は思い込みだった——3万円を10万円に変えたオファー設計"""
try:
    _ins = json.load(open("insights/consul_insights.json", encoding="utf-8"))
    if (datetime.datetime.now() - datetime.datetime.strptime(_ins["updated_at"], "%Y-%m-%d %H:%M")).days > 14:
        raise ValueError("反応データが14日以上古い")
    _fmt = lambda xs: "\n".join(f"  ・{t['title']}（{t['pv']}PV・スキ{t['likes']}）" for t in xs)
    _ov = _ins["overused_pattern"]
    _ex = "\n".join(f"――「{t['title']}」の書き出し――\n{t['excerpt'][:1200]}" for t in _ins["top_models"][:3] if t.get("excerpt"))
    TITLE_RULE = f"""【反応データ（noteの実績・{_ins['all_period']}）】反応の良い記事を参考に書く
手本にする記事（反応が良く、型の乱発に当たらないもの。PV＋スキ×3の順）:
{_fmt(_ins['top_models'])}
よく読まれたテーマ（テーマ選びの参考。タイトルの型は真似しない）:
{_fmt(list({t['key']: t for t in _ins['top_all'][:5] + _ins['top_monthly'][:3]}.values()))}
【使わない型】{_ov['pattern']} は{_ov['count']}本乱発して平均{_ov['avg_score']}点（他の型は平均{_ov['other_avg_score']}点）。この書き出し・この型のタイトルは使わない。
【タイトルの付け方】上の反応が良い記事に共通する要素を使う＝具体的な数字（7回・5つ・90日・3万円→10万円など）／院長の一人称の体験（「なぜ私の整体院は〜のか」）／思い込みをひっくり返す一言（「〜は思い込みだった」）。直近タイトルと同じ書き出しの言葉は使わない。30〜45字。
【書き出しと構成の参考】反応が良い記事の書き出しを下に置く。読者のつぶやきから入る・自分の失敗談を数字つきで語る・気づきの瞬間を描く、という運び方を参考にする。文章や言い回しをそのまま写さない。関西弁は使わない。
{_ex}"""
    print(f"反応データ使用: {_ins['updated_at']}")
except Exception as _e:
    print(f"反応データなし→従来の型で生成: {_e}")

AI_RULE = "" if any("AI" in t for t in _titles) else "\n【今回はAI活用回】テーマは「AIの基礎／実際に動かしている業務効率化／初心者でもできる実践法」から選ぶ(テーマ候補より優先)。タイトルに必ず「AI」を含める。専門用語は初出で言い換え、コピペできるプロンプトを最低3本＋番号付き手順＋よくある失敗3つを入れる。自動化の紹介は匿名で、ツール料金は書かない。"
PROMPT = f"""あなたは整体師・サロン経営者向けのマーケティングnote有料記事の専門ライターです。
整体院を経営しながら発信を続けてきた立場から、経営者向けの記事を1本書いてください。
【店舗情報の禁止】店名・屋号・地名の名乗り・住所・電話・公式HP・予約URL・来院誘導は本文・見出し・CTAすべてで一切書かない（自己紹介は「整体院を経営しながら発信を続けてきた立場から」程度に留め、地域名は一般論の例示のみ）。事例は「ある整体院」と匿名にする。{AI_RULE}

【読者】月商100万前後で停滞する整体師・サロン経営者
【テーマ候補】継続コース設計/リピート率向上/高単価化/オファー設計/MEO・Googleマップ集客/SNS導線/紹介の仕組み化/ホットペッパー脱依存/価格設計/時間設計 から1つ
【重複回避】直近タイトル: {recent}
{TITLE_RULE}
【構成(UCCHAN型・全文無料)】# タイトル → ##共感導入(あるある) → ##院長の体験・気づき → ##第1章〜第5章(仕組み/手順/数字/テンプレ/ロードマップ) → ##あなたへの問い → 固定CTA
  ※「ここから有料」等の有料分離マーカーは入れない(全文無料)
【固定CTA】末尾に必ず:
「集客の何から手をつければいいかわからない」「自分の投稿の何がズレているか見てほしい」そんな方は、公式LINEから気軽に相談してください。個別で一緒に整理します。👇 公式LINEはこちら（無料相談受付中）https://lin.ee/GwQ0FSx 友だち追加後、「note読みました」とメッセージをください。
【追加リンク】公式HP・予約URLは書かない（マーケ記事は店舗導線を載せない）。
【書籍案内】追加リンクの後に必ず次のブロックを入れる:
📘 書籍も発売中『マンガでわかる店舗集客』シリーズ（Kindle）
クーポン集客・リピート改善のノウハウを、店舗オーナーとコンサルタントの対話マンガで解説しています。
▶ Amazonで「マンガでわかる店舗集客」と検索、または https://www.amazon.co.jp/s?k=%E3%83%9E%E3%83%B3%E3%82%AC%E3%81%A7%E3%82%8F%E3%81%8B%E3%82%8B%E5%BA%97%E8%88%97%E9%9B%86%E5%AE%A2
【スタイル】ストーリー型・対話型。「あなた」「先生」への語りかけ。具体的数字・事例・テンプレ。誇大表現NG。
【文字数】4500〜6500字
Markdown本文のみ出力。前置き不要。冒頭は必ず「# 」で始めること。"""

payload = {"contents":[{"parts":[{"text":PROMPT}]}], "generationConfig":{"temperature":0.9,"maxOutputTokens":16384,"thinkingConfig":{"thinkingBudget":0}}}
# 2026-09-20: 1モデル×3回リトライでは 503(高負荷)/429(枠)/404(廃止) の日に記事が出なかった(9/7)。
# 無料枠も負荷もモデル別なので、失敗したら待たずに次のモデルへ切替える。全滅したら60秒置いてもう1周。
MODELS = [MODEL] + [m for m in ("gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.8-flash", "gemini-3.7-flash", "gemini-2.5-flash") if m != MODEL]
done = False
for rnd in range(2):
    for m in MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={API_KEY}"
        req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type":"application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                d = json.loads(r.read())
            text = d["candidates"][0]["content"]["parts"][0]["text"].strip()
            if not text.startswith("#") and "# " in text:
                text = text[text.find("# "):]
            if len(text) < 1500:
                raise ValueError(f"出力が短すぎる({len(text)}字)")
            open(OUT, "w", encoding="utf-8").write(text)
            print(f"生成完了: {OUT} ({len(text)}字・model={m})")
            done = True
            break
        except Exception as e:
            print(f"{m} 失敗→次のモデルへ: {str(e)[:100]}"); time.sleep(3)
    if done:
        break
    print("全モデル失敗。60秒待って再試行"); time.sleep(60)
if not done:
    raise SystemExit("生成失敗")
