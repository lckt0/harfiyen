import QtQuick

// Düz, keskin köşeli klavye. Açık harfler parmak renginde hafif tonlu ve altlarında ince
// parmak çizgisi var; basılacak tuş vurgu renginde biraz kalkar, Shift eşi vurgu
// çerçevelidir, yanlış basılan tuş kısa bir an hata renginde yanar.
Item {
    id: kok
    readonly property var r: ana.renk
    readonly property real u: width / ana.klavyeGenislik
    readonly property real ara: Math.max(3, Math.round(u * 0.08))

    height: 5 * u

    function parmakRengi(p) { return r["p_" + p] || r.soluk }

    Repeater {
        model: ana.tuslar
        delegate: Item {
            id: tus
            required property var modelData
            readonly property var k: modelData
            readonly property bool hedef: ana.hedefTus !== "" && k.ad === ana.hedefTus && !k.numpad
            readonly property bool shift: ana.shiftTus !== "" && k.ad === ana.shiftTus
            readonly property bool flas: ana.flasTus !== "" && k.ad === ana.flasTus && !k.numpad
            readonly property bool renkli: k.acik && k.parmak !== "" && (k.harf || k.ad === " ")
            readonly property color pRenk: kok.parmakRengi(k.parmak)

            x: k.x * kok.u + kok.ara / 2
            y: k.satir * kok.u + kok.ara / 2
            width: k.g * kok.u - kok.ara
            height: k.yuk * kok.u - kok.ara

            Rectangle {
                id: govde
                width: parent.width
                height: parent.height
                y: tus.hedef ? -3 : 0
                color: tus.flas ? r.hata
                     : tus.hedef ? r.vurgu
                     : tus.renkli ? Qt.tint(r.yuzey, Qt.alpha(tus.pRenk, 0.10 + 0.12 * r.karisim))
                     : r.yuzey
                border.width: 1
                border.color: tus.shift ? r.vurgu
                            : tus.hedef ? r.vurgu
                            : tus.renkli ? Qt.tint(r.cizgi, Qt.alpha(tus.pRenk, 0.35)) : r.cizgi
                Behavior on y { NumberAnimation { duration: 80; easing.type: Easing.OutCubic } }
                Behavior on color { ColorAnimation { duration: 80 } }

                // Shift'li karakter (sayı sırası)
                Text {
                    anchors { left: parent.left; top: parent.top; leftMargin: kok.u * 0.12; topMargin: kok.u * 0.06 }
                    visible: tus.k.ust !== ""
                    text: tus.k.ust
                    color: tus.hedef ? r.vurgu_yazi : r.soluk
                    font { family: pencere.yaziTipi; pixelSize: Math.round(kok.u * 0.2) }
                }
                Text {
                    anchors.centerIn: parent
                    anchors.verticalCenterOffset: tus.k.ust !== "" ? kok.u * 0.1 : 0
                    text: tus.k.etiket
                    color: tus.hedef || tus.flas ? r.vurgu_yazi
                         : tus.shift ? r.vurgu
                         : tus.k.harf ? (tus.k.acik ? r.yazi : r.cizgi)
                         : r.soluk
                    font {
                        family: pencere.yaziTipi
                        pixelSize: Math.round(kok.u * (tus.k.etiket.length > 1 ? 0.2 : 0.3))
                        weight: tus.hedef ? Font.Bold : Font.Normal
                    }
                }
                // F ve J çıkıntısı
                Rectangle {
                    visible: tus.k.cikinti
                    anchors { horizontalCenter: parent.horizontalCenter; bottom: parent.bottom; bottomMargin: kok.u * 0.14 }
                    width: kok.u * 0.22
                    height: 2
                    color: tus.hedef ? r.vurgu_yazi : r.soluk
                }
                // Parmak çizgisi
                Rectangle {
                    visible: tus.renkli && !tus.hedef
                    anchors { bottom: parent.bottom; left: parent.left; right: parent.right; margins: 1 }
                    height: 2
                    color: tus.pRenk
                    opacity: 0.8
                }
            }
        }
    }
}
