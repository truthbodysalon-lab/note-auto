#!/bin/zsh
# Mac側：クラウド生成記事を取得→noteに【下書き保存】。
# 【自己修復】①ブラウザ消失は自動で入れ直す ②本当に切れている時だけ通知（原因を取り違えない）
#
# 2026-09-24 改修（17日間の停止事故を受けて）:
#  - session_alive.py のエラーを 2>/dev/null で握り潰していたため、真の原因(ブラウザ消失)が
#    ログに一切残らず「ログイン切れ」と誤通知され続けた。→ 例外内容を必ずログに残す。
#  - 通知は notify.sh(Discord) を直接使う（LINEは恒久禁止）。
export LANG=ja_JP.UTF-8 LC_ALL=ja_JP.UTF-8
export PATH=/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin:$PATH
KIT=/Users/mt112/note-cloud-kit
NA=/Users/mt112/.note-auto
LOG=$KIT/post_local.log
NOTIFY=/Users/mt112/.claude/scripts/notify.sh
echo "" >> $LOG
echo "=== $(date '+%F %T') Mac投稿 ===" >> $LOG

# 0) 自動操作ブラウザの存在を保証（消えていたら自動で入れ直す）
if ! /bin/zsh $NA/ensure_browser.sh "$LOG"; then
  echo "[FATAL] ブラウザ復旧不可のため中止（記事は保持）" >> $LOG
  echo "=== 完了 ===" >> $LOG
  exit 0
fi

# 1) クラウド生成の最新記事を取得（クラウドを正として強制同期）
cd $KIT && git fetch origin >> $LOG 2>&1 && git reset --hard origin/main >> $LOG 2>&1

# 2) アカウントごとに「生死チェック→生きてれば投稿／切れてれば通知して保持」
post_one () {
  local label=$1 glob=$2 jp=$3
  # ★エラーを握り潰さない：例外内容を必ず捕まえてログに残す
  local sess_out sess_rc
  sess_out=$(/usr/bin/python3 $NA/session_alive.py $label 2>&1); sess_rc=$?
  if [ $sess_rc -eq 0 ]; then
    # セッション生存→投稿（溜まった記事も自動で追いつく。dedupで二重投稿なし）
    /usr/bin/python3 $NA/upload.py \
      $NA/profiles/$label "$KIT/articles/$label" "$glob" \
      "$KIT/uploaded_${label}_local.json" $label >> $LOG 2>&1
    rm -f $NA/.dead_$label   # 復活したらフラグ解除（次に切れたら再通知できる）
  else
    # ここに来たら「本当にログインが切れている」ケース。詳細も必ず残す。
    echo "[$label] ⚠️セッション判定NG rc=$sess_rc 詳細: ${sess_out}" >> $LOG
    need_notify=0
    if [ ! -f $NA/.dead_$label ]; then
      need_notify=1
    elif [ -n "$(find $NA/.dead_$label -mtime +3 2>/dev/null)" ]; then
      need_notify=1
      pending=$(ls "$KIT/articles/$label" 2>/dev/null | wc -l | tr -d ' ')
      echo "[$label] 放置3日超（滞留 ${pending}本）→再通知" >> $LOG
    fi
    if [ $need_notify -eq 1 ]; then
      printf '⚠️ note（%s）のログインが切れました。\n\nデスクトップの「noteログイン.command」をダブルクリックして再ログインしてください（完了後、溜まった記事を自動投稿します）。\n\n生成済みの記事は保持しているので失われません。放置中は3日ごとに再通知します。\n\n[診断] %s' "$jp" "${sess_out:0:150}" | $NOTIFY >> $LOG 2>&1
      touch $NA/.dead_$label
    fi
  fi
}

# 整体・コンサルとも「下書き保存」まで（作成は下書きまで）。整体の"公開"は publish_seitai.sh が
# 「画像付き下書きを古い順に1本ずつ」担当（テキスト下書きは画像なし＝公開対象外なので二重公開しない）
post_one seitai "note_*.md" "整体・まぁ"
post_one consul "mk_*.md" "コンサル・高橋雅英"

echo "=== 完了 ===" >> $LOG
