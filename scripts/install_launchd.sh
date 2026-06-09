#!/usr/bin/env bash
# install_launchd.sh
# ──────────────────
# Installs four launchd schedules so the terminal's data updates
# automatically without your laptop being logged in.
#
# Schedule (IST):
#   16:30  update_prices.py
#   17:00  update_filings.py
#   17:30  generate_ai_summaries.py
#   08:30  send_daily_email.py --brief morning
#   16:35  send_daily_email.py --brief evening
#
# Run once:
#     bash scripts/install_launchd.sh
#
# Uninstall:
#     bash scripts/install_launchd.sh --uninstall

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="${PROJECT_DIR}/.venv/bin/python"
LOG_DIR="${PROJECT_DIR}/logs"
LAUNCH_DIR="${HOME}/Library/LaunchAgents"

mkdir -p "${LOG_DIR}" "${LAUNCH_DIR}"

# IST = UTC+5:30. launchd uses LOCAL time (your Mac's timezone).
# Adjust the Hour/Minute below if you are not in IST.

make_plist () {
    local name="$1" hour="$2" minute="$3" script="$4" args="$5"
    cat > "${LAUNCH_DIR}/com.indiaterminal.${name}.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>             <string>com.indiaterminal.${name}</string>
  <key>WorkingDirectory</key>  <string>${PROJECT_DIR}</string>
  <key>ProgramArguments</key>
  <array>
    <string>${PYTHON}</string>
    <string>${PROJECT_DIR}/scripts/${script}</string>
EOF
    for a in ${args}; do
        echo "    <string>${a}</string>" >> "${LAUNCH_DIR}/com.indiaterminal.${name}.plist"
    done
    cat >> "${LAUNCH_DIR}/com.indiaterminal.${name}.plist" <<EOF
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>   <integer>${hour}</integer>
    <key>Minute</key> <integer>${minute}</integer>
  </dict>
  <key>StandardOutPath</key>  <string>${LOG_DIR}/${name}.log</string>
  <key>StandardErrorPath</key><string>${LOG_DIR}/${name}.err.log</string>
  <key>RunAtLoad</key>        <false/>
</dict>
</plist>
EOF
}

case "${1:-install}" in
  --uninstall|uninstall)
    for n in prices filings summaries email_morning email_evening; do
        f="${LAUNCH_DIR}/com.indiaterminal.${n}.plist"
        if [ -f "${f}" ]; then
            launchctl unload "${f}" 2>/dev/null || true
            rm "${f}"
            echo "Removed ${f}"
        fi
    done
    echo "Uninstalled."
    ;;
  *)
    make_plist prices         16 30 update_prices.py            ""
    make_plist filings        17 00 update_filings.py           "--days 3"
    make_plist summaries      17 30 generate_ai_summaries.py    ""
    make_plist email_morning   8 30 send_daily_email.py         "--brief morning"
    make_plist email_evening  16 35 send_daily_email.py         "--brief evening"

    for n in prices filings summaries email_morning email_evening; do
        launchctl unload "${LAUNCH_DIR}/com.indiaterminal.${n}.plist" 2>/dev/null || true
        launchctl load   "${LAUNCH_DIR}/com.indiaterminal.${n}.plist"
        echo "Loaded com.indiaterminal.${n}"
    done

    echo ""
    echo "Done.  Logs will appear in ${LOG_DIR}/"
    echo "Check with:  launchctl list | grep indiaterminal"
    ;;
esac
