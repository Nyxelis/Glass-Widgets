pragma Singleton
import QtQuick

QtObject {
    readonly property real gridUnit: 18
    readonly property real smallSpacing: 4
    readonly property real mediumSpacing: 8
    readonly property real largeSpacing: 16
    readonly property int veryShortDuration: 100
    readonly property int shortDuration: 150
    readonly property int longDuration: 300
    readonly property int veryLongDuration: 400
    readonly property real devicePixelRatio: 1.0

    readonly property QtObject iconSizes: QtObject {
        readonly property int small: 16
        readonly property int smallMedium: 22
        readonly property int medium: 32
        readonly property int large: 48
        readonly property int huge: 64
        readonly property int enormous: 128
    }
}
