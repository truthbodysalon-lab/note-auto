"""アメブロ投稿の品質ゲート（2026-10-26）。gen_ameba_article.py と post.py が共通で使う。

- check_article(text, tp, recents): アメブロ専用記事の検査。OKなら None、NGなら理由の文字列
- check_note(text): noteの記事を代用するときの検査。架空の体験談・改善率・公式と違う実績数字が入っていたらNG
「通った記事だけ投稿する」ための唯一の判定。ここを緩めない。
"""
import re, difflib

# ---- 共通：効果の断定・順位・架空の体験談・公式と違う実績
COMMON_BANNED = [
    r"改善率", r"93\.7", r"満足度", r"1万", r"一万", r"10年", r"年間\d", r"No\.?\s?1", r"ナンバーワン", r"ナンバー1", r"日本一", r"地域一番", r"県内一",
    r"完治", r"根治", r"根本(改善|解決|から)", r"効果(が|は)(あります|期待|出)", r"必ず(?!しも)", r"絶対(に)?(治|良|楽|改善)", r"100\s?%", r"保証", r"奇跡",
    r"お客様の声", r"患者さんの声", r"体験談",
    r"[A-ZＡ-Ｚ]さん", r"[A-ZＡ-Ｚ]様", r"[○〇◯]{1,2}(さん|様)",
    r"\d{2}代の?(男性|女性)の?方?[、,（(][^。\n]{0,14}(在住|会社員|主婦|勤務|パート|さん|様)",
]
# ---- アメブロ専用記事だけ：料金・店舗情報・連絡先は本文に書かない（店舗情報は post.py のフッタが付ける）
ARTICLE_ONLY_BANNED = [
    r"施術後に[「『]", r"と話され", r"と喜ばれ", r"と笑顔で", r"\d{1,3}代の?(男性|女性|方)",
    r"\d[\d,，]*\s?円", r"料金", r"価格", r"割引", r"クーポン", r"初回限定", r"XX",
    r"https?://", r"☎|TEL|電話番号", r"〒",
]

def _num(s):
    return int(re.sub(r"[,，]", "", s))

def number_problem(text):
    """公式と違う実績数字: 人数(100以上)は13,000以外NG／口コミ件数は140以外NG"""
    for m in re.finditer(r"(\d[\d,，]*)\s*[人名]", text):
        try:
            n = _num(m.group(1))
        except ValueError:
            continue
        if n >= 100 and n != 13000:
            return f"公式と違う人数: {m.group(0)}"
    for m in re.finditer(r"口コミ[^\n。]{0,15}?(\d[\d,，]*)\s*件", text):
        if _num(m.group(1)) != 140:
            return f"公式(140件以上)と違う口コミ件数: {m.group(0)[:20]}"
    for m in re.finditer(r"(\d[\d,，]*)\s*件(以上)?の?(口コミ|レビュー|評価)", text):
        if _num(m.group(1)) != 140:
            return f"公式(140件以上)と違う口コミ件数: {m.group(0)[:20]}"
    return None

def title_of(text):
    for l in text.splitlines():
        if l.startswith("# "):
            return l[2:].strip()
    return ""

def _core(title):
    """先頭の【…】を除いた部分（【長岡市】【肩こり】が毎回同じなので、似ている判定から外す）"""
    return re.sub(r"^(【[^】]*】)+", "", title).strip()

def similar_title(title, recents, thr=0.6):
    c = _core(title)
    for t in recents:
        if t == title:
            return t
        if difflib.SequenceMatcher(None, _core(t), c).ratio() >= thr:
            return t
    return None

def _neutral(text):
    """「保証できません」のような、保証を打ち消す正しい注意書きは禁止表現として数えない"""
    return re.sub(r"保証(は)?(でき(ま)?せん|するものではありません|されるものではありません|はいたしません|しておりません)", "", text)

def check_article(text, tp, recents):
    """アメブロ専用記事の検査。OKなら None"""
    if not text.startswith("# "):
        return "1行目が# タイトルでない"
    title = title_of(text)
    if not (22 <= len(title) <= 50):
        return f"タイトルの長さ{len(title)}"
    if "長岡" not in title or not ("肩こり" in title or "頭痛" in title):
        return "タイトルに長岡/肩こり/頭痛がない"
    lines = text.splitlines()
    tag_lines = [l for l in lines if re.match(r"^#[^#\s]", l)]
    if not tag_lines or len(re.findall(r"#[^\s#]+", tag_lines[-1])) < 8:
        return "ハッシュタグが足りない"
    body = "\n".join(l for l in lines[1:] if not re.match(r"^#[^#\s]", l))
    n = len(re.sub(r"\s", "", body))
    if not (2000 <= n <= 3300):
        return f"本文{n}字（2,000〜3,300字の範囲外）"
    if body.count("\n## ") + (1 if body.lstrip().startswith("## ") else 0) < 3:
        return "見出しが3つ未満"
    scan = _neutral(text)
    for pat in COMMON_BANNED + ARTICLE_ONLY_BANNED:
        m = re.search(pat, scan)
        if m:
            return f"禁止表現: {m.group(0)}"
    p = number_problem(text)
    if p:
        return p
    if "個人差" not in text:
        return "『個人差』がない"
    if "医療機関" not in text:
        return "『医療機関』への案内がない"
    if not ("読者登録" in text and "いいね" in text):
        return "読者登録/いいねの誘いがない"
    if tp == "事例":
        if "複数の方" not in text or "個人の感想" not in text:
            return "事例の注記（複数の方/個人の感想）がない"
    s = similar_title(title, recents)
    if s:
        return f"直近または同日のタイトルと重複疑い: {s[:25]}"
    return None

def check_note(text):
    """note記事をアメブロに代用してよいか。OKなら None。
    （noteは字数・構成が別物なので、危ない表現だけを見る）"""
    if not text.startswith("# "):
        return "1行目が# タイトルでない"
    scan = _neutral(text)
    for pat in COMMON_BANNED:
        m = re.search(pat, scan)
        if m:
            return f"禁止表現: {m.group(0)}"
    p = number_problem(text)
    if p:
        return p
    if re.search(r"[（(]\s*\d{2}代[^）)\n]{0,10}[、,][^）)\n]{0,10}在住", text):
        return "架空の患者の紹介（年代・在住）"
    return None
