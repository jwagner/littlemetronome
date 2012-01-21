#!/usr/bin/env python
from math import sin, pi
import sys


# INIT GTK and GST

argv = sys.argv
# work around gstreamer parsing sys.argv!
sys.argv = []
import gobject
gobject.threads_init()

import pygtk
pygtk.require('2.0')

import pygst
pygst.require('0.10')

import gst, gtk

# always enable button images
gtk.settings_get_default().set_long_property("gtk-button-images", True, "main")
sys.argv = argv

from . import mygtk
mygtk.install()

from array import array

NAME = u"Little Metronome"

sink_config = "autoaudiosink"
rate = 48000.0
freq = 400.0
volume = 0.5
t = 0

if len(argv) > 1:
    bpm = float(argv[1])
else:
    bpm = 60
bps = bpm/60.0

class Metronome(object):
    def __init__(self, sink_config):
        self.pipeline = gst.Pipeline()
        self.t = 0
        self.bpm = 80
        self.volume = 0.5

        source = gst.element_factory_make("appsrc")
        source_caps = gst.Caps('audio/x-raw-float,rate=(int)%i,channels=(int)1,width=(int)32,endianness=(int)1234' % rate)
        source.connect('need-data', self._need_data)
        source.set_property('caps', source_caps)

        convert = gst.element_factory_make("audioconvert")

        sink = gst.parse_bin_from_description(sink_config, True)

        self.pipeline.add_many(source, convert, sink)
        gst.element_link_many(source, convert, sink)

    def _need_data(self, src, length):
        data = array('f')
        bps = self._bps
        volume = self.volume
        for i in xrange(self.t, self.t+length):
            tsec = i/rate
            envelope = max(0.0, 1.0-((( ((tsec*bps)%1.0)/bps -0.05)*20.0)**4.0))
            #on = 1/((tsec*bps)%1.0)
            sample = sin(tsec*freq*pi*2.0)*envelope*volume
            data.append(sample)
        self.t += length
        src.emit('push-buffer', gst.Buffer(data))


    def get_bpm(self):
        return self._bpm

    def set_bpm(self, value):
        self._bpm = value
        self._bps = value/60.0

    bpm = property(get_bpm, set_bpm)

    def play(self):
        self.t = 0
        self.pipeline.set_state(gst.STATE_PLAYING)

    def pause(self):
        self.pipeline.set_state(gst.STATE_PAUSED)

class BPMScale(mygtk.TextScale):
    format = "%.1f BPM "
    size = 10


class MainWindow(gtk.Window):
    def __init__(self, metronome):
        gtk.Window.__init__(self,gtk.WINDOW_TOPLEVEL)

        self.metronome = metronome

        self.init_ui()

    def init_ui(self):
        self.set_title(NAME)

        try:
            self.set_icon(mygtk.iconfactory.get_icon("littlemetronome", 128))
            pass
        except gobject.GError:
            print "could not load icon"

        self.set_default_size(500, 200)
        self.set_border_width(5)

        self.accel_group = gtk.AccelGroup()
        self.add_accel_group(self.accel_group)

        vbox = gtk.VBox()
        self.add(vbox)

        tempo = BPMScale(gtk.Adjustment(80.00, 10.00, 400.0, 1.0, 0.5))
        tempo.scale.connect("value-changed", self.tempo_changed)
        self.tempo_changed(tempo)

        form = mygtk.form([
            ('Tempo', tempo),
            ('Increase', None),
            ('Meter', None),
            ('Pattern', None)
        ])

        vbox.pack_start(form)

        buttonbox = gtk.HButtonBox()
        vbox.pack_end(buttonbox, False, False)

        self.play_button = gtk.ToggleButton(gtk.STOCK_MEDIA_PLAY)
        self.play_button.connect("toggled", self.play)
        self.play_button.set_use_stock(True)
        self.play_button.add_accelerator("clicked", self.accel_group, gtk.keysyms.Return, 0, ())
        buttonbox.pack_start(self.play_button, False, False)

        self.volume_button = gtk.VolumeButton()
        self.volume_button.set_value(1.0)
        self.volume_button.set_relief(gtk.RELIEF_NORMAL)
        self.volume_button.connect("value-changed", self.volume_changed)
        self.volume_changed(self.volume_button, None)
        buttonbox.pack_start(self.volume_button, False, False)

        self.connect("destroy", gtk.main_quit)

    def volume_changed(self, sender, _):
        self.metronome.volume = sender.get_value()

    def tempo_changed(self, sender):
        self.metronome.bpm = sender.get_value()

    def play(self, sender):
        if sender.get_active():
            self.metronome.play()
        else:
            self.metronome.pause()


if __name__ == "__main__":
    metronome = Metronome(sink_config)

    win = MainWindow(metronome)
    win.show_all()

    gtk.main()
