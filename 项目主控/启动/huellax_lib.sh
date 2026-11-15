#!/usr/bin/env bash
# 集成启动器公共库（SQL-first 整栈）。
#
# 在 T5 的 lib.sh 之上增加 B（星表 8799）、C（AnyField 8798，可选）和
# 静态封面（8840），复用同一套 PID/端口/健康/停止逻辑。
# T5 的 start_all/status/stop_all 仍只管理 DB/app/view 三服务。
# shellcheck shell=bash

HUELLAX_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "$HUELLAX_DIR/lib.sh"

# 集成栈开关；解析参数后由 hx_resolve_stack 根据文件是否存在调整。
ENABLE_CATALOG=1
ENABLE_ANYFIELD=1
ENABLE_COVER=1
REQUIRE_ANYFIELD=0
COVER_DIR_REQUESTED="${HUELLAX_COVER_DIR:-}"
COVER_DIR=""
CATALOG_REASON=""
ANYFIELD_REASON=""
COVER_REASON=""

# 整栈状态：core_owned 表示 core 三服务是否由本集成启动器（经 start_all）
# 启动并因此可被 stop_huellax 停止；手工启动的 core 永远不会被误停。
CORE_OWNED=0
CORE_WAS_RUNNING=0
CORE_STARTED_THIS_RUN=0
HX_STARTED_CATALOG=0
HX_STARTED_ANYFIELD=0
HX_STARTED_COVER=0
ROLLBACK_DONE=0
HX_LOCK_HELD=0
HX_STATE=""
HX_LOCK=""
HX_FLAGS=""

# 路径（hx_resolve_stack 填充）
DB_TOOL_DIR="$LAUNCHER_ROOT_DIR/系统/数据库工具"
APP_DIR="$LAUNCHER_ROOT_DIR/系统/app"
VIEW_DIR="$LAUNCHER_ROOT_DIR/系统/视图工具"
ANYFIELD_DIR="$LAUNCHER_ROOT_DIR/系统/anyfield"
CATALOG_SERVER="$DB_TOOL_DIR/catalog_server.py"
ANYFIELD_SERVER="$ANYFIELD_DIR/server.py"
SPHEREX_DB="$DB_TOOL_DIR/var/catalog.sqlite"
STAR_DB="$DB_TOOL_DIR/var/star_catalog.sqlite"

# ------------------------------------------------------------------ 用法/参数

hx_usage() {
  local prog="$1"
  cat <<EOF
Usage: $prog [options]

Start the integrated SQL-first HuellaX stack:
  DB 8797 + MoveScope 8790 + view 8830 (reusing start_all.sh/lib.sh)
  B star catalog 8799 (only when var/star_catalog.sqlite exists)
  C AnyField 8798 (optional; only when 系统/anyfield/server.py exists)
  static cover 8840 (python3 -m http.server, serving the cover root)

Ports (explicit; the launcher never scans or silently changes ports):
  --app-port <port>        MoveScope (default $APP_PORT)
  --db-port <port>         SQLite catalog API (default $DB_PORT)
  --view-port <port>       Sky View static site (default $VIEW_PORT)
  --catalog-port <port>    B star catalog (default $CATALOG_PORT)
  --anyfield-port <port>   C AnyField (default $ANYFIELD_PORT)
  --cover-port <port>      static cover (default $COVER_PORT)

Switches:
  --cover-dir <dir>        cover root to serve (must contain index.html);
                           default: <repo>/cover, <repo>/portada, <repo>/封面,
                           then the committed fallback 项目主控/启动/cover
  --no-catalog             do not start B even if star_catalog.sqlite exists
  --no-anyfield            do not start C
  --no-cover               do not start the 8840 cover
  --require-anyfield       make optional C a required service
  --offline                pass --offline to start_all.sh (app uses cached data)
  -h, --help               show this help

Environment variables (CLI wins):
  LAUNCH_APP_PORT / LAUNCH_DB_PORT / LAUNCH_VIEW_PORT
  LAUNCH_CATALOG_PORT / LAUNCH_ANYFIELD_PORT / LAUNCH_COVER_PORT
  HUELLAX_COVER_DIR
  PYTHON=<interpreter with numpy/Pillow>   (auto-detected when unset)
  LAUNCH_PYTHON=<interpreter for probe.py>

Only PIDs recorded by this launcher family are stopped; foreign processes are
reported, never killed.
EOF
}

