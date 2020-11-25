import ac
import acsys
import ctypes
import os, threading, json, math
import gzip
#import time
from .util.func import rgb, getFontSize
from .util.classes import Window, Label, Value, Colors, Config, Log, Button, raceGaps

        
class ACDelta:
    resetPressed = False
    configChanged = False
    ui_row_height = 42

    # INITIALIZATION
    def __init__(self): 
        self.window = Window(name="ACTV Delta", icon=False, width=240, height=246, texture="")
        self.cursor = Value(False)
        self.session = Value(-1)
        self.performance = Value(0)
        self.performance_session = Value(0)
        self.spline = Value(0)
        self.laptime = Value(0)
        self.TimeLeftUpdate = Value(0)
        self.referenceLap = []
        self.referenceLap_session = []
        self.referenceLapTime = Value(0)
        self.referenceLapTime_session = Value(0)
        self.lastLapTime = Value(0)
        self.lapCount = 0
        self.lastLapIsValid = True
        self.currentLap = []
        self.deltaLoaded = False
        self.thread_save = False
        self.highlight_end = 0
        self.rowHeight = Value(-1)
        self.lbl_delta = Label(self.window.app, "+0.000")\
            .set(w=150, h=36,
                 x=0, y=60,
                 font_size=26,
                 align="right",
                 visible=1)
        self.lbl_session_delta = Label(self.window.app, "+0.000")\
            .set(w=150, h=36,
                 x=0, y=40,
                 font_size=14,
                 align="right",
                 visible=1)
        self.lbl_lap = Label(self.window.app, "0.000")\
            .set(w=150, h=32,
                 x=0, y=80,
                 font_size=17,
                 align="right",
                 visible=1)
        self.btn_reset = Button(self.window.app, self.on_reset_press)\
            .setPos(90, 68).setSize(60, 20)\
            .setText("Reset")\
            .setAlign("center")\
            .setBgColor(rgb([255, 12, 12], bg=True))\
            .setVisible(0)
        self.spin_row_height = ac.addSpinner(self.window.app, "")
        ac.setRange(self.spin_row_height, 20, 70)
        ac.setPosition(self.spin_row_height, 20, 28)
        ac.setValue(self.spin_row_height, self.__class__.ui_row_height)
        ac.addOnValueChangeListener(self.spin_row_height, self.on_spin_row_height_changed)
        ac.setVisible(self.spin_row_height, 0)
        font_name = "Segoe UI"
        if ac.initFont(0, font_name, 0, 0) > 0:
            self.lbl_delta.setFont(font_name, 0, 1)
            self.lbl_session_delta.setFont(font_name, 0, 1)
        self.cfg = Config("apps/python/prunn/", "config.ini")
        self.load_cfg()
            
    @staticmethod
    def on_spin_row_height_changed(value):
        ACDelta.ui_row_height = value
        ACDelta.configChanged = True
        
    @staticmethod
    def on_reset_press(a, b):
        ACDelta.resetPressed = True
                
    # PUBLIC METHODS
    def load_cfg(self):
        self.__class__.ui_row_height = self.cfg.get("DELTA", "delta_row_height", "int")
        ac.setValue(self.spin_row_height, self.__class__.ui_row_height)
        self.redraw_size()
            
    def save_cfg(self):
        self.redraw_size()
        self.cfg.set("DELTA", "delta_row_height", self.__class__.ui_row_height)
            
    def redraw_size(self):
        if self.__class__.ui_row_height > 0:
            self.rowHeight.setValue(self.__class__.ui_row_height)
        else:
            self.rowHeight.setValue(38)
        if self.rowHeight.hasChanged():
            font_size = getFontSize(self.rowHeight.value)
            row_height = self.rowHeight.value-16
            font_size2 = getFontSize(row_height)
            # width=self.rowHeight*5
            self.lbl_delta.setSize(row_height/24*32 + 120, self.rowHeight.value)\
                .setFontSize(font_size)
            self.lbl_session_delta.setSize(row_height/24*32 + 120, row_height)\
                .setY(60 - font_size2*0.7, True).setFontSize(font_size2)
            self.lbl_lap.setSize(row_height/24*32 + 120, row_height)\
                .setY(63 + font_size, True)\
                .setFontSize(font_size2)
            self.btn_reset.setSize(self.rowHeight.value + 26, row_height)\
                .setPos(90, font_size*2 + 60)\
                .setFontSize(font_size2)
        
    def get_delta_file_path(self):
        track_file_path = os.path.join(os.path.expanduser("~"), "Documents", "Assetto Corsa", "plugins", "actv_deltas", "default")
        if not os.path.exists(track_file_path):
            os.makedirs(track_file_path)
        track_file_path += "/" + ac.getTrackName(0)
        if ac.getTrackConfiguration(0) != "":
            track_file_path += "_" + ac.getTrackConfiguration(0)
        track_file_path += "_" + ac.getCarName(0) + ".delta"
        return track_file_path
    
    def save_delta(self):
        reference_lap = list(self.referenceLap)
        reference_lap_time = self.referenceLapTime.value
        if len(reference_lap) > 0:
            try:
                times = []
                for l in reference_lap:
                    times.append((l.sector, l.time))
                data_file = {
                            'lap': reference_lap_time,
                            'times': times, 
                            'track': ac.getTrackName(0), 
                            'config': ac.getTrackConfiguration(0), 
                            'car': ac.getCarName(0), 
                            'user': ac.getDriverName(0)
                            }                  
                file = self.get_delta_file_path()
                with gzip.open(file, 'wt') as outfile:
                    json.dump(data_file, outfile)
            except:
                Log.w("Error tower")
        
    def load_delta(self):
        self.deltaLoaded = True
        file = self.get_delta_file_path()
        if os.path.exists(file):
            try:
                with gzip.open(file, 'rt') as data_file:   
                    data = json.load(data_file)
                    self.referenceLapTime.setValue(data["lap"])                    
                    times = data["times"]
                    self.referenceLap = []
                    for t in times:
                        self.referenceLap.append(raceGaps(t[0], t[1]))
                    ac.console("AC Delta: File loaded")
            except:
                Log.w("Error tower")  
     
    def get_performance_gap(self, sector, time):
        if len(self.referenceLap) < 10:
            return round(ac.getCarState(0, acsys.CS.PerformanceMeter)*1000)
        if sector > 0.5:
            reference_lap = reversed(self.referenceLap)
        else:
            reference_lap = self.referenceLap
        for l in reference_lap:
            if l.sector == sector:
                return time - l.time
        return False  # do not update

    def get_performance_session_gap(self, sector, time):
        if len(self.referenceLap_session) < 10:
            return round(ac.getCarState(0, acsys.CS.PerformanceMeter)*1000)
        if sector > 0.5:
            reference_lap = reversed(self.referenceLap_session)
        else:
            reference_lap = self.referenceLap_session
        for l in reference_lap:
            if l.sector == sector:
                return time - l.time
        return False  # do not update
    
    def time_splitting(self, ms, full="no"):
        s = ms/1000
        m, s = divmod(s, 60)
        h, m = divmod(m, 60)
        # d, h = divmod(h,24)
        if full == "yes":
            d = ms % 1000
            if h > 0:
                return "{0}:{1}:{2}.{3}".format(int(h), str(int(m)).zfill(2), str(int(s)).zfill(2), str(int(d)).zfill(3))
            elif m > 0:  
                return "{0}:{1}.{2}".format(int(m), str(int(s)).zfill(2), str(int(d)).zfill(3))
            else:
                return "{0}.{1}".format(int(s), str(int(d)).zfill(3))
        else:
            d = ms / 100 % 10
            if h > 0:
                return "{0}:{1}:{2}.{3}".format(int(h), str(int(m)).zfill(2), str(int(s)).zfill(2), int(d))
            elif m > 0:  
                return "{0}:{1}.{2}".format(int(m), str(int(s)).zfill(2), int(d))
            else:
                return "{0}.{1}".format(int(s), int(d))             
        
    def manage_window(self, game_data):
        win_x = self.window.getPos().x
        win_y = self.window.getPos().y
        if win_x > 0:
            self.window.last_x = win_x
            self.window.last_y = win_y
        else:
            self.window.setLastPos()
            win_x = self.window.getPos().x
            win_y = self.window.getPos().y
        if win_x < game_data.cursor_x < win_x + self.window.width and win_y < game_data.cursor_y < win_y + self.window.height:
            self.cursor.setValue(True)
        else:
            self.cursor.setValue(False)
        session_changed = self.session.hasChanged()
        if session_changed:
            self.reset_data()
        if self.cursor.hasChanged() or session_changed:
            if self.cursor.value:
                self.window.setBgOpacity(0.4).border(0)
                self.window.showTitle(True)
                self.btn_reset.setVisible(1)
                ac.setVisible(self.spin_row_height, 1)
            else:
                self.window.setBgOpacity(0).border(0)
                self.window.showTitle(False) 
                self.btn_reset.setVisible(0)
                ac.setVisible(self.spin_row_height, 0)
                
    def reset_data(self):
        self.currentLap = []
        self.referenceLap_session = []
        self.lastLapIsValid = True
        self.lapCount = 0
        self.highlight_end = 0
        self.referenceLapTime_session.setValue(0)
        self.performance_session.setValue(0)
                    
    def on_update(self, sim_info, game_data):
        if self.__class__.configChanged:
            self.save_cfg()
            self.__class__.configChanged = False
        if not self.deltaLoaded:
            thread_load = threading.Thread(target=self.load_delta)
            thread_load.daemon = True      
            thread_load.start() 
        if self.__class__.resetPressed:
            self.referenceLapTime.setValue(0)
            self.referenceLapTime_session.setValue(0)
            self.referenceLap = []
            self.referenceLap_session = []
            self.__class__.resetPressed = False
        self.session.setValue(game_data.session)
        self.manage_window(game_data)
        self.lbl_delta.animate()
        self.lbl_session_delta.animate()
        self.lbl_lap.animate()
        sim_info_status = game_data.status
        if sim_info_status == 2:  # LIVE
            session_time_left = game_data.sessionTimeLeft
            if session_time_left == 0:
                self.reset_data()
            elif game_data.beforeRaceStart:
                self.reset_data()
            elif bool(ac.isCarInPitline(0)) or bool(ac.isCarInPit(0)):
                self.reset_data()
            self.spline.setValue(round(ac.getCarState(0, acsys.CS.NormalizedSplinePosition), 3))
            
            if self.lastLapIsValid and sim_info.physics.numberOfTyresOut >= 4:
                self.lastLapIsValid = False
            
            if self.spline.hasChanged():
                self.laptime.setValue(round(ac.getCarState(0, acsys.CS.LapTime), 3))
                self.lastLapTime.setValue(ac.getCarState(0, acsys.CS.LastLap))
                gap = self.get_performance_gap(self.spline.value, self.laptime.value)
                if gap != False:
                    self.performance.setValue(gap)
                gap = self.get_performance_session_gap(self.spline.value, self.laptime.value)
                if gap != False:
                    self.performance_session.setValue(gap)
                # new lap
                if self.lastLapTime.hasChanged():
                    if (self.referenceLapTime.value == 0 or self.lastLapTime.value < self.referenceLapTime.value) and self.lastLapIsValid and self.lastLapTime.value > 0 and self.lapCount < ac.getCarState(0, acsys.CS.LapCount):  
                        self.referenceLapTime.setValue(self.lastLapTime.value)
                        self.referenceLapTime_session.setValue(self.lastLapTime.value)

                        self.referenceLap_session = self.referenceLap = list(self.currentLap)
                        if len(self.referenceLap) > 2000:  # 2laps in
                            ac.console("too many laps in reference----")
                            ac.log("too many laps in reference----")
                            how_much = math.floor(len(self.referenceLap)/1000)
                            del self.referenceLap[0:math.floor(len(self.referenceLap)/how_much)]
                            self.referenceLap_session = self.referenceLap

                        thread_save = threading.Thread(target=self.save_delta)
                        thread_save.daemon = True
                        thread_save.start()
                        # make it green for 5 sec
                        self.highlight_end = session_time_left - 6000
                        self.lbl_lap.setColor(Colors.green(), True)
                    elif (self.referenceLapTime.value == 0 or self.lastLapTime.value < self.referenceLapTime_session.value) and self.lastLapIsValid and self.lastLapTime.value > 0 and self.lapCount < ac.getCarState(0, acsys.CS.LapCount):
                        self.referenceLapTime_session.setValue(self.lastLapTime.value)
                        self.referenceLap_session = list(self.currentLap)
                        if len(self.referenceLap_session) > 2000:  # 2laps in
                            ac.console("too many laps in referenceLap_session----")
                            ac.log("too many laps in referenceLap_session----")
                            how_much = math.floor(len(self.referenceLap_session)/1000)
                            del self.referenceLap_session[0:math.floor(len(self.referenceLap_session)/how_much)]

                    self.currentLap = []
                    self.lapCount = ac.getCarState(0, acsys.CS.LapCount)
                    self.lastLapIsValid = True
                    
                self.currentLap.append(raceGaps(self.spline.value, self.laptime.value))
            
            # update graphics
            self.TimeLeftUpdate.setValue(int(session_time_left/500))
            if self.TimeLeftUpdate.hasChanged():    
                if self.performance.hasChanged():
                    time_prefix = ""
                    color = Colors.white()
                    if self.performance.value > 0:
                        time_prefix = "+"
                        if self.lastLapIsValid:
                            color = Colors.yellow()
                        else:
                            color = Colors.red()
                    elif self.performance.value < 0:
                        time_prefix = "-"
                        if self.lastLapIsValid:
                            color = Colors.green()
                        else:
                            color = Colors.orange()
                    else:
                        if not self.lastLapIsValid:
                            color = Colors.red()
                    self.lbl_delta.setText(time_prefix + self.time_splitting(abs(self.performance.value), "yes"))\
                        .setColor(color, True)
                if self.performance_session.hasChanged():
                    if self.referenceLapTime.value != self.referenceLapTime_session.value and (self.laptime.value >= 8000 or self.lastLapTime.value == 0):
                        time_prefix = ""
                        color = Colors.white()
                        if self.performance_session.value > 0:
                            time_prefix = "+"
                            if self.lastLapIsValid:
                                color = Colors.yellow()
                            else:
                                color = Colors.red()
                        elif self.performance_session.value < 0:
                            time_prefix = "-"
                            if self.lastLapIsValid:
                                color = Colors.green()
                            else:
                                color = Colors.orange()
                        else:
                            if not self.lastLapIsValid:
                                color = Colors.red()
                        self.lbl_session_delta.setText(time_prefix + self.time_splitting(abs(self.performance_session.value), "yes"))\
                            .setColor(color, True)
                    else:
                        # showlastlap
                        color = Colors.white()
                        #if not self.lastLapIsValid:
                        #    color = Colors.red()
                        self.lbl_session_delta.setText("L: " + self.time_splitting(self.lastLapTime.value, "yes")).setColor(color, True)

            if self.referenceLapTime.hasChanged():
                self.lbl_lap.setText(self.time_splitting(self.referenceLapTime.value, "yes"))
            if self.highlight_end == 0 or session_time_left < self.highlight_end:
                self.lbl_lap.setColor(Colors.white(), True)
