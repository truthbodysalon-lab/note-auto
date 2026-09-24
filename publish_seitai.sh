#!/bin/zsh
# 整体note：【画像付きの下書き】を古い順に毎朝1本だけ【公開】する（新規作成はしない）。
# 作成(テキスト下書き)は post_local.sh 側。ここは「あなたが画像を付けた下書き＝公開OK」を公開する。
# 【自己修復】①ブラウザ消失は自動で入れ直す ②本当に切れている時だけ通知。1日1本のみ。
#
# 2026-09-24 改修（17日間の停止事故を受けて）:
#  - session_alive.py のエラーを握り潰していたため真の原因(ブラウザ消失)が埋もれた。→ 詳細を必ずログへ。
#  - 通知は notify.sh(Discord) を直接使う（LINEは恒久禁止）。
export LANG=ja_JP.UTF-8 LC_ALL=ja_JP.UTF-8
export PATH=/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin:$PATH
NA=/Users/mt112/.note-auto
LOG=/Users/mt112/note-cloud-kit/publish_seitai.log
NOTIFY=/Users/mt112/.claude/scripts/notify.sh
echo "" >> $LOG
echo "=== $(date '+%F %T') 整体・画像付き下書きを1本公開 ===" >> $LOG

# 0) 自動操作ブラウザの存在を保証（消えていたら自動で入れ直す）
if ! /bin/zsh $NA/ensure_browser.sh "$LOG"; then
  echo "[FATAL] ブラウザ復旧不可のため中止" >> $LOG
  echo "=== 完了 ===" >> $LOG
  exit 0
fi

# 古いフラグ掃除
find $NA -name '.pub_done_seitai_*' -mtime +7 -delete 2>/dev/null

# 本日すでに1本公開していればスキップ（1日1本）
FLAG=$NA/.pub_done_seitai_$(date +%Y%m%d)
if [ -f "$FLAG" ]; then
  echo "[seitai] 本日は公開済み。スキップ" >> $LOG
  echo "=== 完了 ===" >> $LOG
  exit 0
fi

# ★エラーを握り潰さない：例外内容を必ず捕まえてログに残す
SESS_OUT=$(/usr/bin/python3 $NA/session_alive.py seitai 2>&1); SESS_RC=$?
if [ $SESS_RC -eq 0 ]; then
  OUT=$(/usr/bin/python3 $NA/publish_draft.py $NA/profiles/seitai seitai 2>&1)
  code=$?
  echo "$OUT" >> $LOG
  rm -f $NA/.dead_seitai
  if [ $code -eq 0 ]; then
    touch "$FLAG"
    echo "[seitai] ✅本日1本公開 完了" >> $LOG
  elif [ $code -eq 3 ]; then
    echo "[seitai] 画像付き下書きなし＝公開対象なし（待機）" >> $LOG
  else
    echo "[seitai] ⚠️公開失敗→次回リトライ" >> $LOG
  fi
else
  echo "[seitai] ⚠️セッション判定NG rc=$SESS_RC 詳細: ${SESS_OUT}" >> $LOG
  need_notify=0
  if [ ! -f $NA/.dead_seitai ]; then
    need_notify=1
  elif [ -n "$(find $NA/.dead_seitai -mtime +3 2>/dev/null)" ]; then
    need_notify=1
  fi
  if [ $need_notify -eq 1 ]; then
    printf '⚠️ note（整体・まぁ）のログインが切れて、画像付き下書きの自動公開が止まっています。\n\nデスクトップの「noteログイン.command」をダブルクリックして再ログインしてください。ログイン後、次回の実行で自動公開を再開します。\n\n放置中は3日ごとに再通知します。\n\n[診断] %s' "${SESS_OUT:0:150}" | $NOTIFY >> $LOG 2>&1
    touch $NA/.dead_seitai
  fi
fi
echo "=== 完了 ===" >> $LOG