hx_need_value() {
  if [ "$#" -lt 2 ] || [ -z "${2:-}" ]; then
    echo "Error: $1 requires a value" >&2
    exit 2
  fi
}

hx_parse_args() {
  local prog="${1:-$(basename "$0")}"
  [ "$#" -gt 0 ] && shift
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --app-port) hx_need_value "$1" "${2:-}"; APP_PORT="$2"; shift 2 ;;
      --app-port=*) APP_PORT="${1#*=}"; shift ;;
      --db-port) hx_need_value "$1" "${2:-}"; DB_PORT="$2"; shift 2 ;;
      --db-port=*) DB_PORT="${1#*=}"; shift ;;
      --view-port) hx_need_value "$1" "${2:-}"; VIEW_PORT="$2"; shift 2 ;;
      --view-port=*) VIEW_PORT="${1#*=}"; shift ;;
      --catalog-port) hx_need_value "$1" "${2:-}"; CATALOG_PORT="$2"; shift 2 ;;
      --catalog-port=*) CATALOG_PORT="${1#*=}"; shift ;;
      --anyfield-port) hx_need_value "$1" "${2:-}"; ANYFIELD_PORT="$2"; shift 2 ;;
      --anyfield-port=*) ANYFIELD_PORT="${1#*=}"; shift ;;
      --cover-port) hx_need_value "$1" "${2:-}"; COVER_PORT="$2"; shift 2 ;;
      --cover-port=*) COVER_PORT="${1#*=}"; shift ;;
      --cover-dir) hx_need_value "$1" "${2:-}"; COVER_DIR_REQUESTED="$2"; shift 2 ;;
      --cover-dir=*) COVER_DIR_REQUESTED="${1#*=}"; shift ;;
      --no-catalog) ENABLE_CATALOG=0; shift ;;
      --no-anyfield) ENABLE_ANYFIELD=0; shift ;;
      --no-cover) ENABLE_COVER=0; shift ;;
      --require-anyfield) REQUIRE_ANYFIELD=1; shift ;;
      --offline) OFFLINE=1; shift ;;
      -h|--help) hx_usage "$prog"; exit 0 ;;
      *)
        echo "Error: unknown argument: $1" >&2
        hx_usage "$prog" >&2
        exit 2
        ;;
    esac
  done
  hx_validate_ports || exit 2
  # 先按 core 三端口决定 RUN_DIR/LOG_DIR；集成脚本与 start_all 共用该目录。
  launcher_init_paths
  HX_STATE="$RUN_DIR/huellax.state"
  HX_LOCK="$RUN_DIR/.huellax.lock"
  HX_FLAGS="$(hx_flags)"
}

