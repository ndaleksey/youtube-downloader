import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "./components" as Components

ApplicationWindow {
    visible: true
    width: 600
    height: 300
    title: "YouTube Downloader"

    Component.onCompleted: {
        if (typeof window !== 'undefined') {
            window.setIcon("icons/app.svg")
        }
    }

    Components.LoadingIndicator {
        id: loadingIndicator
        visible: false
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 10

        Label {
            text: "Вставьте ссылку на YouTube видео:"
            font.pixelSize: 14
        }

        TextField {
            id: urlInput
            Layout.fillWidth: true
            placeholderText: "https://www.youtube.com/watch?v=..."
            enabled: !downloadButton.downloading
            
            onTextChanged: {
                errorLabel.text = ""
                qualityCombo.currentIndex = -1
                qualityCombo.model = []
            }
        }

        Button {
            id: checkFormatsButton
            Layout.fillWidth: true
            enabled: urlInput.text.length > 0 && !downloadButton.downloading
            
            contentItem: RowLayout {
                spacing: 10
                Image {
                    source: Qt.resolvedUrl("icons/refresh.svg")
                    sourceSize.width: 24
                    sourceSize.height: 24
                    width: 24
                    height: 24
                    opacity: checkFormatsButton.enabled ? 1.0 : 0.5
                }
                Text {
                    text: "Получить список разрешений"
                    color: checkFormatsButton.enabled ? "black" : "#aaa"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    Layout.fillWidth: true
                }
            }
            
            onClicked: {
                loadingIndicator.open()
                backend.checkFormats(urlInput.text)
            }
        }

        ComboBox {
            id: qualityCombo
            Layout.fillWidth: true
            enabled: count > 0 && !downloadButton.downloading
            model: []
            visible: true
            displayText: count > 0 ? currentText : "Выберите качество видео"
            opacity: enabled ? 1.0 : 0.6
        }

        Button {
            id: downloadButton
            Layout.fillWidth: true
            enabled: urlInput.text.length > 0 && qualityCombo.count > 0
            
            contentItem: RowLayout {
                spacing: 10
                Image {
                    source: downloadButton.downloading ? 
                           Qt.resolvedUrl("icons/stop.svg") : 
                           Qt.resolvedUrl("icons/download.svg")
                    sourceSize.width: 24
                    sourceSize.height: 24
                    width: 24
                    height: 24
                }
                Text {
                    text: downloadButton.downloading ? "Отменить загрузку" : "Начать загрузку"
                    color: downloadButton.enabled ? "black" : "#aaa"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    Layout.fillWidth: true
                }
            }
            
            property bool downloading: false
            
            onClicked: {
                if (downloading) {
                    backend.startDownload(urlInput.text)
                    downloading = false
                    downloadProgress.value = 0
                    downloadProgress.mbValue = 0
                    statusLabel.text = ""
                } else {
                    backend.startDownload(urlInput.text)
                }
            }
        }

        ProgressBar {
            id: downloadProgress
            Layout.fillWidth: true
            from: 0
            to: 100
            visible: downloadButton.downloading
            value: 0

            Label {
                anchors.centerIn: parent
                text: downloadProgress.mbValue ? downloadProgress.mbValue.toFixed(1) + " МБ" : "0 МБ"
                color: "black"
                visible: parent.visible
                z: 1
                
                background: Rectangle {
                    color: "white"
                    opacity: 0.7
                    radius: 2
                    anchors.fill: parent
                    anchors.margins: -4
                }
            }

            Label {
                anchors.right: parent.right
                anchors.rightMargin: 8
                anchors.verticalCenter: parent.verticalCenter
                text: downloadProgress.value.toFixed(1) + "%"
                color: "black"
                visible: parent.visible
                z: 1
                
                background: Rectangle {
                    color: "white"
                    opacity: 0.7
                    radius: 2
                    anchors.fill: parent
                    anchors.margins: -4
                }
            }

            property real mbValue: 0
        }

        Label {
            id: statusLabel
            Layout.fillWidth: true
            horizontalAlignment: Text.AlignHCenter
            font.pixelSize: 12
            visible: downloadButton.downloading
            wrapMode: Text.WordWrap
            text: ""
        }

        Label {
            id: errorLabel
            Layout.fillWidth: true
            horizontalAlignment: Text.AlignHCenter
            color: text.startsWith("Загрузка завершена") ? "#4CAF50" : "red"
            font.pixelSize: 12
            visible: text.length > 0
            wrapMode: Text.WordWrap
        }
    }

    Connections {
        target: backend
        
        function onUrlValidationError(error) {
            errorLabel.text = error
            loadingIndicator.close()
        }

        function onLoadingStarted() {
            errorLabel.text = ""
        }

        function onLoadingFinished() {
            loadingIndicator.close()
        }

        function onFormatsLoaded(formats) {
            qualityCombo.model = formats
            loadingIndicator.close()
        }

        function onDownloadStarted() {
            downloadButton.downloading = true
            downloadProgress.value = 0
            downloadProgress.mbValue = 0
            statusLabel.text = "Подготовка к загрузке..."
            errorLabel.text = ""
        }

        function onProgressChanged(percent, mbValue, speed) {
            if (downloadButton.downloading) {
                downloadProgress.value = percent
                downloadProgress.mbValue = mbValue
                statusLabel.text = speed
            }
        }

        function onDownloadFinished(title) {
            downloadButton.downloading = false
            downloadProgress.value = 0
            downloadProgress.mbValue = 0
            statusLabel.text = ""
            urlInput.text = ""
            errorLabel.text = "Загрузка завершена: " + title
        }

        function onDownloadError(error) {
            loadingIndicator.close()
            downloadButton.downloading = false
            downloadProgress.value = 0
            downloadProgress.mbValue = 0
            statusLabel.text = ""
            errorLabel.text = "Ошибка: " + error
        }
    }
} 