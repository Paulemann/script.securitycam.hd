#!/usr/bin/python
# -*- coding: utf-8 -*-

# Import the modules
import os, time, random, string, sys, platform
import xbmc, xbmcaddon, xbmcgui, xbmcvfs
from threading import Thread

try:
    from urllib.request import build_opener, HTTPPasswordMgrWithDefaultRealm, HTTPBasicAuthHandler, HTTPDigestAuthHandler, Request
except ImportError:
    from urllib2 import build_opener, HTTPPasswordMgrWithDefaultRealm, HTTPBasicAuthHandler, HTTPDigestAuthHandler, Request

if sys.version_info.major < 3:
    INFO = xbmc.LOGNOTICE
    from xbmc import translatePath
else:
    INFO = xbmc.LOGINFO
    from xbmcvfs import translatePath

# Action IDs
ACTION_PREVIOUS_MENU = 10
ACTION_STOP = 13
ACTION_NAV_BACK = 92
ACTION_BACKSPACE = 110

ACTION_SELECT_ITEM = 7
#ACTION_SHOW_INFO = 11
#ACTION_CONTEXT_MENU = 117
#ACTION_ENTER = 135
#ACTION_MENU = 163

ACTION_MOVE_LEFT = 1
ACTION_MOVE_RIGHT = 2

REMOTE_0 = 58
REMOTE_1 = 59
REMOTE_2 = 60
REMOTE_3 = 61
REMOTE_4 = 62
REMOTE_5 = 63
REMOTE_6 = 64
REMOTE_7 = 65
REMOTE_8 = 66
REMOTE_9 = 67

MAXCAMS = 9

# Set plugin variables
__addon__        = xbmcaddon.Addon()
__addon_id__     = __addon__.getAddonInfo('id')
__addon_path__   = __addon__.getAddonInfo('path')
__profile__      = __addon__.getAddonInfo('profile')
__localize__     = __addon__.getLocalizedString
__settings__     = os.path.join(__profile__, 'settings.xml')
__black__        = os.path.join(__addon_path__, 'resources', 'media', 'black.png')
__loading__      = os.path.join(__addon_path__, 'resources', 'media', 'loading.gif')
__btnTextureFO__ = os.path.join(__addon_path__, 'resources', 'media', 'buttonFO.png')
__btnTextureNF__ = os.path.join(__addon_path__, 'resources', 'media', 'buttonNF.png')

CAMERAS          = []

ffmpeg_exec      = 'ffmpeg.exe' if platform.system() == 'Windows' else 'ffmpeg'

# Utils
def log(message,loglevel=INFO):
    xbmc.log(msg='[{}] {}'.format(__addon_id__, message), level=loglevel)


def which(pgm):
    for path in os.getenv('PATH').split(os.path.pathsep):
        p=os.path.join(path, pgm)
        if os.path.exists(p) and os.access(p, os.X_OK):
            return p
    return None