hx_validate_ports() {
  local p
  local ports=("$APP_PORT" "$DB_PORT" "$VIEW_PORT" "$CATALOG_PORT" "$ANYFIELD_PORT" "$COVER_PORT")
  local names=(app db view catalog anyfield cover)
  local i j
  for i in "${!ports[@]}"; do
    p="${ports[$i]}"
    if [[ ! "$p" =~ ^[0-9]+$ ]] || (( 10#$p < 1 || 10#$p > 65535 )); then
      echo "Error: ${names[$i]} port must be an integer 1-65535, got '$p'" >&2
      return 1
    fi
    ports[$i]=$((10#$p))
  done
  for ((i = 0; i < ${#ports[@]}; i++)); do
    for ((j = i + 1; j < ${#ports[@]}; j++)); do
      if [ "${ports[$i]}" -eq "${ports[$j]}" ]; then
        echo "Error: ${names[$i]} and ${names[$j]} ports are both ${ports[$i]}" >&2
        return 1
      fi
    done
  done
  APP_PORT="${ports[0]}"
  DB_PORT="${ports[1]}"
  VIEW_PORT="${ports[2]}"
  CATALOG_PORT="${ports[3]}"
  ANYFIELD_PORT="${ports[4]}"
  COVER_PORT="${ports[5]}"
  return 0
}

hx_flags() {
  printf -- '--app-port %s --db-port %s --view-port %s --catalog-port %s --anyfield-port %s --cover-port %s' \
    "$APP_PORT" "$DB_PORT" "$VIEW_PORT" "$CATALOG_PORT" "$ANYFIELD_PORT" "$COVER_PORT"
}

# 本启动器族记录且命令行匹配、且正在监听该端口。
hx_pid_owned() {
  local svc="$1" pid pids
  pid="$(read_pid "$svc" 2>/dev/null || true)"
  [ -n "$pid" ] || return 1
  pid_alive "$pid" || return 1
  pid_matches_service "$svc" "$pid" || return 1
  pids="$(port_pids "$(service_port "$svc")")"
  [[ " $pids " == *" $pid "* ]]
}

hx_core_flags() {
  printf -- '--app-port %s --db-port %s --view-port %s' "$APP_PORT" "$DB_PORT" "$VIEW_PORT"
}

# ------------------------------------------------------------------ 状态文件

hx_state_get() {
  local key="$1"
  [ -f "$HX_STATE" ] || return 1
  sed -n "s/^${key}=//p" "$HX_STATE" 2>/dev/null | tail -n 1
}

hx_state_write() {
  local tmp
  mkdir -p "$RUN_DIR" || return 1
  tmp="$HX_STATE.tmp.$$"
  {
    printf 'format=1\n'
    printf 'started_at=%s\n' "$(iso_now)"
    printf 'profile=%s\n' "$PROFILE"
    printf 'flags=%s\n' "$HX_FLAGS"
    printf 'ports=%s\n' "$APP_PORT,$DB_PORT,$VIEW_PORT,$CATALOG_PORT,$ANYFIELD_PORT,$COVER_PORT"
    printf 'core_owned=%s\n' "$CORE_OWNED"
    printf 'catalog=%s\n' "$([ "$ENABLE_CATALOG" -eq 1 ] && echo 1 || echo 0)"
    printf 'anyfield=%s\n' "$([ "$ENABLE_ANYFIELD" -eq 1 ] && echo 1 || echo 0)"
    printf 'cover=%s\n' "$([ "$ENABLE_COVER" -eq 1 ] && echo 1 || echo 0)"
    printf 'cover_dir=%s\n' "$COVER_DIR"
    printf 'git=%s\n' "$(launcher_git_rev)"
  } >"$tmp" && mv "$tmp" "$HX_STATE"
}

hx_check_state_ports() {
  local recorded current recorded_flags
  [ -f "$HX_STATE" ] || return 0
  recorded="$(hx_state_get ports 2>/dev/null || true)"
  current="$APP_PORT,$DB_PORT,$VIEW_PORT,$CATALOG_PORT,$ANYFIELD_PORT,$COVER_PORT"
  if [ -n "$recorded" ] && [ "$recorded" != "$current" ]; then
    recorded_flags="$(hx_state_get flags 2>/dev/null || true)"
    echo "Error: an integrated run with different ports is recorded in ${HX_STATE#"$LAUNCHER_ROOT_DIR"/}." >&2
    echo "  recorded: $recorded" >&2
    echo "  current:  $current" >&2
    echo "Stop it first with the recorded ports:" >&2
    echo "  ./stop_huellax.sh ${recorded_flags:-<recorded flags unavailable>}" >&2
    return 1
  fi
  return 0
}

# ------------------------------------------------------------------ 路径/可用性

hx_cover_dir() {
  local explicit="$1" cand abs
  if [ -n "$explicit" ]; then
    if [ ! -d "$explicit" ]; then
      echo "Error: cover directory not found: $explicit" >&2
      return 2
    fi
    abs="$(cd "$explicit" && pwd)" || return 2
    if [ ! -f "$abs/index.html" ]; then
      echo "Error: cover directory has no index.html: $abs" >&2
      return 2
    fi
    printf '%s\n' "$abs"
    return 0
  fi
  # 新封面（cover 分支）优先；旧目录名只作为兼容。
  for cand in \
    "$LAUNCHER_ROOT_DIR" \
    "$LAUNCHER_ROOT_DIR/cover" \
    "$LAUNCHER_ROOT_DIR/portada" \
    "$LAUNCHER_ROOT_DIR/封面" \
    "$HUELLAX_DIR/cover"; do
    if [ -d "$cand" ] && [ -f "$cand/index.html" ]; then
      (cd "$cand" && pwd)
      return 0
    fi
  done
  return 1
}

hx_resolve_stack() {
  local rc=0
  if [ ! -f "$SPHEREX_DB" ]; then
    echo "Error: missing SQLite catalog: $SPHEREX_DB" >&2
    echo "  Initialize it first: cd 系统/数据库工具 && PYTHON=<python> ./tools/import_all.sh" >&2
    echo "  or minimal:          cd 系统/数据库工具 && PYTHON=<python> ./cli.py init" >&2
    return 1
  fi

  if [ "$ENABLE_CATALOG" -eq 1 ]; then
    if [ ! -f "$STAR_DB" ]; then
      ENABLE_CATALOG=0
      CATALOG_REASON="star_catalog.sqlite not found: $STAR_DB"
    elif [ ! -f "$CATALOG_SERVER" ]; then
      ENABLE_CATALOG=0
      CATALOG_REASON="catalog_server.py not found: $CATALOG_SERVER"
    fi
  else
    CATALOG_REASON="disabled by --no-catalog"
  fi

  if [ "$ENABLE_ANYFIELD" -eq 1 ]; then
    if [ ! -f "$ANYFIELD_SERVER" ]; then
      ENABLE_ANYFIELD=0
      ANYFIELD_REASON="anyfield/server.py not found: $ANYFIELD_SERVER"
    fi
  else
    ANYFIELD_REASON="disabled by --no-anyfield"
  fi

  if [ "$ENABLE_COVER" -eq 1 ]; then
    COVER_DIR="$(hx_cover_dir "$COVER_DIR_REQUESTED")" || rc=$?
    if [ "$rc" -ne 0 ]; then
      if [ -n "$COVER_DIR_REQUESTED" ]; then
        return 1
      fi
      ENABLE_COVER=0
      COVER_REASON="no cover root with index.html (checked cover/, portada/, 封面/, launcher fallback)"
    fi
  else
    COVER_REASON="disabled by --no-cover"
  fi
  return 0
}

hx_service_available() {
  case "$1" in
    db|app|view) echo 1 ;;
    catalog) echo "$ENABLE_CATALOG" ;;
    anyfield) echo "$ENABLE_ANYFIELD" ;;
    cover) echo "$ENABLE_COVER" ;;
    *) echo 0 ;;
  esac
}

hx_skip_reason() {
  case "$1" in
    catalog) echo "$CATALOG_REASON" ;;
    anyfield) echo "$ANYFIELD_REASON" ;;
    cover) echo "$COVER_REASON" ;;
    *) echo "" ;;
  esac
}

hx_mark_started() {
  case "$1" in
    catalog) HX_STARTED_CATALOG=1 ;;
    anyfield) HX_STARTED_ANYFIELD=1 ;;
    cover) HX_STARTED_COVER=1 ;;
  esac
}

