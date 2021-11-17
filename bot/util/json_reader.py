import json
import pathlib
import traceback


class JsonReader:
    def __init__(self, config_file: pathlib.Path):
        self.config_file = config_file
        self.data = {}    # noqa: WPS110
        self.loadfile()

    def loadfile(self):
        try:
            data = self.config_file.read_text()    # noqa: WPS110
        except Exception:
            traceback.print_exc()
            return
        self.data = json.loads(data)    # noqa: WPS110

    def __getitem__(self, item):    # noqa: WPS110
        return self.data[item]

    def __contains__(self, item):    # noqa: WPS110
        return item in self.data
