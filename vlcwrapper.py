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

    def remove_item(self, i):
        self.items.pop(i)
        if self.screen:
            self.clear_screen()
            self.draw()



HOME = os.environ['HOME']
CACHE = '{}/.cache/vlcwrapper'.format(HOME)
THUMBS = '{}/thumbs'.format(CACHE)
VIEWER = 'feh'

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
                if metadata[0] or metadata[2]:
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
        fname = None
        if os.path.isfile(self.cache):
            with open(self.cache) as f:
                curr = f.readline().strip()
                pos = f.readline().strip()
                fname = f.readline().strip()
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
            if fname:
                sleep(1)
                while subprocess.check_output(['playerctl', 'metadata', 'xesam:url']).decode() != fname:
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
            if pos:
                t = '{}:{:02d}'.format(int(float(pos)//60), int(float(pos)%60))
            else:
                t = '0:00'
            fname = ff.readline().strip('\n')
            fname = fname[len('file://'):] if fname.startswith('file://') else fname
            fname = urllib.parse.unquote(fname)
            curr = curr if curr else fname.split('/')[-1]
        if fname:
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
                c = subprocess.call(['ffmpeg', '-ss' , t, '-i', fname , '-vf', 'scale=320:-1', '-q:v', '4', '-vframes', '1', os.path.join(THUMBS, thumbname)])
                if c == 0:
                    found = True

            thumb = os.path.join(THUMBS, thumbname) if found else ''
            elems.append((mtime, path, curr, t, thumb))

    files = []
    sitems = list(reversed(sorted(elems)))
    for _, j, k, l, _ in sitems:
        files.append('{} {} |{}'.format(k, l, j))
    lastchar = [None]
    def image(menu, x):
        if x == ord('s') and menu.current_option < len(sitems):
            t = sitems[menu.current_option][4]
            if t:
                if VIEWER == 'pxl':
                    subprocess.call(['pxl', t])
                    menu.clear_screen()
                    os.system('reset')
                    curses.noecho()
                    curses.cbreak()
                    menu.stdscr.keypad(True)
                    menu.draw()
                elif VIEWER == 'feh':
                    subprocess.call(['feh', t])
        elif lastchar[0] == 'd' and x == ord('y'):
            os.remove(os.path.join(CACHE, sitems[menu.current_option][1].replace('/', '!')))
            os.remove(sitems[menu.current_option][4])
            sitems.pop(menu.current_option)
            menu.remove_item(menu.current_option)
        elif x == ord('q'):
            menu.go_to(len(sitems))
            menu.select()
        lastchar[0] = chr(x)
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