hx_was_started() {
  case "$1" in
    catalog) echo "$HX_STARTED_CATALOG" ;;
    anyfield) echo "$HX_STARTED_ANYFIELD" ;;
    cover) echo "$HX_STARTED_COVER" ;;
    *) echo 0 ;;
  esac
}

# ------------------------------------------------------------------ 预检

# 返回 0=core 端口都空；3=三服务已由启动器管理且健康；其他=拒绝启动。
hx_preflight_core() {
  local svc port pids pid owned=0 healthy=0 listening=0 line
  for svc in db app view; do
    port="$(service_port "$svc")"
    pids="$(port_pids "$port")"
    if [ -z "$pids" ]; then
      continue
    fi
    listening=1
    pid="$(read_pid "$svc" 2>/dev/null || true)"
    if [ -n "$pid" ] && pid_alive "$pid" && pid_matches_service "$svc" "$pid" \
      && [[ " $pids " == *" $pid "* ]]; then
      owned=$((owned + 1))
      if health_once "$svc" 2 >/dev/null 2>&1; then
        healthy=$((healthy + 1))
      fi
      continue
    fi
    echo "  x core service $svc port $port is held by a foreign process:" >&2
    while IFS= read -r line; do
      [ -n "$line" ] && echo "      $line" >&2
    done < <(port_owner_lines "$port")
    return 1
  done
  if [ "$listening" -eq 0 ]; then
    return 0
  fi
  if [ "$owned" -eq 3 ] && [ "$healthy" -eq 3 ]; then
    return 3
  fi
  echo "  error: core services are partially running or unhealthy (owned=$owned healthy=$healthy)." >&2
  echo "  Stop them first: ./stop_all.sh $(hx_core_flags)" >&2
  return 1
}

