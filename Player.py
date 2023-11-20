import os
from PyQt6 import QtWidgets, QtGui, QtCore
import re
from Logger import logger
from TracksModel import TracksModel
import vlc

PATTERN = r'.*\.(mp3|flac|aif|aiff)'
TAGS=["Catas", "Phiphi", "Deep", "Hard", "Retro", "Trance", "Best", "Ambiant", "Fun", "Zarb", "A Cappella"]
class Player(QtWidgets.QMainWindow):

    def __init__(self, conf):
        QtWidgets.QMainWindow.__init__(self, None)
        self.conf = conf
        self.setWindowTitle("Media Player")
        self.init_create_ui()
        self.keys = list(filter(lambda key_name: key_name[0:4] == 'Key_', dir(QtCore.Qt.Key)))
        # Create a basic vlc instance
        self.instance = vlc.get_default_instance()
        self.media = None
        # Create an empty vlc media player
        self.mediaplayer = self.instance.media_player_new()
        self.current_index = None

    def init_create_ui(self):
        self.widget = QtWidgets.QWidget(self)
        self.setCentralWidget(self.widget)
        self.setAcceptDrops(True)

        self.tagsbuttonbox = QtWidgets.QHBoxLayout()

        self.tagbutton = {}
        for tag in TAGS:
            self.tagbutton[tag] = QtWidgets.QPushButton(tag)
            self.tagbutton[tag].setCheckable(True)
            # self.tagbutton[tag].clicked[bool].connect(self.set_tags)
            self.tagbutton[tag].setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
            self.tagsbuttonbox.addWidget(self.tagbutton[tag])

        self.topzone = QtWidgets.QHBoxLayout()
        self.topzone.addLayout(self.tagsbuttonbox)

        # self.filelist = QtWidgets.QListView()
        self.filelist = QtWidgets.QTableView()
        self.filelist.clicked.connect(self.item_clicked)
        self.filelist.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.filelist.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)

        self.waveform = QtWidgets.QFrame()

        self.positionslider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal, self)
        self.positionslider.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.positionslider.setToolTip("Position")
        self.positionslider.setMaximum(1000)
        self.positionslider.sliderMoved.connect(self.set_position_from_slider)
        self.positionslider.sliderPressed.connect(self.set_position_from_slider)

        self.hbuttonbox = QtWidgets.QHBoxLayout()
        self.playbutton = QtWidgets.QPushButton("Play")
        self.hbuttonbox.addWidget(self.playbutton)
        self.playbutton.clicked.connect(self.play_pause)

        self.stopbutton = QtWidgets.QPushButton("Stop")
        self.hbuttonbox.addWidget(self.stopbutton)
        self.stopbutton.clicked.connect(self.stop)

        self.timelabel = QtWidgets.QLabel()
        # self.timelabel.setText(self.get_time_info())
        self.hbuttonbox.addWidget(self.timelabel)

        self.hbuttonbox.addStretch(1)
        self.volumeslider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal, self)
        self.volumeslider.setMaximum(100)
        # self.volumeslider.setValue(self.mediaplayer.audio_get_volume())
        self.volumeslider.setToolTip("Volume")
        self.hbuttonbox.addWidget(self.volumeslider)
        # self.volumeslider.valueChanged.connect(self.set_volume)

        self.lowzone = QtWidgets.QVBoxLayout()
        self.lowzone.addWidget(self.positionslider)
        self.lowzone.addLayout(self.hbuttonbox)

        self.vboxlayout = QtWidgets.QVBoxLayout()
        self.vboxlayout.addWidget(self.filelist)
        self.vboxlayout.addLayout(self.topzone)
        self.vboxlayout.addLayout(self.lowzone)

        self.widget.setLayout(self.vboxlayout)

        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.update_ui)


    # HANDLERS
    def update_ui(self):
        # Set the slider's position to its corresponding media position
        # Note that the setValue function only takes values of type int,
        # so we must first convert the corresponding media position.
        media_pos = int(self.mediaplayer.get_position() * 1000)
        self.positionslider.setValue(media_pos)
        self.timelabel.setText(self.get_time_info())

        # No need to call this function if nothing is played
        if not self.mediaplayer.is_playing():
            self.timer.stop()

            # After the video finished, the play button stills shows "Pause",
            # which is not the desired behavior of a media player.
            # This fixes that "bug".
            if not self.is_paused:
                self.stop()

    def dropEvent(self, e):
        dropped_data = e.mimeData().text()
        entries = dropped_data.split('\n')
        #.replace('file://','')
        # print(entries)
        if len(entries) == 0:
            print('0 entries dropped on app, ignoring')
            self.load_files([])
        elif len(entries) > 1:
            print('multiple entries dropped, keeping files only')
            self.load_files(entries)
        elif entries[0][-1] == '/':
            print('dropped a directory')
            self.load_dir(entries[0])
        else:
            print('dropped a file')
            self.load_files(entries)
        e.setDropAction(QtCore.Qt.DropAction.MoveAction)
        e.accept()

    def dragEnterEvent(self, e):
        e.accept()

    def keyPressEvent(self, event):
        key = event.key()
        # print('pressed from myDialog: ', key)
        if key == QtCore.Qt.Key.Key_Escape.value:
            self.close()
        logger.debug(self.key_to_enum(key))
        action = self.key_to_action(key)
        if (action):
            action()

    def item_clicked(self):
        self.select(self.filelist.currentIndex().row())
        self.load_current()
        self.play()

    def play_pause(self):
        if self.mediaplayer.is_playing():
            self.pause()
        else:
            self.play()


    def stop(self):
        self.mediaplayer.stop()
        # self.playbutton.setText("Play")

    def set_position_from_slider(self):
        '''
        this position comes from the slider which has a [0, 1000] range
        '''
        # TODO retrieve pos value from event
        # The vlc MediaPlayer needs a float value between 0 and 1, Qt uses
        # integer variables, so you need a factor; the higher the factor, the
        # more precise are the results (1000 should suffice).

        # Set the media position to where the slider was dragged
        pos = self.positionslider.value()
        self.set_position(pos/1000.0)

    # / HANDLERS

    # "Key_Escape": "quit"
    def key_to_action(self, key):
        actions = self.conf['actions']
        action_key = list(filter(lambda k: key == eval('QtCore.Qt.Key.'+k), actions.keys()))
        if (len(action_key) == 0):
            return None
        return eval(f'self.{actions[action_key[0]]}')

    ## Old version
    ##     "quit": "Key_Escape",
    # def key_to_action(self, key):
    #     actions = self.conf['actions']
    #     action_item = list(filter(lambda k: key == eval('QtCore.Qt.Key.'+actions[k]), actions.keys()))
    #     if (len(action_item) == 0):
    #         return None
    #     return eval(f'self.{action_item[0]}')

    def key_to_enum(self, key):
        keyname = list(filter(lambda k: key == eval('QtCore.Qt.Key.'+k), self.keys))
        if (len(keyname) == 0):
            return None
        return keyname[0]

    def load_dir(self, path):
        self.load_files(map(lambda f: path+f, sorted(os.listdir(path.replace('file://','')))))

    def load_files(self, filenames):
        self.update_tracklist(list(map(lambda f: f.replace('file://',''), filter(re.compile(PATTERN, re.IGNORECASE).match, filenames))))

    def update_tracklist(self, filepaths):
        self.track_model = TracksModel(tracks=filepaths)
        self.filelist.setModel(self.track_model)
        # self.filelist.resizeColumnsToContents()

    def load_track(self, fullpath):
        self.media = self.instance.media_new(fullpath)
        self.mediaplayer.set_media(self.media)
        self.media.parse()
        print('Artist', self.media.get_meta(vlc.Meta.Artist))
        print('Title', self.media.get_meta(vlc.Meta.Title))
        print('Genre', self.media.get_meta(vlc.Meta.Genre))

    def select(self, index: int = None, increment: int = None):
        if index != None and increment != None:
            logger.critical('Bad Coder')
            return
        elif increment != None:
            index = self.current_index
            if increment > 0:
                if index == None:
                    index = -1
                index += increment
            elif increment < 0:
                if index == None:
                    index = self.track_model.rowCount()
                index += increment

        if self.track_model.rowCount() == 0:
            index = None

        if index != None:
            if index < 0 or self.track_model.rowCount() <= index:
                index = (index + self.track_model.rowCount()) % self.track_model.rowCount()

            self.current_index = index
        # logger.debug(self.current_index)
        self.filelist.selectRow(self.current_index)


    def load_current(self):
        if self.current_index != None:
            track = self.track_model.get_track(self.current_index)
            self.load_track(track['fullname'])            

    def pause(self):
        self.mediaplayer.pause()
        self.playbutton.setText("Play")
        self.is_paused = True
        self.timer.stop()

    def play(self):
        if self.mediaplayer.play() == -1:
            self.open_file()
            return

        self.mediaplayer.play()
        # self.playbutton.setText("Pause")
        self.timer.start()
        self.is_paused = False


    def get_time_info(self):
        # if self.mediaplayer.is_playing():
        #     stars = '* '*self.rating + '_ '*(5-self.rating)
        #     return f'{self.milliseconds_to_string(self.mediaplayer.get_time())} / {self.milliseconds_to_string(self.media.get_duration())} -- {self.filesize} -- {self.bitrate} -- {stars}'
        return 'Stopped'

    def milliseconds_to_string(self, ms):
        m = int(ms / 60000)
        s = int(ms / 1000) % 60
        return f'{m}:{s:02}'
    
    def bytes_to_Mb(self, b):
        m = int(100 * b / 1024 / 1024) / 100
        return f'{m} Mb'

    # KEYBOARD ACTIONS
    def quit(self):
        print('QUIT') 
        self.close()
    
    def play_next_track(self):
        self.select(increment=1)
        self.load_current()
        self.play()
    
    def play_previous_track(self):
        self.select(increment=-1)
        self.load_current()
        self.play()
    
    def set_position(self, pos: float):
        self.timer.stop()
        self.mediaplayer.set_position(pos)
        self.timer.start()

    def step_backward(self, seconds: int):
        self.step_forward(-seconds)

    def step_forward(self, seconds: int):
        self.set_position((self.mediaplayer.get_time() + seconds * 1000) / self.media.get_duration())

    def move_to_dustbin(self):
        print("MOVE TO DUSTBIN")
    
    def keep_file(self):
        print("MOVE TO ")

    def incr_rating(self):
        if self.current_index != None:
            self.track_model.incr_rating(self.current_index)

    def set_style(self, style):
        print(f'style: {style}')
        if self.current_index != None:
            self.track_model.set_style(self.current_index, style)
    # / KEYBOARD ACTIONS