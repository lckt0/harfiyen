import QtQuick

// Menü, mod ve metin listeleri için ortak katman: perde + mola tarzı kart.
// ↑↓ seç, Enter onayla, Esc kapat; fareyle de seçilir.
Item {
    id: kok
    readonly property var r: ana.renk
    readonly property var m: ana.metinler
    property string baslik
    property var ogeler: []
    property int secim: 0
    readonly property bool gorunur: ana.katman === "menu" || ana.katman === "mod" || ana.katman === "metin"
    signal secildi(string ad)

    visible: perde.opacity > 0

    function ac(b, liste, tur) {
        baslik = b
        ogeler = liste
        secim = Math.max(0, liste.findIndex(o => o.isaret))
        ana.katmanAc(tur)
    }
    function kapat() { ana.katmanAc("") }
    function tus(olay) {
        if (olay.key === Qt.Key_Escape) kapat()
        else if (olay.key === Qt.Key_Up || olay.key === Qt.Key_Backtab)
            secim = (secim + ogeler.length - 1) % ogeler.length
        else if (olay.key === Qt.Key_Down || olay.key === Qt.Key_Tab)
            secim = (secim + 1) % ogeler.length
        else if (olay.key === Qt.Key_Return || olay.key === Qt.Key_Enter)
            secildi(ogeler[secim].eylem)
    }

    Rectangle {
        id: perde
        anchors.fill: parent
        color: "#000000"
        opacity: kok.gorunur ? 0.55 : 0
        Behavior on opacity { NumberAnimation { duration: 140 } }
        MouseArea { anchors.fill: parent; enabled: kok.gorunur; onClicked: kok.kapat() }
    }

    Rectangle {
        id: kart
        anchors.centerIn: parent
        width: Math.min(parent.width - 64, 620)
        height: govde.implicitHeight
        color: r.zemin
        border.color: r.cizgi
        border.width: 1
        opacity: perde.opacity / 0.55
        scale: 0.97 + 0.03 * opacity

        Column {
            id: govde
            width: parent.width

            Item {
                width: parent.width
                height: 48
                Text {
                    anchors { left: parent.left; leftMargin: 22; verticalCenter: parent.verticalCenter }
                    text: kok.baslik.toLocaleUpperCase(Qt.locale("tr_TR"))
                    color: r.baslik
                    font { family: pencere.yaziTipi; pixelSize: 13; weight: Font.DemiBold; letterSpacing: 2 }
                }
                TusIpucu {
                    anchors { right: parent.right; rightMargin: 18; verticalCenter: parent.verticalCenter }
                    tus: "Esc"; etiket: ""
                    onTiklandi: kok.kapat()
                }
            }
            Rectangle { width: parent.width; height: 1; color: r.cizgi }

            Item { width: 1; height: 8 }
            Repeater {
                model: kok.ogeler
                delegate: Item {
                    id: oge
                    required property var modelData
                    required property int index
                    readonly property bool secili: index === kok.secim
                    width: govde.width
                    height: 42
                    Rectangle {
                        anchors { fill: parent; leftMargin: 1; rightMargin: 1 }
                        color: oge.secili ? r.yuzey : "transparent"
                    }
                    Rectangle {
                        visible: oge.secili
                        anchors { left: parent.left; top: parent.top; bottom: parent.bottom; leftMargin: 1 }
                        width: 2
                        color: r.vurgu
                    }
                    Text {
                        id: isaret
                        anchors { left: parent.left; leftMargin: 22; verticalCenter: parent.verticalCenter }
                        text: oge.modelData.isaret ? "●" : ""
                        width: 18
                        color: r.vurgu
                        font { family: pencere.yaziTipi; pixelSize: 10 }
                    }
                    Text {
                        id: etiket
                        anchors { left: isaret.right; verticalCenter: parent.verticalCenter }
                        text: oge.modelData.etiket
                        color: oge.secili ? r.baslik : r.yazi
                        font { family: pencere.yaziTipi; pixelSize: 15 }
                    }
                    Text {
                        anchors { right: parent.right; rightMargin: 22; verticalCenter: parent.verticalCenter; left: etiket.right; leftMargin: 24 }
                        horizontalAlignment: Text.AlignRight
                        elide: Text.ElideLeft
                        text: oge.modelData.ipucu || ""
                        color: r.soluk
                        font { family: pencere.yaziTipi; pixelSize: 12 }
                    }
                    MouseArea {
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onEntered: kok.secim = oge.index
                        onClicked: kok.secildi(oge.modelData.eylem)
                    }
                }
            }
            Item { width: 1; height: 8 }
            Rectangle { width: parent.width; height: 1; color: r.cizgi }
            Item {
                width: parent.width
                height: 36
                Text {
                    anchors { left: parent.left; leftMargin: 22; verticalCenter: parent.verticalCenter }
                    text: m.menu_ipucu
                    color: r.soluk
                    font { family: pencere.yaziTipi; pixelSize: 12 }
                }
            }
        }
    }
}
