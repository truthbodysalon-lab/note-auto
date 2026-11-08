#!/usr/bin/env python3
"""クラウド用 マーケ記事生成（Gemini API・無料枠。全滅した日はMacがCodexで代行＝LLM_BACKEND=codex）
環境変数: GEMINI_API_KEY（Geminiのとき）
出力: ARTICLE_DIR/mk_<日付>_01.md
"""
import os, re, json, time, datetime, glob
import llm_backend

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

# AI回の2回に1回は AI×Office回（2026-11-08 masa指示「AIを活用してExcelやWord、PowerPointなどの活用法も記事として販売できるように」）。
# 直前のAI回のタイトルにOffice名が無ければ今回はOffice回。道具は直前のOffice回と変える（Excel→Word→PowerPoint）
OFFICE = {"Excel": r"Excel|エクセル", "Word": r"Word|ワード", "PowerPoint": r"PowerPoint|パワポ|パワーポイント"}
OFFICE_TOPIC = {
    "Excel": "売上・新規客・来院数・広告費の表づくり、関数（SUMIFS・COUNTIFS・XLOOKUPなど）やピボットテーブルをAIに書かせる、月次の数字をAIに読ませて打ち手を出す",
    "Word": "お客様への案内文・同意書・スタッフ向けマニュアル・チラシ原稿をAIで下書きし、Wordの見出しスタイルや目次で整える",
    "PowerPoint": "セミナー資料・求人説明・提携先への提案資料をAIで構成（スライドごとの見出しと要点）し、PowerPointのアウトライン表示に貼って仕上げる",
}
if AI_RULE:
    _ai = [t for t in (open(f, encoding="utf-8").readline() for f in sorted(glob.glob(f"{ARTICLE_DIR}/mk_*.md"))[-15:]) if "AI" in t]
    _off = [k for t in _ai for k, p in OFFICE.items() if re.search(p, t)]
    if not (_ai and _off and re.search(OFFICE[_off[-1]], _ai[-1])):
        _keys = list(OFFICE)
        _tool = _keys[(_keys.index(_off[-1]) + 1) % 3] if _off else "Excel"
        AI_RULE = (f"\n【今回はAI×{_tool}回】テーマは「AIで{_tool}を使いこなす店舗経営」。内容の例: {OFFICE_TOPIC[_tool]}（テーマ候補より優先）。"
                   f"タイトルに必ず「AI」と「{_tool}」を含める。読者はパソコンが得意ではない店舗経営者。{_tool}の画面の操作は番号付き手順で書き、"
                   "AIへの頼み方はコピペできるプロンプトを最低3本＋よくある失敗3つを入れる。関数名・機能名・メニュー名は実在するものだけを書き、"
                   "版（Microsoft 365・買い切り版など）で表示や有無が違うものはそう書く。お客様の氏名・電話番号などの個人情報をAIに貼らない注意を必ず入れる。ツール料金は書かない。")
        print(f"AI×{_tool}回")
# AI回は効果の数字を作らない（2026-11-08 試作で「業務時間を半分以下にできた」と根拠のない数字がタイトル・本文に出たため）
IS_AI = bool(AI_RULE)
if IS_AI:
    AI_RULE += ("\n【効果の数字は書かない】「業務時間が半分」「○倍」「○%削減」「○時間短縮」「月商○万円達成」のような、AIを使った効果の数字はタイトルにも本文にも書かない（裏づけの資料が無いため）。"
                "書いてよい数字は、手順の数・プロンプトの本数・日数・表の列の数など、記事の中で事実として言えるものだけ。効果は「下書きの手間が減った」「迷う時間が減った」のように数字なしで書く。")
