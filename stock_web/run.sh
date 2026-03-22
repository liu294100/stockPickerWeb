#!/usr/bin/env bash
set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

PYTHON_CANDIDATES=()

add_python() {
  local candidate="$1"
  [ -z "$candidate" ] && return
  [ ! -x "$candidate" ] && return
  for existing in "${PYTHON_CANDIDATES[@]}"; do
    [ "$existing" = "$candidate" ] && return
  done
  PYTHON_CANDIDATES+=("$candidate")
}

for name in python3 python; do
  if command -v "$name" >/dev/null 2>&1; then
    add_python "$(command -v "$name")"
  fi
done

for path in /usr/bin/python3 /usr/local/bin/python3 /opt/homebrew/bin/python3; do
  [ -x "$path" ] && add_python "$path"
done

count=${#PYTHON_CANDIDATES[@]}
if [ "$count" -eq 0 ]; then
  echo "未检测到可用 Python 环境。"
  echo "请先安装 Python 3.10 及以上版本，再重新运行本脚本。"
  echo "下载地址: https://www.python.org/downloads/"
  exit 1
fi

if [ "$count" -eq 1 ]; then
  PYTHON_EXE="${PYTHON_CANDIDATES[0]}"
else
  echo "检测到多个 Python，请输入数字选择："
  i=1
  for p in "${PYTHON_CANDIDATES[@]}"; do
    echo "  $i. $p"
    i=$((i + 1))
  done
  while true; do
    read -r -p "请输入序号并回车: " pick
    if [[ "$pick" =~ ^[0-9]+$ ]] && [ "$pick" -ge 1 ] && [ "$pick" -le "$count" ]; then
      PYTHON_EXE="${PYTHON_CANDIDATES[$((pick - 1))]}"
      break
    fi
  done
fi

echo "已选择: $PYTHON_EXE"
"$PYTHON_EXE" --version

if [ ! -f requirements.txt ]; then
  echo "未找到 requirements.txt，无法自动安装依赖。"
  exit 1
fi

echo "正在检查并安装依赖..."
if ! "$PYTHON_EXE" -m pip --version >/dev/null 2>&1; then
  "$PYTHON_EXE" -m ensurepip --upgrade >/dev/null 2>&1 || true
fi
"$PYTHON_EXE" -m pip install -r requirements.txt

echo "依赖就绪，正在启动应用..."
"$PYTHON_EXE" app.py