# Classes
class CamSelectDialog(xbmcgui.WindowDialog):
    def __init__(self, max):
        self.select = None
        self.button = []

        lblHeight  = 50
        btnWidth   = 80
        btnHeight  = 80
        btnPadding = 20
        btnFont    = 'font60'
        lblFont    = 'font45_title'
        lblColor   = '0xFFFFFFFF'
        btnColor   = '0xFFFFFFFF'
        btnColor2  = '0xFF000000'

        posX       = (1280 - 3*btnWidth - 4*btnPadding) // 2
        posY       = (720 - lblHeight - 3*btnHeight - 4*btnPadding) // 2

        self.addControl(xbmcgui.ControlImage(posX, posY, 3*btnWidth + 4*btnPadding, lblHeight + 3*btnHeight + 4*btnPadding, __black__))
        self.addControl(xbmcgui.ControlLabel(posX, posY, 3*btnWidth + 4*btnPadding, lblHeight, __localize__(35000), alignment = 6, font = lblFont, textColor = lblColor))

        for i in range(0, 9):
            self.button.append(xbmcgui.ControlButton(posX + btnPadding + (i%3)*(btnWidth + btnPadding),
                                                     posY + lblHeight + btnPadding + (i//3)*(btnHeight + btnPadding),
                                                     btnWidth,
                                                     btnHeight,
                                                     str(i + 1),
                                                     focusTexture = __btnTextureFO__,
                                                     noFocusTexture = __btnTextureNF__,
                                                     alignment = 6,
                                                     font = btnFont,
                                                     textColor = btnColor,
                                                     focusedColor = btnColor2))
            self.addControl(self.button[-1])

        for i in range(0, 9):
            if i < 8:
                self.button[i].controlRight(self.button[i + 1])
            else:
                self.button[i].controlRight(self.button[0])

            if i > 0:
                self.button[i].controlLeft(self.button[i - 1])
            else:
                self.button[i].controlLeft(self.button[8])

            if i < 3:
                self.button[i].controlUp(self.button[6 + i])
            else:
                self.button[i].controlUp(self.button[i - 3])

            if i < 6:
                self.button[i].controlDown(self.button[3 + i])
            else:
                self.button[i].controlDown(self.button[i - 6])

            if i < max:
                self.button[i].setVisible(True)
            else:
                self.button[i].setVisible(False)


    def start(self):
        self.setFocus(self.button[0])
        self.doModal()

        return self.select


    def onControl(self, control):
        self.select = int(control.getLabel())
        self.close()


    def onAction(self, action):
        if action.getId() in (ACTION_PREVIOUS_MENU, ACTION_STOP, ACTION_BACKSPACE, ACTION_NAV_BACK):
            self.close()


class CamPreviewDialog(xbmcgui.WindowDialog):
    def __init__(self, cameras, zoom=None):
        grid_coords = [
                  [(320,180,640,360)],
                  [(0,180,640,360),(640,180,640,360)],
                  [(0,0,640,360),(640,0,640,360),(180,360,640,360)],
                  [(0,0,640,360),(640,0,640,360),(0,360,640,360),(640,360,640,360)],
                  [(0,120,427,240),(427,120,427,240),(854,120,427,240),(214,360,427,240),(640,360,427,240)],
                  [(0,120,427,240),(427,120,427,240),(854,120,427,240),(0,360,427,240),(427,360,427,240),(854,360,427,240)],
                  [(0,0,427,240),(427,0,427,240),(854,0,427,240),(214,240,427,240),(640,240,427,240),(214,480,427,240),(640,480,427,240)],
                  [(0,0,427,240),(427,0,427,240),(854,0,427,240),(0,240,427,240),(427,240,427,240),(854,240,427,240),(214,480,427,240),(640,480,427,240)],
                  [(0,0,427,240),(427,0,427,240),(854,0,427,240),(0,240,427,240),(427,240,427,240),(854,4800,427,240),(0,480,427,240),(427,480,427,240),(854,480,427,240)]
                  ]

        posX       = 5
        posY       = 5
        lblWidth   = 80
        lblHeight  = 80
        lblFont    = 'font_clock'
        lblColor   = '0xFFFFFFFF'

        self.threads = []

        self.zoom   = zoom
        self.select = None

        if self.zoom:
            self.cams = [cameras[self.zoom - 1].copy()]
        else:
            self.cams = cameras

        self.total  = len(cameras)
        self.count  = len(self.cams)

        passwd_mgr = HTTPPasswordMgrWithDefaultRealm()
        self.opener = build_opener()

        self.addControl(xbmcgui.ControlImage(0, 0, 1280, 720, __black__))

        for i in range(self.count):
            if self.cams[i]['username'] and self.cams[i]['password']:
                passwd_mgr.add_password(None, self.cams[i]['url'], self.cams[i]['username'], self.cams[i]['password'])
                self.opener.add_handler(HTTPBasicAuthHandler(passwd_mgr))
                self.opener.add_handler(HTTPDigestAuthHandler(passwd_mgr))

            randomname = ''.join([random.choice(string.ascii_letters + string.digits) for n in range(32)])
            self.cams[i]['tmpdir'] = os.path.join(__profile__, randomname)
            if not xbmcvfs.exists(self.cams[i]['tmpdir']):
                xbmcvfs.mkdir(self.cams[i]['tmpdir'])

            if self.zoom:
                self.cams[i]['x'], self.cams[i]['y'], self.cams[i]['width'], self.cams[i]['height'] = 0, 0, 1280, 720
            elif not SETTINGS['customGrid']:
                self.cams[i]['x'], self.cams[i]['y'], self.cams[i]['width'], self.cams[i]['height'] = grid_coords[self.count - 1][i]

            self.cams[i]['control'] = xbmcgui.ControlImage(
                self.cams[i]['x'], self.cams[i]['y'], self.cams[i]['width'], self.cams[i]['height'],
                __black__, aspectRatio = self.cams[i]['aspectRatio'])
            self.addControl(self.cams[i]['control'])

        if self.zoom:
            self.addControl(xbmcgui.ControlLabel(posX, posY, lblWidth, lblHeight, str(self.zoom), alignment = 6, font = lblFont, textColor = lblColor))


    def start(self):
        self.show()

        while True:
            while self.select:
                camZoom = CamPreviewDialog(self.cams, self.select)
                self.select = camZoom.start()
                del camZoom

            for i in range(self.count):
                self.cams[i]['control'].setImage(__loading__, False)

            self.stopFlag = False

            for i in range(self.count):
                t = Thread(target=self.update, args=(self.cams[i], lambda: self.stopFlag))
                t.start()
                self.threads.append(t)

            startTime = time.time()
            while(not SETTINGS['autoClose'] or (time.time() - startTime) * 1000 <= SETTINGS['duration']):
                if self.stopFlag:
                    break
                xbmc.sleep(500)

            self.stopFlag = True

            for t in self.threads:
                del t
            self.threads = []

            if self.zoom or not self.select:
                break

        self.close()
        self.cleanup()

        return self.select


    def update(self, cam, stop):
        request = Request(cam['url'])
        old_snapshot = None
        index = 1

        type = cam['url'][:4]

        if type == 'rtsp':
            if not which(ffmpeg_exec):
                log('Error: {} not installed. Can\'t process rtsp input format.'.format(ffmpeg_exec))
                self.stop()
                return

            if cam['username'] and cam['password']:
                input = 'rtsp://{}:{}@{}'.format(cam['username'], cam['password'], cam['url'][7:])
            else:
                input = cam['url']

            output = os.path.join(cam['tmpdir'], 'snapshot_%06d.jpg')
            command = [ffmpeg_exec,
                      '-nostdin',
                      '-rtsp_transport', 'tcp',
                      '-i', input,
                      '-an',
                      '-f', 'image2',
                      '-vf', 'fps=fps='+str(int(1000.0/SETTINGS['interval'])),
                      '-q:v', '10',
                      '-s', str(cam['width'])+'x'+str(cam['height']),
                      '-vcodec', 'mjpeg',
                      translatePath(output)]
            p = subprocess.Popen(command)

        while(not stop()):
            snapshot = os.path.join(cam['tmpdir'], 'snapshot_{:06d}.jpg'.format(index))
            if index > 1:
                old_snapshot = os.path.join(cam['tmpdir'], 'snapshot_{:06d}.jpg'.format(index - 1))
            index += 1

            try:
                if type == 'http':
                    imgData = self.opener.open(request).read()

                    if imgData:
                        file = xbmcvfs.File(snapshot, 'wb')
                        file.write(bytearray(imgData))
                        file.close()

                elif type == 'rtsp':
                    while(not stop()):
                        if xbmcvfs.exists(snapshot):
                            break
                        xbmc.sleep(10)

                elif xbmcvfs.exists(cam['url']):
                    xbmcvfs.copy(cam['url'], snapshot)

            except Exception as e:
                log(str(e))
                #snapshot = __loading__
                snapshot = None

            if snapshot:
                cam['control'].setImage(snapshot, False)

            if old_snapshot:
                xbmcvfs.delete(old_snapshot)

            if type != 'rtsp':
                xbmc.sleep(SETTINGS['interval'])

        if type == 'rtsp' and p.pid:
            p.terminate()


    def cleanup(self):
        for i in range(self.count):
            files = xbmcvfs.listdir(self.cams[i]['tmpdir'])[1]
            for file in files:
                xbmcvfs.delete(os.path.join(self.cams[i]['tmpdir'], file))
            xbmcvfs.rmdir(self.cams[i]['tmpdir'])


    def onAction(self, action):
        log('Action ID: {}'.format(action.getId()))
        if action.getId() in (ACTION_PREVIOUS_MENU, ACTION_STOP, ACTION_BACKSPACE, ACTION_NAV_BACK):
            self.select = None
            self.stop()

        if action.getId() in range(REMOTE_1, REMOTE_9 + 1): # and self.total > 1:
            if (action.getId() - REMOTE_0) > self.total:
                return
            self.select = action.getId() - REMOTE_0
            self.stop()

        if self.zoom and action.getId() == ACTION_MOVE_RIGHT:
            if self.zoom < self.total:
                self.select = self.zoom + 1
                self.stop()

        if self.zoom and action.getId() == ACTION_MOVE_LEFT:
            if self.zoom > 1:
                self.select = self.zoom - 1
                self.stop()

        if not self.zoom and action.getId() == ACTION_SELECT_ITEM: # and self.count > 1:
            camSelect = CamSelectDialog(self.total)
            self.select = camSelect.start()
            del camSelect
            self.stop()


    def stop(self):
        self.stopFlag = True


if __name__ == '__main__':
    if not xbmcvfs.exists(__settings__):
        xbmc.executebuiltin('Addon.OpenSettings(' + __addon_id__ + ')')

    # Get settings
    SETTINGS = {
        'interval':     int(float(__addon__.getSetting('interval'))),
        'autoClose':    bool(__addon__.getSetting('autoClose') == 'true'),
        'duration':     int(float(__addon__.getSetting('duration')) * 1000),
        'customGrid':   bool(__addon__.getSetting('customGrid') == 'true')
        }

    for i in range(MAXCAMS):
        if __addon__.getSetting('active{:d}'.format(i + 1)) == 'true':
            cam = {
                'url':          __addon__.getSetting('url{:d}'.format(i + 1)),
                'username':     __addon__.getSetting('username{:d}'.format(i + 1)),
                'password':     __addon__.getSetting('password{:d}'.format(i + 1)),
                'aspectRatio':  int(float(__addon__.getSetting('aspectRatio{:d}'.format(i + 1)))),
                'x':            int(float(__addon__.getSetting('posx{:d}'.format(i + 1)))),
                'y':            int(float(__addon__.getSetting('posy{:d}'.format(i + 1)))),
                'width':        int(float(__addon__.getSetting('width{:d}'.format(i + 1)))),
                'height':       int(float(__addon__.getSetting('height{:d}'.format(i + 1))))
                }
            CAMERAS.append(cam)

    camPreview = CamPreviewDialog(CAMERAS)
    camPreview.start()

    del camPreview
