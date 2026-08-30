#!/bin/zsh
# 整体note：クラウド生成の無料記事を毎朝10時までに【公開】する。
# 【自己修復】セッション切れ検知→LINE通知＋記事保持（ログイン後に自動公開）。
export LANG=ja_JP.UTF-8 LC_ALL=ja_JP.UTF-8
export PATH=/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin:$PATH
KIT=/Users/mt112/note-cloud-kit
NA=/Users/mt112/.note-auto
LOG=$KIT/publish_seitai.log
LINE=/Users/mt112/.claude/scripts/line-push-masahide.sh
echo "" >> $LOG
echo "=== $(date '+%F %T') 整体・自動公開 ===" >> $LOG

# 1) クラウド生成の最新記事を取得
cd $KIT && git fetch origin >> $LOG 2>&1 && git reset --hard origin/main >> $LOG 2>&1

# 2) セッション生死→生きてれば【公開】、切れてれば通知して保持
if /usr/bin/python3 $NA/session_alive.py seitai >/dev/null 2>&1; then
  /usr/bin/python3 $NA/publish.py \
    $NA/profiles/seitai "$KIT/articles/seitai" "note_*.md" \
    "$KIT/uploaded_seitai_local.json" seitai >> $LOG 2>&1
  rm -f $NA/.dead_seitai
else
  echo "[seitai] ⚠️セッション切れ→公開スキップ（記事は保持）" >> $LOG
  need_notify=0
  if [ ! -f $NA/.dead_seitai ]; then
    need_notify=1
  elif [ -n "$(find $NA/.dead_seitai -mtime +3 2>/dev/null)" ]; then
    need_notify=1
  fi
  if [ $need_notify -eq 1 ]; then
    printf '⚠️ note（整体・まぁ）のログインが切れて、毎朝の自動公開が止まっています。\n\nデスクトップの「noteログイン.command」をダブルクリックして再ログインしてください。ログイン後に溜まった記事を自動公開します。\n\n記事は失われません。放置中は3日ごとに再通知します。' | $LINE >> $LOG 2>&1
    touch $NA/.dead_seitai
  fi
fi
echo "=== 完了 ===" >> $LOG
