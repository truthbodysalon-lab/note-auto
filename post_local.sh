#!/bin/zsh
# Mac側：クラウドが生成した記事を取得して、ローカルのログインでnoteに投稿する
# （noteはクラウドからの投稿を拒否するため、投稿だけはMac＝あなたのIPで行う）
export LANG=ja_JP.UTF-8 LC_ALL=ja_JP.UTF-8
export PATH=/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin:$PATH
KIT=/Users/mt112/note-cloud-kit
LOG=$KIT/post_local.log
echo "" >> $LOG
echo "=== $(date '+%F %T') Mac投稿 ===" >> $LOG

# 1) クラウドが生成した最新記事を取得（クラウドを正として強制同期）
cd $KIT && git fetch origin >> $LOG 2>&1 && git reset --hard origin/main >> $LOG 2>&1

# 2) ローカルのログイン（profile）でnoteへ投稿（dedupはローカルjson）
/usr/bin/python3 /Users/mt112/.note-auto/upload.py \
  /Users/mt112/.note-auto/profiles/seitai \
  "$KIT/articles/seitai" "note_*.md" \
  "$KIT/uploaded_seitai_local.json" seitai >> $LOG 2>&1

/usr/bin/python3 /Users/mt112/.note-auto/upload.py \
  /Users/mt112/.note-auto/profiles/consul \
  "$KIT/articles/consul" "mk_*.md" \
  "$KIT/uploaded_consul_local.json" consul >> $LOG 2>&1

echo "=== 完了 ===" >> $LOG
