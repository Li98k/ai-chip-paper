#!/bin/bash
# R16 看门狗：至少 5 小时持续驱动 hermes worker 轮次，串行、断点续跑、崩溃自恢复。
cd /home/chiva/AI_video/AI_chip_paper || exit 1
DL=$(cat rounds/DEADLINE_EPOCH)
LOG=rounds/watcher.log
echo "[watcher $$] start $(date -u +%FT%TZ) deadline=$(date -u -d @$DL +%FT%TZ)" >> $LOG
while :; do
  now=$(date +%s)
  [ "$now" -ge "$DL" ] && { echo "[watcher] deadline reached $(date -u +%FT%TZ)" >> $LOG; break; }
  # 已有 worker 在跑？(pgrep 只匹配带 R16W 标记的 hermes 进程)
  busy=$(pgrep -af "hermes" | grep -c "R16W" || true)
  if [ "${busy:-0}" -ge 1 ]; then sleep 60; continue; fi
  # 队列全部完成且已过滚动期？继续滚动优化（不设终止）
  ts=$(date -u +%Y%m%d_%H%M%S)
  echo "[watcher] launch round $ts $(date -u +%FT%TZ)" >> $LOG
  timeout 2400 hermes chat --oneshot -Q --yolo --in /home/chiva/AI_video/AI_chip_paper \
    --continue "R16W-$ts" \
    -q "R16W 自动轮次。阅读 rounds/THREAD_PROMPT.md(铁律与原理主线) 和 rounds/QUEUE.md，领取第一个未勾选 [ ] 任务并完整做完它：产出物落盘、勾选该任务、在 QUEUE.md 末尾追加领取记录、git add -A && git commit -m 'R16-Tn: <一句总结>'。若队列已全部完成则按 QUEUE.md 尾部滚动优化规则做一轮精修。只做一个任务，做完即收尾退出，不要开新任务。" \
    >> "rounds/round_$ts.log" 2>&1
  rc=$?
  echo "[watcher] round $ts exit=$rc $(date -u +%FT%TZ)" >> $LOG
  sleep 30
done
echo "[watcher] exit $(date -u +%FT%TZ)" >> $LOG
