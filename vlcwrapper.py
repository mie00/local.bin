#!/usr/bin/env python3
import sys
import os
import subprocess
from time import sleep
import threading
import time
import curses
import urllib.parse
from cursesmenu import CursesMenu, SelectionMenu

class MySelectionMenu(SelectionMenu):
    def __init__(self, *args, cb=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.cb = cb

    def _main_loop(self, scr):
        if scr is not None:
            CursesMenu.stdscr = scr
        self.screen = curses.newpad(len(self.items) + 6, CursesMenu.stdscr.getmaxyx()[1])
        self._set_up_colors()
        curses.curs_set(0)
        CursesMenu.stdscr.refresh()
        self.draw()
        CursesMenu.currently_active_menu = self
        self._running.set()
        while self._running.wait() is not False and not self.should_exit:
            ui = self.process_user_input()
            if self.cb:
                self.cb(self, ui)



HOME = os.environ['HOME']
CACHE = '{}/.cache/vlcwrapper'.format(HOME)
THUMBS = '{}/thumbs'.format(CACHE)

for d in (CACHE, THUMBS):
    os.makedirs(d, exist_ok=True)

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
            res = [subprocess.check_output(['playerctl', 'metadata', 'xesam:title']).decode().strip(), subprocess.check_output(['playerctl', 'position']).decode().strip(), subprocess.check_output(['playerctl', 'metadata', 'xesam:url']).decode()]
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
    elems = []
    thumbs = os.listdir(THUMBS)
    for name in os.listdir(CACHE):
        if not name.startswith('!'):
            continue
        path = name.replace('!', '/')
        f = os.path.join(CACHE, name)
        mtime = os.stat(f).st_mtime
        with open(f) as ff:
            curr = ff.readline().strip('\n')
            pos = ff.readline().strip('\n')
            t = '{}:{:02d}'.format(int(float(pos)//60), int(float(pos)%60))
            fname = ff.readline().strip('\n')
        if curr:
            thumbpre = name + '!'
            thumbname = '{}!{}{}.png'.format(thumbpre, curr, pos)
            found = False
            for thumb in thumbs[:]:
                if thumb.startswith(thumbpre):
                    if thumb == thumbname:
                        found = True
                    else:
                        os.remove(os.path.join(THUMBS, thumb))
                    break
            if found == False:
                fname = fname[len('file://'):] if fname.startswith('file://') else fname
                fname = urllib.parse.unquote(fname)
                c = subprocess.call(['ffmpeg', '-ss' , t, '-i', fname , '-vf', 'scale=320:-1', '-q:v', '4', '-vframes', '1', os.path.join(THUMBS, thumbname)])
                if c == 0:
                    found = True

            thumb = os.path.join(THUMBS, thumbname) if found else ''
            elems.append((mtime, path, curr, t, thumb))

    files = []
    sitems = list(reversed(sorted(elems)))
    for _, j, k, l, _ in sitems:
        files.append('{} {} |{}'.format(k, l, j))
    def image(menu, x):
        if x == ord('s') and menu.current_option < len(sitems):
            t = sitems[menu.current_option][4]
            if t:
                subprocess.call(['pxl', t])
                menu.clear_screen()
                os.system('reset')
                curses.noecho()
                curses.cbreak()
                menu.stdscr.keypad(True)
                menu.draw()
        if x == ord('q'):
            menu.go_to(len(sitems))
            menu.select()
    menu = MySelectionMenu(files, title='Recently Played', cb=image)
    menu.show()
    s = menu.selected_option
    if s >= len(sitems):
        return None
    else:
        return sitems[s][1]

if __name__ == "__main__":
    if len(sys.argv) > 1:
        play(sys.argv[1])
    else:
        c = choise()
        if c is not None:
            play(c)

