#!/usr/bin/env python3
"""クラウド用 整体（患者向け健康）記事生成（Gemini API・無料枠）
環境変数: GEMINI_API_KEY
出力: ARTICLE_DIR/note_<日付>_01.md
"""
import os, json, re, time, datetime, urllib.request, glob

API_KEY = os.environ["GEMINI_API_KEY"]
MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
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

# 2026-09-26: 品質問題2件への対策。
# (1) 末尾アクセス情報に「XX」「X分」等の伏せ字プレースホルダが残る事故が多発 → 正式NAPを
#     プロンプトに明記し伏せ字を厳禁。生成後もfix_access_block()で機械的に正式情報へ強制置換。
# (2) タイトルが「放置していませんか？慢性的な肩こり・頭痛と「隠れた○○」：…」で毎日重複 →
#     プロンプトにタイトル型のバリエーションを指定し、直近タイトルとの重複を機械チェックして
#     重複時はモデル切替と同じリトライ経路で再生成させる。

OFFICIAL_NAP = """**アクセス:** 整体院トゥルース
〒940-0072 新潟県長岡市柳原町2-4
**電話:** 0258-94-5898
**営業時間:** 9:00〜22:00（完全予約制）
**定休日:** 不定休
**駐車場:** 1台（柳原郵便局様裏、諸橋パーキングA,B,C）
**商圏:** 長岡市・見附市・小千谷市・三条市・新潟市"""

# アクセス欄に伏せ字・曖昧表現が残っていないかの検出パターン
PLACEHOLDER_PATTERNS = [
    r"XX", r"X分", r"X-X-X", r"某所", r"〇〇", r"○○",
    r"詳細(は|な).{0,12}(ご確認|お伝え|ご覧)", r"具体的な住所は省略", r"省略します",
    r"公式(サイト|HP)をご(確認|覧)ください", r"地図情報", r"住所や地図を記載",
    r"ご予約時にお伝え", r"営業時間.{0,6}\)?：?\s*$", r"\[.*(住所|営業時間).*\]",
]


def fix_access_block(text: str) -> str:
    """アクセス/住所を紹介する段落に伏せ字が見つかったら、正式NAPへ丸ごと置換する。"""
    lines = text.split("\n")
    out = []
    i = 0
    replaced = False
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        is_access_header = (
            ("アクセス" in stripped or "住所" in stripped)
            and (
                stripped.startswith("アクセス") or stripped.startswith("住所")
                or stripped.startswith("**アクセス") or stripped.startswith("**住所")
                or stripped.startswith("【アクセス") or stripped.startswith("[アクセス")
                or re.match(r"^\**(アクセス|住所)\**[:：]", stripped)
            )
        )
        if is_access_header:
            j = i
            block = []
            while j < len(lines) and lines[j].strip() != "" and not lines[j].lstrip().startswith("#"):
                block.append(lines[j])
                j += 1
            block_text = "\n".join(block)
            if any(re.search(p, block_text) for p in PLACEHOLDER_PATTERNS):
                out.extend(OFFICIAL_NAP.split("\n"))
                replaced = True
            else:
                out.extend(block)
            i = j
            continue
        out.append(line)
        i += 1
    result = "\n".join(out)
    if replaced:
        print("アクセス欄の伏せ字プレースホルダを正式NAPに置換しました")
    return result


def title_of(text: str) -> str:
    first = text.split("\n", 1)[0]
    return first.lstrip("#").strip()


def title_prefix(title: str) -> str:
    pre = re.split(r"[：:]", title, maxsplit=1)[0]
    return re.sub(r"[^\w一-龥ぁ-んァ-ン]", "", pre)


def is_title_duplicate(title: str, recent_titles: list) -> bool:
    pre = title_prefix(title)
    if not pre:
        return False
    for r in recent_titles:
        rpre = title_prefix(title_of(r) if r.startswith("#") else r)
        if not rpre:
            continue
        if pre[:14] == rpre[:14]:
            return True
    return False


PROMPT = f"""あなたは整体院トゥルース（新潟県長岡市）の患者向け健康note記事の専門ライターです。
肩こり・頭痛などに悩む30〜50代女性に向けて、体の仕組みとセルフケアを伝える健康記事を1本書いてください。

【院情報】整体院トゥルース（新潟県長岡市）/ Google口コミ4.9・134件 / 改善率93.7% / 年間250人施術
  公式LINE https://lin.ee/GwQ0FSx / 商圏:長岡市・見附市・小千谷市・三条市・新潟市
【正式アクセス情報（末尾で使用・一字一句そのまま。要約・伏せ字化・省略は絶対禁止）】
{OFFICIAL_NAP}
【アクセス表記の絶対NG】「XX」「〇〇」「○○」「X分」「某所」「詳細はご予約時にお伝えします」「公式HPをご確認ください」など、
  住所・電話・営業時間・駐車場を伏せ字や省略にすることは一切禁止。上記の正式アクセス情報を必ずそのまま転記すること。
【テーマ候補】{', '.join(THEMES)} から1つ選ぶ
【重複回避】直近タイトル一覧（この書き出し・言い回しと重複させないこと）: {recent}
  特に「放置していませんか？慢性的な肩こり・頭痛と「隠れた○○」：長岡市の整体師が解説する体の仕組みとセルフケア」という
  書き出しは直近で多用されているため、今回は使わないこと。
【タイトルルール】
  - 「：」より前の部分だけで意味が通じ、単独で50字以内に収まるようにする（アメブロ転載時は「：」前だけを使うため）
  - 「：」の後ろは任意の補足サブタイトルとして使ってよい
  - 主要KW「長岡市」「肩こり」「頭痛」等はタイトル前半に含める
  - 以下のタイトル型から、直近タイトルと異なる型をローテーションで選ぶこと（同じ型・書き出しを連日使わない）:
    1. 疑問形（例:長岡市で肩こりが治らないのはなぜ？）
    2. 数字型（例:長岡市の整体師が教える頭痛を防ぐ3つの習慣）
    3. 症状+地域型（例:長岡市で増えている肩こり、原因は姿勢だけじゃない）
    4. 悩み共感型（例:マッサージしても戻る肩こり、実は自律神経が原因かも）
    5. 断定・逆説型（例:肩こりの原因は肩じゃない、長岡市の整体師が解説）
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
## 整体院トゥルースについて（長岡市・アクセス・商圏。アクセス欄は上記【正式アクセス情報】をそのまま記載）
## 最後に（やさしい問いかけ）
固定CTA
関連リンク
ハッシュタグ（#長岡市 #肩こり #頭痛 など5〜8個）
【固定CTA】必ず末尾に:
「肩こりや頭痛が続いていて、何から始めればいいかわからない」「セルフケアを試しても変わらない、根本から見てほしい」そんな方は、公式LINEから気軽にご相談ください。お体の状態をうかがって、あなたに合った対処をお伝えします。👇 公式LINEはこちら（無料相談受付中）https://lin.ee/GwQ0FSx 友だち追加後、「note読みました」とメッセージをください。
【追加リンク】CTAの後に: 🌐公式HP https://body-salon-truth.com/ ／ 🗓ご予約 https://beauty.hotpepper.jp/kr/slnH000596246/?vos=cpahpbprosmaf131118005
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
            title = title_of(text)
            if is_title_duplicate(title, recent):
                raise ValueError(f"タイトルが直近と重複疑い: {title[:30]}")
            text = fix_access_block(text)
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
