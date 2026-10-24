import QtQuick

// Yeni harf açıldığında kartın üstünde kısa süre beliren rozet.
Rectangle {
    id: kok
    readonly property var r: ana.renk
    property string harf

    function goster(h) {
        harf = h
        akis.restart()
    }

    width: yazi.implicitWidth + 32
    height: yazi.implicitHeight + 14
    color: r.vurgu
    opacity: 0
    scale: 0.6

    Text {
        id: yazi
        anchors.centerIn: parent
        text: (ana.metinler.yeni_harf_kisa || "YENİ HARF") + "   " + kok.harf.toLocaleUpperCase(Qt.locale("tr_TR"))
        color: r.vurgu_yazi
        font { family: pencere.yaziTipi; pixelSize: 16; weight: Font.Bold; letterSpacing: 2 }
    }

    SequentialAnimation {
        id: akis
        ParallelAnimation {
            NumberAnimation { target: kok; property: "opacity"; to: 1; duration: 140 }
            NumberAnimation { target: kok; property: "scale"; from: 0.6; to: 1.1; duration: 180; easing.type: Easing.OutCubic }
        }
        NumberAnimation { target: kok; property: "scale"; to: 1.0; duration: 120 }
        PauseAnimation { duration: 2200 }
        NumberAnimation { target: kok; property: "opacity"; to: 0; duration: 400 }
    }
}
