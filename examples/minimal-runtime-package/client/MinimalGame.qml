// Contract-only pseudo component; requires the future SGS GameViewContext host.
import QtQuick

Item {
    required property var context
    readonly property string packageId: "org.sgs.example.runtime_bridge"
    readonly property string apiVersion: "1.0-draft"
    readonly property var supportedModes: ["bridge_demo"]

    function chooseForRequest(token, choice) {
        return context.replyGameRequest(token, { choice: choice }, false)
    }
}