EFFECT = re.compile(r"半分|[0-9０-９]+(?:\.[0-9]+)?\s*(?:倍|割|%|％)|[0-9０-９]+\s*時間(?:を|の)?(?:短縮|削減|浮)|(?:短縮|削減)(?:し|でき)|月商\s*[0-9０-９]+\s*万")
# 本文は「効果を言っている」行だけを見る（Excelの表の「達成率80%」などの例は直さない）
EFFECT_BODY = re.compile(r"(?:半分|[0-9０-９]+(?:\.[0-9]+)?\s*(?:倍|割|%|％))[^。\n]{0,15}(?:削減|短縮|減っ|減ら|増え|アップ|伸び|上が|速く|早く|楽に|になり|になっ|にでき|でき)|[0-9０-９]+\s*時間(?:を|の|も)?(?:短縮|削減|浮)")
# 関西弁（2026-11-08 試作で「〜やん」「〜怖いんやろ？」が出た。【スタイル】の指示だけでは防げなかった）
KANSAI = re.compile(r"やんか|やん[。」！？!?、]|やろ[。」？！?!]|(?<!大)へん[。」]|ねん[。」！？]|せやから|せやけど|あかん|ほんま")
PROMPT = f"""あなたは整体師・サロン経営者向けのマーケティングnote有料記事の専門ライターです。
整体院を経営しながら発信を続けてきた立場から、経営者向けの記事を1本書いてください。
【店舗情報の禁止】店名・屋号・地名の名乗り・住所・電話・公式HP・予約URL・来院誘導は本文・見出し・CTAすべてで一切書かない（自己紹介は「整体院を経営しながら発信を続けてきた立場から」程度に留め、地域名は一般論の例示のみ）。事例は「ある整体院」と匿名にする。{AI_RULE}

【読者】月商100万前後で停滞する整体師・サロン経営者
【テーマ候補】継続コース設計/リピート率向上/高単価化/オファー設計/MEO・Googleマップ集客/SNS導線/紹介の仕組み化/ホットペッパー脱依存/価格設計/時間設計 から1つ
【重複回避】直近タイトル（テーマの重複確認用。タイトルの書き方は真似しない）: {recent}
{TITLE_RULE}
【構成(UCCHAN型・全文無料)】# タイトル → ##共感導入(あるある) → ##院長の体験・気づき → ##第1章〜第5章(仕組み/手順/数字/テンプレ/ロードマップ) → ##あなたへの問い → 固定CTA
  ※「ここから有料」等の有料分離マーカーは入れない(全文無料)
【固定CTA】末尾に必ず:
「集客の何から手をつければいいかわからない」「自分の投稿の何がズレているか見てほしい」そんな方は、公式LINEから気軽に相談してください。個別で一緒に整理します。👇 公式LINEはこちら（無料相談受付中）https://lin.ee/GwQ0FSx 友だち追加後、「note読みました」とメッセージをください。
【テキストのご提案】固定CTAの後に必ず次のブロックを入れる（2026-11-07 masa指示「購入者には提案という形で」）。煽り・期限・「今だけ」・残り枠などの押し売りの言い方は足さない。先頭に、この記事の内容から自然につなぐ一文を1行だけ足してよい。金額とURLは変えない:
---
📖 ここまで読んでくださったあなたへのご提案
この記事でお伝えした考え方を、集客・SNS・リピート・価格設計まで通して学べる実践テキストにまとめています。
「自分の院でも一通り設計し直したい」と思った方にだけ、ご提案させてください。
通常15万円のテキストを、note読者の方は49,800円（税込）でお求めいただけます。
▶ 詳細・お申し込み https://square.link/u/JIiymU1c
無理におすすめはしません。まずは公式LINEで相談してから決めていただいても大丈夫です。
【追加リンク】公式HP・予約URLは書かない（マーケ記事は店舗導線を載せない）。
【書籍案内】追加リンクの後に必ず次のブロックを入れる:
📘 書籍も発売中『マンガでわかる店舗集客』シリーズ（Kindle）
クーポン集客・リピート改善のノウハウを、店舗オーナーとコンサルタントの対話マンガで解説しています。
▶ Amazonで「マンガでわかる店舗集客」と検索、または https://www.amazon.co.jp/s?k=%E3%83%9E%E3%83%B3%E3%82%AC%E3%81%A7%E3%82%8F%E3%81%8B%E3%82%8B%E5%BA%97%E8%88%97%E9%9B%86%E5%AE%A2
【スタイル】ストーリー型・対話型。「あなた」「先生」への語りかけ。具体的数字・事例・テンプレ。誇大表現NG。
【文字数】4500〜6500字
Markdown本文のみ出力。前置き不要。冒頭は必ず「# 」で始めること。"""

MODELS = [MODEL] + [m for m in ("gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.8-flash", "gemini-3.7-flash", "gemini-2.5-flash") if m != MODEL]

# 2026-11-07: 指示だけでは直近タイトル（全部「もう〜」型）を真似して型が残ったため、生成後に機械で検査する。
# 型が残っていたらタイトルだけ作り直す。作り直しに失敗しても記事は止めない
BAD_TITLE = re.compile(r"月商100万で停滞する整体師が|^「もう|完全手順$")

