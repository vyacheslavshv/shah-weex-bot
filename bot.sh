#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"
PIDFILE="$DIR/.pid"
VENV="$DIR/.venv"
PYTHON="$VENV/bin/python"
PIP="$VENV/bin/pip"

case "$1" in
  start)
    if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
      echo "Bot is already running (PID $(cat "$PIDFILE"))"
      exit 1
    fi
    mkdir -p "$DIR/logs" "$DIR/data"
    nohup "$PYTHON" "$DIR/main.py" > /dev/null 2>&1 &
    echo $! > "$PIDFILE"
    echo "Bot started (PID $!)"
    ;;
  stop)
    if [ ! -f "$PIDFILE" ] || ! kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
      echo "Bot is not running"
      rm -f "$PIDFILE"
      exit 0
    fi
    kill "$(cat "$PIDFILE")"
    rm -f "$PIDFILE"
    echo "Bot stopped"
    ;;
  restart)
    "$0" stop
    sleep 1
    "$0" start
    ;;
  update)
    "$0" stop
    git -C "$DIR" pull
    "$PIP" install -r "$DIR/requirements.txt" --quiet
    cd "$DIR" && "$VENV/bin/aerich" upgrade 2>/dev/null
    "$0" start
    echo "Update complete"
    ;;
  logs)
    tail -f "$DIR/logs/bot.log"
    ;;
  status)
    if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
      echo "Bot is running (PID $(cat "$PIDFILE"))"
    else
      echo "Bot is not running"
      rm -f "$PIDFILE" 2>/dev/null
    fi
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|update|logs|status}"
    ;;
esac
