import QtQuick

QtObject {
    id: cal
    property int days: 7
    property int weeks: 6
    property int firstDayOfWeek: 1
    property var today: new Date()
    property int year: today.getFullYear()
    property int month: today.getMonth() + 1 // 1-based in KDE

    function goToYearAndMonth(y, m) {
        year = y;
        month = m;
    }

    property QtObject daysModel: QtObject {
        id: dm
        signal agendaUpdated(var date)

        function setPluginsManager(mgr) {}

        function eventsForDate(date) {
            if (typeof calendarBackendService !== "undefined" && calendarBackendService) {
                return calendarBackendService.getEventsForDate(date);
            }
            return [];
        }
    }
}