def fix_title(text):
    head, _, rest = text.partition("\n")
    title = head.lstrip("#").strip()
    bad = lambda s: bool(BAD_TITLE.search(s)) or (IS_AI and bool(EFFECT.search(s))) or bool(KANSAI.search(s))
    if not bad(title) and len(title) <= 50:
        return text
    _tools = [p for p in OFFICE.values() if re.search(p, title)]  # Office名は次回の回し方の判定キーなので落とさない
    ok = lambda s: bool(s) and not bad(s) and 10 <= len(s) <= 60 and ("AI" not in title or "AI" in s) and all(re.search(p, s) for p in _tools)
    ask = f"""次のnote記事（整体師・サロン経営者向けマーケティング）のタイトルを1本だけ作り直してください。
今のタイトル: {title}
本文の冒頭:
{rest[:1500]}
条件: 30〜45字。「もう〜」で始めない。「月商100万で停滞する整体師が」「完全手順」は使わない。具体的な数字／院長の一人称の体験（例: なぜ私の整体院は〜のか）／思い込みをひっくり返す一言（例: 〜は思い込みだった）のどれかを入れる。店名・地名は入れない。誇大表現NG。関西弁は使わない。{"必ず「AI」を含める。" if "AI" in title else ""}{"効果の数字（半分・○倍・○%削減・○時間短縮など）は入れず、手順の数や日数など事実として言える数字にする。" if IS_AI else ""}{"".join(f"「{k}」をそのまま含める。" for k, p in OFFICE.items() if re.search(p, title))}
タイトルの文字列だけを1行で出力。"""
    new = (llm_backend.ask_short(ask, MODELS) or "").lstrip("#").strip().strip("\"'*` ")
    if ok(new):
        print(f"タイトル作り直し: {title} → {new}")
        return f"# {new}\n{rest}"
    # 作り直せない時は「——」より前が条件を満たせばそこだけ残す
    front = title.split("——")[0].strip()
    if front != title and ok(front):
        print(f"タイトルを前半だけに短縮: {title} → {front}")
        return f"# {front}\n{rest}"
    print(f"タイトル作り直しできず（元のまま保存）: {new[:40]}")
    return text

def check(text):
    if not text.startswith("#") and "# " in text:
        text = text[text.find("# "):]
    if len(text) < 1500:
        raise ValueError(f"出力が短すぎる({len(text)}字)")
    return text

try:
    text, used = llm_backend.generate(PROMPT, MODELS, check)
except RuntimeError as e:
    raise SystemExit(f"生成失敗: {e}")
text = fix_title(text)

def fix_lines(text, pattern, how, limit=12):
    """本文で pattern に当たる行（段落）だけを書き直す。直せない行は元のまま（記事は止めない）"""
    lines = text.split("\n")
    hits = [i for i, l in enumerate(lines) if i > 0 and pattern.search(l)][:limit]
    for i in hits:
        old = lines[i]
        new = (llm_backend.ask_short(f"次の1段落を書き直してください。{how}意味・Markdownの記号（**・> ・番号など）・語りかけの調子は保つ。書き直した段落だけを1行で出力。\n{old}", MODELS, max_tokens=800) or "").strip()
        if new and not pattern.search(new) and 0.5 * len(old) <= len(new) <= 1.6 * len(old) + 20:
            lines[i] = new
            print(f"書き直し: {old[:30]}… → {new[:30]}…")
        else:
            print(f"書き直しできず（元のまま）: {old[:40]}")
    return "\n".join(lines)

text = fix_lines(text, KANSAI, "関西弁をやめて、丁寧な標準語（です・ます調、くだけた会話文は標準語の話し言葉）にする。")
if IS_AI:
    text = fix_lines(text, EFFECT_BODY, "AIを使った効果の数字（半分・○倍・○%削減・○時間短縮・月商○万円など）を消し、数字なしの言い方（「手間が減った」「迷う時間が減った」など）にする。手順の数・日数など事実の数字は残してよい。")

# テキストのご提案を書き忘れた日は、書籍案内の前（無ければ末尾）に定型で差し込む
OFFER_URL = "https://square.link/u/JIiymU1c"
if OFFER_URL not in text:
    offer = ("\n---\n📖 ここまで読んでくださったあなたへのご提案\n"
             "この記事でお伝えした考え方を、集客・SNS・リピート・価格設計まで通して学べる実践テキストにまとめています。\n"
             "「自分の院でも一通り設計し直したい」と思った方にだけ、ご提案させてください。\n"
             "通常15万円のテキストを、note読者の方は49,800円（税込）でお求めいただけます。\n"
             f"▶ 詳細・お申し込み {OFFER_URL}\n"
             "無理におすすめはしません。まずは公式LINEで相談してから決めていただいても大丈夫です。\n\n")
    i = text.find("📘")
    text = text[:i] + offer + text[i:] if i >= 0 else text.rstrip() + "\n" + offer
    print("テキストのご提案が無かったので差し込み")
open(OUT, "w", encoding="utf-8").write(text)
print(f"生成完了: {OUT} ({len(text)}字・model={used})")
