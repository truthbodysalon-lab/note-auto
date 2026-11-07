#!/usr/bin/env python3
"""noteコンサル記事の反応データを取得して insights/consul_insights.json に保存する（Mac側）。
クラウドの generate_consul.py がこれを読み、反応の良い記事を参考に次の記事を書く。
ログインは投稿用のブラウザプロファイル（~/.note-auto/profiles/consul）を使う＝Keychain不要。
使い方: /usr/bin/python3 tools/note_stats.py   失敗時は既存ファイルを残して exit 1
"""
import json, os, re, sys, datetime
from playwright.sync_api import sync_playwright

PROFILE = "/Users/mt112/.note-auto/profiles/consul"
KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(KIT, "insights", "consul_insights.json")

# 同じアカウントに整体の健康記事も混ざっているので、マーケ記事だけを拾う
MK_WORDS = ["整体師", "サロン経営", "経営者", "集客", "売上", "院長", "整体院", "SNS", "MEO",
            "Googleマップ", "ホットペッパー", "オファー", "LTV", "リピート", "単価", "価格",
            "マーケ", "AI", "発信", "PASONA", "接触", "フロント", "紹介", "クロージング", "LINE"]
# 直近で乱発して反応が落ちた型（タイトル冒頭のパターン）
OVERUSED = re.compile(r"^「もう.+?」——月商100万で停滞する整体師が")


def is_marketing(title):
    return title != "自己紹介" and any(w in title for w in MK_WORDS)


def score(r):
    # スキはPVより重い反応なので3倍で数える
    return r["read_count"] + 3 * r["like_count"]


def fetch_stats(req, filt):
    rows, page = [], 1
    while page <= 30:
        d = req.get(f"https://note.com/api/v1/stats/pv?filter={filt}&page={page}&sort=pv",
                    timeout=20000).json()["data"]
        rows += d["note_stats"]
        if d.get("last_page"):
            break
        page += 1
    return d["start_date_str"], d["end_date_str"], rows


def slim(r):
    rate = round(r["like_count"] / r["read_count"] * 100, 1) if r["read_count"] else 0.0
    return {"key": r["key"], "title": r["name"].strip(), "pv": r["read_count"],
            "likes": r["like_count"], "like_rate": rate}


def body_excerpt(req, key, limit=1800):
    d = req.get(f"https://note.com/api/v3/notes/{key}", timeout=20000).json().get("data") or {}
    text = re.sub(r"<[^>]+>", "\n", d.get("body") or "")
    text = re.sub(r"\n{2,}", "\n", text).strip()
    return text[:limit]


def main():
    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(PROFILE, headless=True)
        try:
            p = ctx.pages[0] if ctx.pages else ctx.new_page()
            req = p.request
            me = req.get("https://note.com/api/v2/current_user", timeout=20000).json().get("data")
            if not (isinstance(me, dict) and me.get("id")):
                raise RuntimeError("noteのログインが切れている（consulプロファイル）")

            a_start, a_end, all_rows = fetch_stats(req, "all")
            m_start, m_end, mon_rows = fetch_stats(req, "monthly")
            all_mk = sorted([r for r in all_rows if is_marketing(r["name"])], key=score, reverse=True)
            mon_mk = sorted([r for r in mon_rows if is_marketing(r["name"])], key=score, reverse=True)

            over = [r for r in all_mk if OVERUSED.match(r["name"].strip())]
            other = [r for r in all_mk if not OVERUSED.match(r["name"].strip())]
            avg = lambda xs: round(sum(score(x) for x in xs) / len(xs), 1) if xs else 0.0

            top = [slim(r) for r in all_mk[:8]]
            # 手本にする記事は乱発型以外から選ぶ（型そのものは使わせないため）
            models = [slim(r) for r in other[:5]]
            # 本文の抜粋は手本の上位3本（タイトル・書き出し・構成の参考用。コピーさせない）
            for t in models[:3]:
                try:
                    t["excerpt"] = body_excerpt(req, t["key"])
                except Exception as e:
                    t["excerpt"] = ""
                    print(f"本文取得失敗 {t['key']}: {e}", file=sys.stderr)
        finally:
            ctx.close()

    data = {
        "updated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "all_period": f"{a_start}〜{a_end}",
        "monthly_period": f"{m_start}〜{m_end}",
        "score_rule": "PV + スキ×3",
        "top_all": top,
        "top_models": models,
        "top_monthly": [slim(r) for r in mon_mk[:5]],
        "worst_monthly": [slim(r) for r in mon_mk[-5:]] if len(mon_mk) >= 10 else [],
        "overused_pattern": {
            "pattern": "「もう〜」——月商100万で停滞する整体師が〜完全手順",
            "count": len(over), "avg_score": avg(over),
            "other_count": len(other), "other_avg_score": avg(other),
        },
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"保存: {OUT}（上位{len(top)}本・乱発型{len(over)}本 平均{avg(over)} / その他{len(other)}本 平均{avg(other)}）")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[note_stats] 失敗（前回のデータを残す）: {e}", file=sys.stderr)
        sys.exit(1)
