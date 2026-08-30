#!/bin/zsh
# 整体note：【画像付きの下書き】を古い順に毎朝1本だけ【公開】する（新規作成はしない）。
# 作成(テキスト下書き)は post_local.sh 側。ここは「あなたが画像を付けた下書き＝公開OK」を公開する。
# 【自己修復】セッション切れ検知→LINE通知＋保持（ログイン後に自動公開）。1日1本のみ。
export LANG=ja_JP.UTF-8 LC_ALL=ja_JP.UTF-8
export PATH=/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin:$PATH
NA=/Users/mt112/.note-auto
LOG=/Users/mt112/note-cloud-kit/publish_seitai.log
LINE=/Users/mt112/.claude/scripts/line-push-masahide.sh
echo "" >> $LOG
echo "=== $(date '+%F %T') 整体・画像付き下書きを1本公開 ===" >> $LOG

# 古いフラグ掃除
find $NA -name '.pub_done_seitai_*' -mtime +7 -delete 2>/dev/null

# 本日すでに1本公開していればスキップ（1日1本）
FLAG=$NA/.pub_done_seitai_$(date +%Y%m%d)
if [ -f "$FLAG" ]; then
  echo "[seitai] 本日は公開済み。スキップ" >> $LOG
  echo "=== 完了 ===" >> $LOG
  exit 0
fi

if /usr/bin/python3 $NA/session_alive.py seitai >/dev/null 2>&1; then
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
  echo "[seitai] ⚠️セッション切れ→スキップ（記事は保持）" >> $LOG
  need_notify=0
  if [ ! -f $NA/.dead_seitai ]; then
    need_notify=1
  elif [ -n "$(find $NA/.dead_seitai -mtime +3 2>/dev/null)" ]; then
    need_notify=1
  fi
  if [ $need_notify -eq 1 ]; then
    printf '⚠️ note（整体・まぁ）のログインが切れて、画像付き下書きの自動公開が止まっています。\n\nデスクトップの「noteログイン.command」をダブルクリックして再ログインしてください。ログイン後、次回の実行で自動公開を再開します。\n\n放置中は3日ごとに再通知します。' | $LINE >> $LOG 2>&1
    touch $NA/.dead_seitai
  fi
fi
echo "=== 完了 ===" >> $LOG
