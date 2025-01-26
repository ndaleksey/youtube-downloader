import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root
    Layout.fillWidth: true
    height: 100
    color: "#f5f5f5"
    radius: 4
    border.color: "#e0e0e0"
    border.width: 1
    visible: false

    property alias progress: progressBar.value
    property alias status: statusLabel.text
    property alias speed: speedLabel.text

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 10
        spacing: 8

        Label {
            id: statusLabel
            Layout.fillWidth: true
            horizontalAlignment: Text.AlignHCenter
            font.pixelSize: 12
        }

        ProgressBar {
            id: progressBar
            Layout.fillWidth: true
            from: 0
            to: 100
        }

        Label {
            id: speedLabel
            Layout.fillWidth: true
            horizontalAlignment: Text.AlignRight
            font.pixelSize: 12
        }
    }
} 