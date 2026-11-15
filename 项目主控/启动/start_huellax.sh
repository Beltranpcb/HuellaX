#!/usr/bin/env bash
# 一条命令启动 SQL-first 整栈：
#   DB 8797 → MoveScope 8790 → Sky View 8830（复用 start_all.sh/lib.sh）
#   → B 星表 8799（仅当 var/star_catalog.sqlite 存在）
#   → C AnyField 8798（可选，代码存在时）
#   → 静态封面 8840（python3 -m http.server，服务封面根）
#
# 只停止本启动器（族）写入 run/*.pid 且命令行校验通过的进程；
# 不扫描/不自动换端口、不 pkill、不杀外部进程。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=huellax_lib.sh
source "$SCRIPT_DIR/huellax_lib.sh"

hx_parse_args "$(basename "$0")" "$@"
launcher_require_commands || exit 1
launcher_require_python3 || exit 1
hx_resolve_stack || exit 1
hx_check_state_ports || exit 1

SECONDS=0
hx_print_header
if [ "$ENABLE_CATALOG" -eq 0 ]; then
  echo "  B 8799      : skipped — $CATALOG_REASON"
fi
if [ "$ENABLE_ANYFIELD" -eq 0 ]; then
  echo "  C 8798      : skipped — $ANYFIELD_REASON"
fi
if [ "$ENABLE_COVER" -eq 0 ]; then
  echo "  cover 8840  : skipped — $COVER_REASON"
fi
if [ "$OFFLINE" -eq 1 ]; then
  echo "  offline mode: app gets a black-hole proxy and uses cached data"
fi
echo

APPPY="$(resolve_app_python)" || exit 1
export PYTHON="$APPPY"
mkdir -p "$RUN_DIR" "$LOG_DIR" || exit 1
hx_acquire_lock || exit 1
trap 'hx_release_lock' EXIT
trap 'hx_on_signal' INT TERM

PREV_CORE_OWNED="$(hx_state_get core_owned 2>/dev/null || true)"
[ -n "$PREV_CORE_OWNED" ] || PREV_CORE_OWNED=0

# The app must talk to the exact ports started below (also in sandbox profiles).
hx_export_app_env

echo "Preflight: core + integrated ports (ports are explicit, never auto-shifted)"
core_state=0
hx_preflight_core || core_state=$?
case "$core_state" in
  0) ;;
  3) echo "  core DB/app/view are already running under the launcher" ;;
  *)
    echo "Error: core ports are not available; refusing to start the integrated stack." >&2
    exit 1
    ;;
esac

catalog_pre=9
if [ "$ENABLE_CATALOG" -eq 1 ]; then
  catalog_pre=0
  hx_preflight_extra catalog 5 || catalog_pre=$?
  case "$catalog_pre" in
    0) ;;
    3) ;;
    4) ;;
    *)
      echo "Error: B port $CATALOG_PORT is not available; star_catalog.sqlite exists so B is required." >&2
      echo "  Stop the foreign process or rerun with --no-catalog to skip B explicitly." >&2
      exit 1
      ;;
  esac
fi

anyfield_pre=9
if [ "$ENABLE_ANYFIELD" -eq 1 ]; then
  anyfield_pre=0
  hx_preflight_extra anyfield 5 || anyfield_pre=$?
  case "$anyfield_pre" in
    0) ;;
    3) ;;
    4) ;;
    *)
      if [ "$REQUIRE_ANYFIELD" -eq 1 ]; then
        echo "Error: C port $ANYFIELD_PORT is not available and --require-anyfield was set." >&2
        exit 1
      fi
      echo "  warning: C is optional; port $ANYFIELD_PORT is busy. C will be skipped, foreign process left untouched." >&2
      ENABLE_ANYFIELD=0
      ANYFIELD_REASON="port $ANYFIELD_PORT occupied by a foreign process; skipped (optional)"
      anyfield_pre=9
      ;;
  esac
fi

cover_pre=9
if [ "$ENABLE_COVER" -eq 1 ]; then
  cover_pre=0
  hx_preflight_extra cover 3 || cover_pre=$?
  case "$cover_pre" in
    0) ;;
    3) ;;
    4) ;;
    *)
      echo "Error: cover port $COVER_PORT is not available; refusing to start." >&2
      exit 1
      ;;
  esac
fi

# ---------------------------------------------------------------- core 三服务

if [ "$core_state" -eq 3 ]; then
  CORE_WAS_RUNNING=1
  CORE_OWNED="$PREV_CORE_OWNED"
else
  hx_start_core || {
    echo "Error: start_all.sh failed; core services were rolled back by it. No integrated extras were started." >&2
    exit 1
  }
  CORE_STARTED_THIS_RUN=1
  CORE_OWNED=1