# 返回 0=端口空闲；1=被外部进程占用；3=本启动器管理的健康实例；4=本启动器管理但不健康（应重启）。
hx_preflight_extra() {
  local svc="$1" timeout="${2:-2}" port pids pid line
  port="$(service_port "$svc")"
  pids="$(port_pids "$port")"
  if [ -z "$pids" ]; then
    pid="$(read_pid "$svc" 2>/dev/null || true)"
    if [ -n "$pid" ] && pid_alive "$pid" && pid_matches_service "$svc" "$pid"; then
      echo "  $svc: recorded pid=$pid is alive but not listening on $port" >&2
      return 4
    fi
    if [ -n "$pid" ]; then
      rm -f "$(pidfile "$svc")" 2>/dev/null || true
    fi
    return 0
  fi
  pid="$(read_pid "$svc" 2>/dev/null || true)"
  if [ -n "$pid" ] && pid_alive "$pid" && pid_matches_service "$svc" "$pid" \
    && [[ " $pids " == *" $pid "* ]]; then
    if health_once "$svc" "$timeout" >/dev/null 2>&1; then
      echo "  $svc: already running and healthy (pid=$pid)"
      return 3
    fi
    echo "  $svc: launcher-owned pid=$pid is listening but unhealthy; restarting it" >&2
    return 4
  fi
  echo "  x $svc port $port is held by a foreign process (not killed):" >&2
  while IFS= read -r line; do
    [ -n "$line" ] && echo "      $line" >&2
  done < <(port_owner_lines "$port")
  return 1
}

# ------------------------------------------------------------------ 启动/健康

hx_start_core() {
  local -a args=(--app-port "$APP_PORT" --db-port "$DB_PORT" --view-port "$VIEW_PORT")
  if [ "$OFFLINE" -eq 1 ]; then
    args+=(--offline)
  fi
  echo "Starting core DB/app/view via start_all.sh..."
  "$HUELLAX_DIR/start_all.sh" "${args[@]}"
}

hx_start_extra() {
  local svc="$1" log pid
  log="$(logfile "$svc")"
  mkdir -p "$RUN_DIR" "$LOG_DIR" || return 1
  printf '[%s] === start %s port=%s profile=%s cover_root=%s ===\n' \
    "$(iso_now)" "$svc" "$(service_port "$svc")" "$PROFILE" "${COVER_DIR:-}" >>"$log"
  case "$svc" in
    catalog)
      (
        cd "$DB_TOOL_DIR" &&
          exec nohup env PYTHONUNBUFFERED=1 "$APPPY" catalog_server.py \
            --port "$CATALOG_PORT" --db "$STAR_DB"
      ) >>"$log" 2>&1 &
      ;;
    anyfield)
      (
        cd "$ANYFIELD_DIR" &&
          exec nohup env PYTHON="$APPPY" PYTHONUNBUFFERED=1 ./start.sh "$ANYFIELD_PORT"
      ) >>"$log" 2>&1 &
      ;;
    cover)
      (
        cd "$COVER_DIR" &&
          exec nohup env PYTHONUNBUFFERED=1 python3 -m http.server "$COVER_PORT" --bind 127.0.0.1
      ) >>"$log" 2>&1 &
      ;;
    *)
      echo "Error: unknown extra service $svc" >&2
      return 1
      ;;
  esac
  pid=$!
  printf '%s\n' "$pid" >"$(pidfile "$svc")"
  hx_mark_started "$svc"
  echo "  $svc: started pid=$pid (log ${log#"$LAUNCHER_ROOT_DIR"/})"
  return 0
}

hx_wait_extra() {
  local svc="$1" timeout="${2:-15}" out owner_err
  printf '  waiting for %-8s health (max %ss)... ' "$svc" "$timeout"
  if ! out="$(health_wait "$svc" "$timeout")"; then
    echo "FAIL"
    log_event "$svc" "health FAILED: $out"
    echo "  error: $svc health check failed: $out" >&2
    print_log_tail "$svc"
    return 1
  fi
  if ! owner_err="$(verify_service_owner "$svc")"; then
    echo "FAIL"
    log_event "$svc" "owner check FAILED: $owner_err"
    echo "  error: $svc health is reachable ($out) but owner check failed: $owner_err" >&2
    print_log_tail "$svc"
    return 1
  fi
  echo "ok ($out)"
  log_event "$svc" "healthy: $out"
  return 0
}

