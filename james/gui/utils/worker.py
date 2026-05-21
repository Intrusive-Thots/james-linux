from PyQt5.QtCore import pyqtSignal, QThread


class WorkerThread(QThread):
    finished = pyqtSignal(object)

    def __init__(self, target, *args, **kwargs):
        super().__init__()
        self.target = target
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            result = self.target(*self.args, **self.kwargs)
            self.finished.emit(result)
        except Exception as e:
            self.finished.emit(e)
