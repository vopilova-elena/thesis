import datetime

class Logger:
    def __init__(self):
        pass

    @staticmethod
    def get_current_time():
        return datetime.datetime.now().strftime("%H:%M:%S")