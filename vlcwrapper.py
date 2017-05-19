#!/usr/bin/env python3
import sys
import os
import subprocess
from time import sleep
import threading
import time

HOME = os.environ['HOME']
CACHE = '{}/.cache/vlcwrapper'.format(HOME)

class Played(object):
    def __init__(self, fpath):
        self.fpath = fpath
        token = fpath.rstrip('/').replace('/', '!')
        self.cache = '{}/{}'.format(CACHE, token)
        self.running = False

    def update_metadata(self):
        with open(self.cache, 'w+') as f:
            while self.running:
                f.seek(0)
                metadata = self.get_metadata()
                if metadata[0]:
                    f.write('\n'.join(metadata+['']))
                for i in range(8):
                    if not self.running:
                        break
                    sleep(0.25)


    def get_metadata(self):
        try:
            res = [subprocess.check_output(['playerctl', 'metadata', 'xesam:title']).decode().strip(), subprocess.check_output(['playerctl', 'position']).decode().strip()]
            return res
        except:
            running = False
            raise

    def start(self):
        fpath = self.fpath
        curr = None
        pos = None
        if os.path.isfile(self.cache):
            with open(self.cache) as f:
                curr = f.readline().strip()
                pos = f.readline().strip()
        argv = sys.argv
        try:
            self.vlc = subprocess.Popen(['vlc', self.fpath])
            self.running = True
            t = time.time()
            LIMIT=4
            while time.time() < t + LIMIT:
                try:
                    subprocess.check_call(['playerctl', 'status'])
                    break
                except subprocess.CalledProcessError:
                    sleep(0.5)
            if curr:
                sleep(1)
                while subprocess.check_output(['playerctl', 'metadata', 'xesam:title']).decode() != curr:
                    subprocess.check_call(['playerctl', 'next'])
                    sleep(0.1)
                subprocess.check_call(['playerctl', 'position', str(float(pos) - 5)])
            subprocess.call(['player', 'play'])
            sleep(1)
            t = threading.Thread(target=self.update_metadata)
            t.start()
        except:
            self.stop()
        else:
            self.vlc.wait()
            self.running = False

    def stop(self):
        try:
            self.vlc.terminate()
        finally:
            self.running = False
            self.vlc.wait()

def play(path):
    fpath = os.path.abspath(path)
    played = Played(fpath)
    played.start()

def choise():
    from cursesmenu import SelectionMenu
    elems = []
    for name in os.listdir(CACHE):
        path = name.replace('!', '/')
        f = os.path.join(CACHE, name)
        mtime = os.stat(f).st_mtime
        with open(f) as ff:
            curr = ff.readline().strip('\n')
            pos = ff.readline().strip('\n')
        if curr:
            elems.append((mtime, path, curr, float(pos)))

    files = ('{} {}:{:02d} |{}'.format(k, int(l//60), int(l%60), j)  for _, j, k, l in reversed(sorted(elems)))
    menu = SelectionMenu(files, title='Recently Played')
    menu.show()
    s = menu.selected_item.text
    if s == 'Exit':
        return s
    else:
        return s.split('|')[1]

if __name__ == "__main__":
    if len(sys.argv) > 1:
        play(sys.argv[1])
    else:
        c = choise()
        if c != 'Exit':
            play(c)

