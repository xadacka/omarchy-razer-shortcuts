import QtQuick
import Quickshell.Io

Item {
  id: root

  property var shell: null

  function pluginPath(url) {
    var value = String(url || "")
    if (value.indexOf("file://") === 0)
      return decodeURIComponent(value.substring(7))
    return value
  }

  Process {
    id: shortcutLights
    command: ["python3", root.pluginPath(Qt.resolvedUrl("daemon.py")), "run"]
    running: true
  }

  IpcHandler {
    target: "razer-shortcuts"

    function reload(): string {
      if (shortcutLights.running) shortcutLights.running = false
      restartTimer.start()
      return "reloading"
    }
  }

  Timer {
    id: restartTimer
    interval: 250
    repeat: false
    onTriggered: shortcutLights.running = true
  }
}
