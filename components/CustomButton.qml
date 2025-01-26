import QtQuick
import QtQuick.Controls

Button {
    id: control
    
    background: Rectangle {
        color: control.pressed ? "#45a049" : "#4CAF50"
        radius: 4
    }
    
    contentItem: Text {
        text: control.text
        color: "white"
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }
} 