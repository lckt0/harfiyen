import QtQuick

// Hız testi sonucu: büyük DBK, doğruluk, rekor rozeti (mola'daki gibi), bildirimler.
Item {
    id: kok
    property bool gorunur: false
    readonly property var r: ana.renk
    readonly property var m: ana.metinler
    readonly property var s: ana.sonuc

    visible: perde.opacity > 0
    onGorunurChanged: if (gorunur && s.rekor) rozetBelir.restart()

    Rectangle {
        id: perde
        anchors.fill: parent
        color: "#000000"
        opacity: kok.gorunur ? 0.6 : 0
        Behavior on opacity { NumberAnimation { duration: 160 } }
        MouseArea { anchors.fill: parent; enabled: kok.gorunur }
    }

    Rectangle {
        anchors.centerIn: parent
        width: Math.min(parent.width - 64, 560)
        height: govde.implicitHeight
        color: r.zemin
        border.color: r.cizgi
        border.width: 1
        opacity: perde.opacity / 0.6
        scale: 0.97 + 0.03 * opacity

        Column {
            id: govde
            width: parent.width

            Item {
                width: parent.width
                height: 48
                Text {
                    anchors { left: parent.left; leftMargin: 22; verticalCenter: parent.verticalCenter }
                    text: "HARFİYEN  ·  " + (kok.s.baslik || "")
                    color: r.baslik
                    font { family: pencere.yaziTipi; pixelSize: 13; weight: Font.DemiBold; letterSpacing: 2 }
                }
            }
            Rectangle { width: parent.width; height: 1; color: r.cizgi }

            Column {
                width: parent.width
                topPadding: 30
                bottomPadding: 30
                spacing: 12

                Rectangle {
                    id: rozet
                    anchors.horizontalCenter: parent.horizontalCenter
                    visible: kok.s.rekor === true
                    width: rozetYazi.implicitWidth + 28
                    height: rozetYazi.implicitHeight + 10
                    color: r.vurgu
                    Text {
                        id: rozetYazi
                        anchors.centerIn: parent
                        text: m.yeni_rekor
                        color: r.vurgu_yazi
                        font { family: pencere.yaziTipi; pixelSize: 15; weight: Font.Bold; letterSpacing: 2 }
                    }
                    SequentialAnimation {
                        id: rozetBelir
                        NumberAnimation { target: rozet; property: "scale"; from: 0.6; to: 1.12; duration: 160; easing.type: Easing.OutCubic }
                        NumberAnimation { target: rozet; property: "scale"; to: 1.0; duration: 120; easing.type: Easing.InOutQuad }
                    }
                }
                Row {
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: 10
                    Text {
                        text: kok.s.dbk || ""
                        color: kok.s.rekor ? r.vurgu : r.baslik
                        font { family: pencere.yaziTipi; pixelSize: 64; weight: Font.DemiBold }
                    }
                    Text {
                        anchors.baseline: parent.children[0].baseline
                        text: kok.s.birim || ""
                        color: r.soluk
                        font { family: pencere.yaziTipi; pixelSize: 18 }
                    }
                }
                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: (m.m_dogruluk || "") + "  " + (kok.s.dogruluk || "")
                    color: r.dogru
                    font { family: pencere.yaziTipi; pixelSize: 18 }
                }
                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: kok.s.ayrinti || ""
                    color: r.soluk
                    font { family: pencere.yaziTipi; pixelSize: 13 }
                }
                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    visible: text !== ""
                    text: kok.s.onceki || ""
                    color: r.soluk
                    font { family: pencere.yaziTipi; pixelSize: 13 }
                }
                Repeater {
                    model: kok.s.bildirimler || []
                    Text {
                        required property var modelData
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: modelData
                        color: r.uyari
                        font { family: pencere.yaziTipi; pixelSize: 13 }
                    }
                }
            }

            Rectangle { width: parent.width; height: 1; color: r.cizgi }
            Item {
                width: parent.width
                height: 44
                Row {
                    anchors.centerIn: parent
                    spacing: 28
                    TusIpucu { tus: "Enter"; etiket: m.tekrar; onTiklandi: ana.modSec("test") }
                    TusIpucu { tus: "Esc"; etiket: m.derse_don; onTiklandi: ana.modSec("ders") }
                }
            }
        }
    }
}