hx_export_app_env() {
  # The app must follow the ports managed by this launcher, not stale defaults.
  export SPHEREX_DB_URL="http://127.0.0.1:${DB_PORT}"
  export MOVESCOPE_DB_URL="$SPHEREX_DB_URL"
  export CATALOG_URL="http://127.0.0.1:${CATALOG_PORT}"
  export MOVESCOPE_CATALOG_URL="$CATALOG_URL"
  export ANYFIELD_URL="http://127.0.0.1:${ANYFIELD_PORT}"
  # Local services must never go through a user-level HTTP proxy.
  local no_proxy_list="127.0.0.1,localhost"
  if [ -n "${NO_PROXY:-}" ]; then
    no_proxy_list="${NO_PROXY},${no_proxy_list}"
  fi
  export NO_PROXY="$no_proxy_list"
  export no_proxy="$no_proxy_list"
}

# ------------------------------------------------------------------ 锁/回滚/报告

hx_acquire_lock() {
  local pid=""
  if mkdir "$HX_LOCK" 2>/dev/null; then
    printf '%s\n' "$$" >"$HX_LOCK/pid"
    HX_LOCK_HELD=1
    return 0
  fi
  if [ -f "$HX_LOCK/pid" ]; then
    pid="$(tr -cd '0-9' <"$HX_LOCK/pid")"
  fi
  if [ -n "$pid" ] && pid_alive "$pid"; then
    echo "Error: another start_huellax.sh is running (pid=$pid, lock=$HX_LOCK)." >&2
    return 1
  fi
  echo "Cleaning stale integrated start lock: ${HX_LOCK#"$LAUNCHER_ROOT_DIR"/}" >&2
  rm -f "$HX_LOCK/pid" 2>/dev/null || true
  rmdir "$HX_LOCK" 2>/dev/null || true
  if mkdir "$HX_LOCK" 2>/dev/null; then
    printf '%s\n' "$$" >"$HX_LOCK/pid"
    HX_LOCK_HELD=1
    return 0
  fi
  echo "Error: cannot acquire integrated start lock $HX_LOCK" >&2
  return 1
}

hx_release_lock() {
  if [ "${HX_LOCK_HELD:-0}" -eq 1 ]; then
    rm -f "$HX_LOCK/pid" 2>/dev/null || true
    rmdir "$HX_LOCK" 2>/dev/null || true
    HX_LOCK_HELD=0
  fi
}

hx_rollback() {
  [ "$ROLLBACK_DONE" -eq 0 ] || return 0
  ROLLBACK_DONE=1
  local svc rc=0
  echo >&2
  echo "Rollback: stopping only services started by this integrated run" >&2
  for svc in cover anyfield catalog; do
    if [ "$(hx_was_started "$svc")" -eq 1 ]; then
      stop_one "$svc" || rc=1
    fi
  done
  if [ "$CORE_STARTED_THIS_RUN" -eq 1 ]; then
    "$HUELLAX_DIR/stop_all.sh" $(hx_core_flags) || rc=1
  elif [ "$CORE_OWNED" -eq 1 ]; then
    echo "  core services were already running before this start; left untouched" >&2
  fi
  hx_release_lock
  return "$rc"
}

hx_on_signal() {
  trap - INT TERM
  echo >&2
  echo "Interrupted; rolling back this integrated start..." >&2
  hx_rollback || true
  exit 130
}

hx_health_report() {
  local svc url pid health status note label
  printf '\n%-8s %-36s %-8s %s\n' "SERVICE" "URL" "STATUS" "PID / NOTE"
  for svc in db app view catalog anyfield cover; do
    label="$(service_label "$svc")"
    if [ "$(hx_service_available "$svc")" != "1" ]; then
      url="$(service_url "$svc")"
      case "$svc" in view|cover) url="$url/" ;; esac
      printf '%-8s %-36s %-8s %s\n' "$label" "$url" "skip" "$(hx_skip_reason "$svc")"
      continue
    fi
    url="$(service_url "$svc")"
    case "$svc" in view|cover) url="$url/" ;; esac
    pid="$(read_pid "$svc" 2>/dev/null || true)"
    health="$(health_once "$svc" 2 2>/dev/null || true)"
    if [[ "$health" == ok* ]]; then
      status="ok"
    else
      status="FAIL"
    fi
    if [ -n "$pid" ] && pid_alive "$pid" && pid_matches_service "$svc" "$pid"; then
      note="pid=$pid (launcher)"
    elif [ -n "$pid" ]; then
      note="pid=$pid (stale/mismatch)"
    else
      note="pid=- (external or stopped)"
    fi
    printf '%-8s %-36s %-8s %s\n' "$label" "$url" "$status" "$note"
    if [ "$status" = "FAIL" ]; then
      printf '         reason: %s\n' "$health"
    fi
  done
}

