from PyQt5.QtCore import QObject, pyqtSignal

class SignalBus(QObject):
    sensors_updated = pyqtSignal()
    gait_events_updated = pyqtSignal()
    planners_updated = pyqtSignal()