fi

# ---------------------------------------------------------------- B 星表

if [ "$ENABLE_CATALOG" -eq 1 ]; then
  if [ "$catalog_pre" -eq 4 ]; then
    echo "Restarting launcher-owned B on $CATALOG_PORT..."
    stop_one catalog || {
      echo "Error: could not stop the unhealthy B instance; rolling back." >&2
      hx_rollback || true
      exit 1
    }
  fi
  if [ "$catalog_pre" -eq 0 ] || [ "$catalog_pre" -eq 4 ]; then
    if ! hx_start_extra catalog; then
      echo "Error: failed to spawn B; rolling back." >&2
      hx_rollback || true
      exit 1
    fi
    if ! hx_wait_extra catalog 20; then
      echo "Error: B star catalog did not become healthy; rolling back." >&2
      hx_rollback || true
      exit 1
    fi
  fi
fi

# ---------------------------------------------------------------- C AnyField（可选）

if [ "$ENABLE_ANYFIELD" -eq 1 ]; then
  if [ "$anyfield_pre" -eq 4 ]; then
    echo "Restarting launcher-owned C on $ANYFIELD_PORT..."
    if ! stop_one anyfield; then
      if [ "$REQUIRE_ANYFIELD" -eq 1 ]; then
        echo "Error: could not stop unhealthy C; rolling back." >&2
        hx_rollback || true
        exit 1
      fi
      echo "  warning: could not stop unhealthy C; C will be skipped." >&2
      ENABLE_ANYFIELD=0
      ANYFIELD_REASON="launcher-owned C could not be stopped; skipped (optional)"
      anyfield_pre=9
    fi
  fi
  if [ "$anyfield_pre" -eq 0 ] || [ "$anyfield_pre" -eq 4 ]; then
    c_ok=1
    if ! hx_start_extra anyfield; then
      c_ok=0
    elif ! hx_wait_extra anyfield 15; then
      c_ok=0
    fi
    if [ "$c_ok" -eq 0 ]; then
      stop_one anyfield >/dev/null 2>&1 || true
      rm -f "$(pidfile anyfield)" 2>/dev/null || true
      if [ "$REQUIRE_ANYFIELD" -eq 1 ]; then
        echo "Error: required C failed to start; rolling back." >&2
        hx_rollback || true
        exit 1
      fi
      echo "  warning: optional C failed to start; stopped C and continuing with the rest of the stack." >&2
      ENABLE_ANYFIELD=0
      ANYFIELD_REASON="optional C failed to start/health; stopped"
    fi
  fi
fi

# ---------------------------------------------------------------- 8840 封面

if [ "$ENABLE_COVER" -eq 1 ]; then
  if [ "$cover_pre" -eq 4 ]; then
    echo "Restarting launcher-owned cover on $COVER_PORT..."
    stop_one cover || {
      echo "Error: could not stop the unhealthy cover instance; rolling back." >&2
      hx_rollback || true
      exit 1
    }
  fi
  if [ "$cover_pre" -eq 0 ] || [ "$cover_pre" -eq 4 ]; then
    if ! hx_start_extra cover; then
      echo "Error: failed to spawn cover; rolling back." >&2
      hx_rollback || true
      exit 1
    fi
    if ! hx_wait_extra cover 10; then
      echo "Error: cover 8840 did not become healthy; rolling back." >&2
      hx_rollback || true
      exit 1
    fi
  fi
fi

# ---------------------------------------------------------------- 收尾

# 可选 C 若在启动后退出，只警告；除非 --require-anyfield。
if [ "$ENABLE_ANYFIELD" -eq 1 ]; then
  c_health="$(health_once anyfield 2 2>/dev/null || true)"
  if [[ "$c_health" != ok* ]]; then
    if [ "$REQUIRE_ANYFIELD" -eq 1 ]; then
      echo "Error: required C is not healthy: $c_health" >&2
      hx_rollback || true
      exit 1
    fi
    echo "  warning: optional C is not healthy ($c_health); stopping it." >&2
    stop_one anyfield >/dev/null 2>&1 || true
    ENABLE_ANYFIELD=0
    ANYFIELD_REASON="optional C became unhealthy; stopped"
  fi
fi

if ! hx_required_check; then
  echo "Error: integrated stack health check failed; rolling back services started by this run." >&2
  hx_rollback || true
  exit 1
fi

hx_state_write || {
  echo "Error: could not write ${HX_STATE#"$LAUNCHER_ROOT_DIR"/}; rolling back." >&2
  hx_rollback || true
  exit 1
}

trap - INT TERM
hx_release_lock

hx_health_report
hx_data_report
hx_print_hints
echo
echo "Integrated stack ready in ${SECONDS}s (profile=$PROFILE)."
