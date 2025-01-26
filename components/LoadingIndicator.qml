import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Popup {
    id: loadingPopup
    modal: true
    focus: true
    closePolicy: Popup.NoAutoClose
    width: 300
    height: 100
    x: (parent.width - width) / 2
    y: (parent.height - height) / 2
    padding: 0
    
    // Делаем модальный оверлей непрозрачным
    Overlay.modal: Rectangle {
        color: "#99000000"
    }
    
    contentItem: Rectangle {
        color: "#ffffff"  // Белый фон
        
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 10
            spacing: 10

            BusyIndicator {
                id: busyIndicator
                Layout.alignment: Qt.AlignHCenter
                running: loadingPopup.visible
                width: 48
                height: 48
            }

            Label {
                text: "Загрузка списка форматов..."
                Layout.alignment: Qt.AlignHCenter
                font.pixelSize: 14
                color: "#000000"
            }
        }
    }
    
    background: Rectangle {
        color: "#ffffff"
        radius: 5
        border.color: "#cccccc"
        border.width: 1
    }

    // Используем простую анимацию масштаба
    enter: Transition {
        NumberAnimation { property: "scale"; from: 0.9; to: 1.0; duration: 200 }
    }
    exit: Transition {
        NumberAnimation { property: "scale"; from: 1.0; to: 0.9; duration: 200 }
    }

    // Добавляем отладочный вывод
    Component.onCompleted: {
        console.log("LoadingIndicator component created")
    }

    onVisibleChanged: {
        console.log("LoadingIndicator visibility changed to:", visible)
    }

    onOpened: {
        console.log("LoadingIndicator opened")
    }

    onClosed: {
        console.log("LoadingIndicator closed")
    }
} 