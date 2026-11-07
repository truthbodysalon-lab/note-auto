"""note記事生成の文章AI呼び出し（generate_consul.py / generate_seitai.py 共通）
既定 = Gemini（クラウドのGitHub Actions・無料枠）
LLM_BACKEND=codex = Mac上のCodex（ChatGPTサブスク内・Geminiが無料枠で動かない日の代行。2026-11-07 masa指示）
  Codexは読み取り専用サンドボックス・承認なし・~/.codex/config.toml を読まない（フック・MCP・プラグインを動かさない）
"""
import os, json, time, subprocess, tempfile, urllib.request

BACKEND = os.environ.get("LLM_BACKEND", "gemini")
API_KEY = os.environ.get("GEMINI_API_KEY", "")
CODEX_BIN = os.environ.get("CODEX_BIN", "/opt/homebrew/bin/codex")
CODEX_ARGS = ["exec", "--sandbox", "read-only", "--skip-git-repo-check", "--ephemeral",
              "--ignore-user-config", "--ignore-rules", "--color", "never",
              "-c", 'approval_policy="never"', "-c", 'web_search="disabled"',
              "--disable", "hooks", "--disable", "plugins", "--disable", "apps",
              "--disable", "computer_use", "--disable", "browser_use", "--disable", "image_generation",
              "--disable", "memories", "--disable", "multi_agent",
              "-C", os.path.expanduser("~")]

if BACKEND == "gemini" and not API_KEY:
    raise SystemExit("GEMINI_API_KEY が無い（Codexで書くなら LLM_BACKEND=codex）")


def gemini_once(model, prompt, temperature=0.9, max_tokens=16384, timeout=120):
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens,
                                 "thinkingConfig": {"thinkingBudget": 0}}}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={API_KEY}"
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())["candidates"][0]["content"]["parts"][0]["text"].strip()


def codex_once(prompt, timeout=1200):
    fd, out = tempfile.mkstemp(suffix=".md"); os.close(fd)
    try:
        p = subprocess.run([CODEX_BIN, *CODEX_ARGS, "-o", out, "-"], input=prompt.encode("utf-8"),
                           capture_output=True, timeout=timeout)
        text = open(out, encoding="utf-8").read().strip()
        if p.returncode != 0 or not text:
            raise RuntimeError(f"codex exit={p.returncode} {p.stderr.decode('utf-8', 'ignore')[-200:]}")
        return text
    finally:
        os.unlink(out)


def generate(prompt, models, check, temperature=0.9, max_tokens=16384):
    """check(text) は整形済みの本文を返すか、例外で不合格を知らせる。戻り値 (本文, 使ったモデル名)"""
    if BACKEND == "codex":
        for i in range(2):
            try:
                return check(codex_once(prompt)), "codex"
            except Exception as e:
                print(f"codex 失敗({i + 1}/2): {str(e)[:150]}"); time.sleep(10)
        raise RuntimeError("Codexでも生成失敗")
    # 2026-09-20: 503(高負荷)/429(枠)/404(廃止)はモデル別なので、失敗したら待たずに次のモデルへ。全滅なら60秒置いてもう1周
    for rnd in range(2):
        for m in models:
            try:
                return check(gemini_once(m, prompt, temperature, max_tokens)), m
            except Exception as e:
                print(f"{m} 失敗→次のモデルへ: {str(e)[:100]}"); time.sleep(3)
        if rnd == 0:
            print("全モデル失敗。60秒待って再試行"); time.sleep(60)
    raise RuntimeError("Gemini全モデル失敗（Mac側がCodexで代行する）")


def ask_short(prompt, models, max_tokens=200):
    """タイトル作り直しなど短い依頼。全部だめなら None"""
    if BACKEND == "codex":
        try:
            return codex_once(prompt, timeout=300).splitlines()[0]
        except Exception as e:
            print(f"codex 短文失敗: {str(e)[:100]}"); return None
    for m in models:
        try:
            return gemini_once(m, prompt, 0.8, max_tokens, timeout=60).splitlines()[0]
        except Exception as e:
            print(f"短文失敗({m}): {str(e)[:80]}"); time.sleep(2)
    return None
