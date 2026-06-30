#!/bin/zsh
# Mac側：クラウド生成記事を取得→noteに投稿。
# 【自己修復ルール】セッション切れを検知したらLINE通知＋記事は保持（次回ログイン後に自動投稿）。
export LANG=ja_JP.UTF-8 LC_ALL=ja_JP.UTF-8
export PATH=/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin:$PATH
KIT=/Users/mt112/note-cloud-kit
NA=/Users/mt112/.note-auto
LOG=$KIT/post_local.log
LINE=/Users/mt112/.claude/scripts/line-push-masahide.sh
echo "" >> $LOG
echo "=== $(date '+%F %T') Mac投稿 ===" >> $LOG

# 1) クラウド生成の最新記事を取得（クラウドを正として強制同期）
cd $KIT && git fetch origin >> $LOG 2>&1 && git reset --hard origin/main >> $LOG 2>&1

# 2) アカウントごとに「生死チェック→生きてれば投稿／切れてれば通知して保持」
post_one () {
  local label=$1 glob=$2 jp=$3
  if /usr/bin/python3 $NA/session_alive.py $label >/dev/null 2>&1; then
    # セッション生存→投稿（溜まった記事も自動で追いつく。dedupで二重投稿なし）
    /usr/bin/python3 $NA/upload.py \
      $NA/profiles/$label "$KIT/articles/$label" "$glob" \
      "$KIT/uploaded_${label}_local.json" $label >> $LOG 2>&1
    rm -f $NA/.dead_$label   # 復活したらフラグ解除（次に切れたら再通知できる）
  else
    # セッション切れ→記事は保持（投稿しない）。切れた瞬間1回だけLINE通知
    echo "[$label] ⚠️セッション切れ→投稿スキップ（記事は保持）" >> $LOG
    if [ ! -f $NA/.dead_$label ]; then
      printf '⚠️ note（%s）のログインが切れました。\n\nデスクトップの「noteログイン.command」をダブルクリックして再ログインしてください。\n\n生成済みの記事は溜めてあるので、ログインすれば次回自動で投稿されます（記事は失われません）。' "$jp" | $LINE >> $LOG 2>&1
      touch $NA/.dead_$label
    fi
  fi
}

post_one seitai "note_*.md" "整体・まぁ"
post_one consul "mk_*.md" "コンサル・高橋雅英"

echo "=== 完了 ===" >> $LOG
