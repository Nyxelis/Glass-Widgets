import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import "components"

PlasmoidItem {
    id: root

    Plasmoid.backgroundHints: PlasmaCore.Types.NoBackground

    WidgetActions { id: commonActions }

    Plasmoid.contextualActions: commonActions.list
    preferredRepresentation: fullRepresentation

    MacOSColors {
        id: colors
        styleMode: plasmoid.configuration.styleMode
        appearance: plasmoid.configuration.appearance
    }

    FontLoader {
        id: sfRegular
        source: Qt.resolvedUrl("../../../../1-common/fonts/sf_pro_display_regular.otf")
    }

    // Editable text state
    property bool isEditing: false
    property string draftText: ""
    property string currentText: {
        if (typeof windowController !== "undefined" && windowController && windowController.glassText !== undefined) {
            return windowController.glassText;
        }
        if (typeof widgetManagerService !== "undefined" && widgetManagerService && widgetManagerService.glassText !== undefined) {
            return widgetManagerService.glassText;
        }
        if (plasmoid && plasmoid.configuration && plasmoid.configuration.glassText !== undefined) {
            return plasmoid.configuration.glassText;
        }
        return "Liquid gLASS";
    }

    function saveGlassText(val) {
        currentText = val;
        if (typeof windowController !== "undefined" && windowController) {
            windowController.setGlassText(val);
        } else if (typeof widgetManagerService !== "undefined" && widgetManagerService) {
            widgetManagerService.setGlassText(val);
        }
        if (plasmoid && plasmoid.configuration) {
            plasmoid.configuration.glassText = val;
        }
    }

    Connections {
        target: typeof widgetManagerService !== "undefined" ? widgetManagerService : null
        function onGlassTextChanged(newVal) {
            if (!root.isEditing) {
                root.currentText = newVal;
            }
        }
    }

    fullRepresentation: Item {
        id: full
        anchors.fill: parent
        Layout.preferredWidth:  width  > 0 ? width  : 200
        Layout.preferredHeight: height > 0 ? height : 200
        Layout.minimumWidth: 120
        Layout.minimumHeight: 120

        readonly property bool isHovered: rootHover.hovered

        // Modern Qt6 non-blocking hover detection across full widget
        HoverHandler {
            id: rootHover
            cursorShape: root.isEditing ? Qt.IBeamCursor : Qt.PointingHandCursor
        }

        // Modern Qt6 non-blocking tap detection for edit mode
        TapHandler {
            id: rootTap
            acceptedButtons: Qt.LeftButton
            enabled: !root.isEditing

            onDoubleTapped: {
                if (!root.isEditing) {
                    root.draftText = root.currentText;
                    root.isEditing = true;
                    if (typeof windowController !== "undefined" && windowController && windowController.requestActivate) {
                        windowController.requestActivate();
                    }
                    textEdit.forceActiveFocus();
                    textEdit.selectAll();
                }
            }

            onSingleTapped: {
                if (root.currentText.trim().length === 0 && !root.isEditing) {
                    root.draftText = "";
                    root.isEditing = true;
                    if (typeof windowController !== "undefined" && windowController && windowController.requestActivate) {
                        windowController.requestActivate();
                    }
                    textEdit.forceActiveFocus();
                }
            }
        }

        // 1. Liquid Glass Surface: strictly anchored to root widget, sensible 16px corner radius
        LiquidGlass {
            id: glass
            anchors.fill: parent
            width: parent.width
            height: parent.height
            radius: 16
            roundness: 2.2
            refractThickness: plasmoid.configuration.refractThickness
            refractIOR: plasmoid.configuration.refractIORx100 / 100
            refractScale: plasmoid.configuration.refractScale
            tint: colors.glassTint
            tintAlpha: full.isHovered ? Math.min(1.0, (plasmoid.configuration.tintAlphaPct / 100) + 0.05) : (plasmoid.configuration.tintAlphaPct / 100)
            chromaStrength: plasmoid.configuration.chromaStrengthPct / 100
            specStrength: full.isHovered ? (plasmoid.configuration.specStrengthPct / 100) * 1.35 : (plasmoid.configuration.specStrengthPct / 100)
            blurRadius: plasmoid.configuration.blurRadiusPx
            blurAlgorithm: plasmoid.configuration.blurAlgorithm
            realtimeRefraction: plasmoid.configuration.realtimeRefraction
            fallbackOpacity: colors.glassFallbackOpacity
            solidMode: colors.isSolid
            solidColor: colors.solidBackground

            Behavior on tintAlpha {
                NumberAnimation { duration: 200; easing.type: Easing.OutCubic }
            }
            Behavior on specStrength {
                NumberAnimation { duration: 200; easing.type: Easing.OutCubic }
            }
        }

        // 2. Bounded Inner Text Box: 24px margins so text never crowds edges or overlaps buttons
        Item {
            id: textContainer
            anchors.fill: parent
            anchors.margins: 24
            clip: true
            z: 2

            // Auto-Fitting Display Text
            Text {
                id: displayText
                anchors.fill: parent
                visible: !root.isEditing && root.currentText.trim().length > 0
                text: root.isEditing ? textEdit.text : root.currentText
                color: colors.foreground
                font.family: sfRegular.status === FontLoader.Ready ? sfRegular.name : "Segoe UI, -apple-system, sans-serif"
                font.pixelSize: Math.max(18, Math.min(48, Math.round(Math.min(full.height, full.width) * 0.22)))
                font.weight: Font.DemiBold
                minimumPixelSize: 11
                fontSizeMode: Text.Fit
                wrapMode: Text.WordWrap
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                lineHeight: 1.15
            }

            // Empty State Placeholder
            Text {
                id: placeholderText
                anchors.fill: parent
                visible: !root.isEditing && root.currentText.trim().length === 0
                text: "Click to edit"
                color: colors.foreground
                font.family: sfRegular.status === FontLoader.Ready ? sfRegular.name : "Segoe UI, -apple-system, sans-serif"
                font.pixelSize: Math.max(12, Math.round(full.height * 0.08))
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                opacity: full.isHovered ? 0.65 : 0.0
                Behavior on opacity { NumberAnimation { duration: 200 } }
            }

            // Edit Mode: TextEdit with consistent font size, wrapping and centering
            Rectangle {
                id: editFrame
                anchors.fill: parent
                visible: root.isEditing
                radius: 10
                color: Qt.rgba(0, 0, 0, 0.40)
                border.color: "#0a84ff"
                border.width: 1.5

                TextEdit {
                    id: textEdit
                    anchors.fill: parent
                    anchors.margins: 8
                    text: root.draftText
                    color: colors.foreground
                    font.family: sfRegular.status === FontLoader.Ready ? sfRegular.name : "Segoe UI, -apple-system, sans-serif"
                    font.pixelSize: displayText.fontInfo.pixelSize
                    font.weight: Font.DemiBold
                    wrapMode: TextEdit.WordWrap
                    horizontalAlignment: TextEdit.AlignHCenter
                    verticalAlignment: TextEdit.AlignVCenter
                    selectByMouse: true

                    onVisibleChanged: {
                        if (visible) {
                            forceActiveFocus();
                            selectAll();
                        }
                    }

                    Keys.onReturnPressed: (event) => {
                        if (event.modifiers & Qt.ControlModifier || event.modifiers & Qt.ShiftModifier) {
                            textEdit.insert(textEdit.cursorPosition, "\n");
                        } else {
                            root.saveGlassText(textEdit.text);
                            root.isEditing = false;
                            event.accepted = true;
                        }
                    }

                    Keys.onEnterPressed: (event) => {
                        root.saveGlassText(textEdit.text);
                        root.isEditing = false;
                        event.accepted = true;
                    }

                    Keys.onEscapePressed: (event) => {
                        root.isEditing = false;
                        event.accepted = true;
                    }

                    onActiveFocusChanged: {
                        if (!activeFocus && root.isEditing) {
                            root.saveGlassText(textEdit.text);
                            root.isEditing = false;
                        }
                    }
                }
            }
        }

        // 3. Quick Clear ('X') Button on hover
        Rectangle {
            id: clearBtn
            anchors.top: parent.top
            anchors.right: parent.right
            anchors.margins: 10
            width: 22
            height: 22
            radius: 11
            color: clearHover.hovered ? "#ef4444" : Qt.rgba(1, 1, 1, 0.18)
            visible: full.isHovered && !root.isEditing && root.currentText.trim().length > 0
            opacity: visible ? 1.0 : 0.0
            z: 10
            Behavior on color { ColorAnimation { duration: 150 } }
            Behavior on opacity { NumberAnimation { duration: 150 } }

            Text {
                anchors.centerIn: parent
                text: "×"
                color: "#ffffff"
                font.pixelSize: 14
                font.bold: true
            }

            HoverHandler {
                id: clearHover
                cursorShape: Qt.PointingHandCursor
            }

            TapHandler {
                acceptedButtons: Qt.LeftButton
                onSingleTapped: {
                    root.saveGlassText("");
                }
            }
        }
    }
}