hx_required_check() {
  local svc health rc=0
  for svc in db app view; do
    health="$(health_once "$svc" 2 2>/dev/null || true)"
    if [[ "$health" != ok* ]]; then
      echo "  required $svc is not healthy: $health" >&2
      rc=1
    fi
  done
  if [ "$ENABLE_CATALOG" -eq 1 ]; then
    health="$(health_once catalog 2 2>/dev/null || true)"
    if [[ "$health" != ok* ]]; then
      echo "  required B (catalog) is not healthy: $health" >&2
      rc=1
    fi
  fi
  if [ "$ENABLE_COVER" -eq 1 ]; then
    health="$(health_once cover 2 2>/dev/null || true)"
    if [[ "$health" != ok* ]]; then
      echo "  required cover is not healthy: $health" >&2
      rc=1
    fi
  fi
  if [ "$ENABLE_ANYFIELD" -eq 1 ] && [ "$REQUIRE_ANYFIELD" -eq 1 ]; then
    health="$(health_once anyfield 2 2>/dev/null || true)"
    if [[ "$health" != ok* ]]; then
      echo "  required C (--require-anyfield) is not healthy: $health" >&2
      rc=1
    fi
  fi
  return "$rc"
}

hx_print_header() {
  echo "HuellaX integrated launcher (profile=$PROFILE)"
  echo "  core ports : app=$APP_PORT db=$DB_PORT view=$VIEW_PORT"
  echo "  extra ports: B=$CATALOG_PORT C=$ANYFIELD_PORT cover=$COVER_PORT"
  echo "  SQL catalog: ${SPHEREX_DB#"$LAUNCHER_ROOT_DIR"/}"
  echo "  star catalog: ${STAR_DB#"$LAUNCHER_ROOT_DIR"/}$([ -f "$STAR_DB" ] && echo "" || echo " (missing)")"
  if [ "$ENABLE_COVER" -eq 1 ]; then
    echo "  cover root : ${COVER_DIR#"$LAUNCHER_ROOT_DIR"/} ($COVER_DIR)"
  else
    echo "  cover root : <disabled>"
  fi
  echo "  PID dir    : ${RUN_DIR#"$LAUNCHER_ROOT_DIR"/}    logs: ${LOG_DIR#"$LAUNCHER_ROOT_DIR"/}"
  echo "  git        : $(launcher_git_rev)"
}

hx_data_report() {
  local schema star_size
  echo
  echo "[SQL data]"
  schema="$("$LAUNCHER_PROBE_PY" "$LAUNCHER_PROBE" schema --db "$SPHEREX_DB" 2>&1 || true)"
  echo "  catalog.sqlite : ${SPHEREX_DB#"$LAUNCHER_ROOT_DIR"/}"
  echo "    schema_version: $schema"
  if [ -f "$STAR_DB" ]; then
    star_size="$(du -h "$STAR_DB" 2>/dev/null | awk '{print $1}')"
    echo "  star_catalog.sqlite: ${STAR_DB#"$LAUNCHER_ROOT_DIR"/} (${star_size:-?})"
    echo "    separate SQLite; B service only"
  else
    echo "  star_catalog.sqlite: missing (B 8799 will be skipped)"
  fi
  if [ "$ENABLE_COVER" -eq 1 ]; then
    echo "  cover root     : $COVER_DIR"
  fi
}

hx_print_hints() {
  echo
  echo "Open:   http://127.0.0.1:${APP_PORT}/"
  echo "View:   http://127.0.0.1:${VIEW_PORT}/"
  echo "DB API: http://127.0.0.1:${DB_PORT}/api/health"
  if [ "$ENABLE_CATALOG" -eq 1 ]; then
    echo "B API:  http://127.0.0.1:${CATALOG_PORT}/api/v1/health"
  fi
  if [ "$ENABLE_ANYFIELD" -eq 1 ]; then
    echo "C API:  http://127.0.0.1:${ANYFIELD_PORT}/api/v1/health"
  fi
  if [ "$ENABLE_COVER" -eq 1 ]; then
    echo "Cover:  http://127.0.0.1:${COVER_PORT}/"
  fi
  echo "Status: ./status_huellax.sh $(hx_flags)"
  echo "Stop:   ./stop_huellax.sh $(hx_flags)"
}
