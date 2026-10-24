import QtQuick

// Çerçeveli küçük tuş adı + etiket ("F9  zen"); tıklanabilir.
Item {
    id: kok
    property string tus
    property string etiket
    property bool etkin: false
    signal tiklandi()

    readonly property var r: ana.renk
    implicitWidth: sira.implicitWidth
    implicitHeight: 24
    width: implicitWidth
    height: implicitHeight

    Row {
        id: sira
        anchors.verticalCenter: parent.verticalCenter
        spacing: 7
        Rectangle {
            anchors.verticalCenter: parent.verticalCenter
            width: tusYazi.implicitWidth + 10
            height: 18
            color: kok.etkin ? r.vurgu : "transparent"
            border.color: kok.etkin ? r.vurgu : (fare.containsMouse ? r.soluk : r.cizgi)
            border.width: 1
            Text {
                id: tusYazi
                anchors.centerIn: parent
                text: kok.tus
                color: kok.etkin ? r.vurgu_yazi : r.soluk
                font { family: pencere.yaziTipi; pixelSize: 11 }
            }
        }
        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: kok.etiket
            color: fare.containsMouse ? r.yazi : r.soluk
            font { family: pencere.yaziTipi; pixelSize: 13 }
            visible: text !== ""
        }
    }
    MouseArea {
        id: fare
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: kok.tiklandi()
    }
}
