#!/usr/bin/env python3
# -*- coding: utf-8 -*- 

import sys
from ..util.json_service import JsonService, send
from .volume_changer import VolumeChanger


class VolumeService(JsonService):

    def __init__(self):
        print("Key Binding Service")
        self.vc = VolumeChanger()
        super().__init__()
        
    def on_read(self, data):
        if data["func"] not in ("press","release") or not isinstance(data["button"],bool):
            return print("[%s] invalid message."%self.__class__.__name__, file=sys.stderr)
        getattr(self.vc, data["func"])(data["button"])
        

def main():
    VolumeService().mainloop()
    
if __name__ == "__main__":
    main()

