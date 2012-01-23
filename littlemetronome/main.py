#!/usr/bin/env python
from datetime import datetime
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
VERSION = u"0.1"
WEBSITE = "http://29a.ch/"

sink_config = "autoaudiosink"
rate = 48000.0
#freq = 400.0
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
        self.pattern = [(880, 0.8), (440, 0.5), (440, 0.5), (440, 0.5)]

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
        pattern = self.pattern
        pattern_len = len(pattern)
        for i in xrange(self.t, self.t+length):
            tsec = i/rate
            beats = bps*tsec
            envelope = 1.0-((( (beats%1.0)/bps -0.05)*20.0)**4.0)
            if envelope > 0.0:
                freq, amplitude = pattern[int(beats%pattern_len)]
                data.append(sin(tsec*freq*pi*2.0)*envelope*volume*amplitude)
            else:
                data.append(0.0)
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
        self.last_tap = datetime.now()

        self.init_ui()

    def init_ui(self):
        self.set_title(NAME)

        try:
            self.set_icon(mygtk.iconfactory.get_icon("littlemetronome", 128))
            pass
        except gobject.GError:
            print "could not load icon"

        self.set_default_size(400, 180)
        self.set_border_width(5)

        self.accel_group = gtk.AccelGroup()
        self.add_accel_group(self.accel_group)

        vbox = gtk.VBox()
        self.add(vbox)

        self.tempo = BPMScale(gtk.Adjustment(80.00, 10.00, 400.0, 1.0, 0.5))
        self.tempo.scale.connect("value-changed", self.tempo_changed)
        self.tempo_changed(self.tempo)

        self.pattern = gtk.Entry()
        self.pattern.set_tooltip_text('Rhythm pattern 0 = Silent, 1-9 = different beeps')
        self.pattern.connect("changed", self.pattern_changed)
        self.pattern.set_text("1222")

        form = mygtk.form([
            ('Tempo', self.tempo),
            ('Increase', None),
            ('Pattern', self.pattern)
        ])

        vbox.pack_start(form)

        buttonbox = gtk.HButtonBox()
        vbox.pack_end(buttonbox, False, False)

        self.play_button = gtk.ToggleButton(gtk.STOCK_MEDIA_PLAY)
        self.play_button.set_tooltip_text("Play (enter)")
        self.play_button.connect("toggled", self.play)
        self.play_button.set_use_stock(True)
        self.play_button.add_accelerator("clicked", self.accel_group, gtk.keysyms.Return, 0, ())
        buttonbox.pack_start(self.play_button, False, False)

        self.tap_button = gtk.Button('Tap')
        self.tap_button.set_tooltip_text('Tap tempo (space)')
        self.tap_button.connect("clicked", self.tap)
        self.tap_button.add_accelerator("clicked", self.accel_group, ord(' '), 0, ())
        buttonbox.pack_start(self.tap_button, False, False)

        self.volume_button = gtk.VolumeButton()
        self.volume_button.set_value(1.0)
        self.volume_button.set_relief(gtk.RELIEF_NORMAL)
        self.volume_button.connect("value-changed", self.volume_changed)
        self.volume_changed(self.volume_button, None)
        buttonbox.pack_start(self.volume_button, False, False)

        button_about = gtk.Button(stock=gtk.STOCK_ABOUT)
        button_about.connect("clicked", self.about)
        buttonbox.pack_end(button_about)

        self.connect("destroy", gtk.main_quit)

    def volume_changed(self, sender, _):
        self.metronome.volume = sender.get_value()

    def tempo_changed(self, sender):
        self.metronome.bpm = sender.get_value()

    def pattern_changed(self, sender):
        text = sender.get_text()
        #0, A5, A4, E4
        beeps = [(1.0, 0.0), 
                (880.0, 0.8),
                (440.0, 0.75),
                (392.0, 0.6),
                (349.23, 0.5),
                (329.63, 0.5),
                (293.66, 0.5),
                (261.63, 0.5),
                (246.94, 0.5),
                (220.00, 0.5)
                ]
        pattern = []
        for c in text:
            n = ord(c) - ord('0')
            if 0 <= n < len(beeps):
                pattern.append(beeps[n])
        if pattern:
            self.metronome.pattern = pattern

    def tap(self, sender):
        t = datetime.now()
        td = (t - self.last_tap).total_seconds()
        self.last_tap = t
        bpm = 60.0/td

        if bpm >= 20:
            self.tempo.scale.set_value(bpm)

    def play(self, sender):
        if sender.get_active():
            self.metronome.play()
        else:
            self.metronome.pause()

    def about(self, sender):
        """show an about dialog"""
        about = gtk.AboutDialog()
        about.set_transient_for(self)
        about.set_logo(mygtk.iconfactory.get_icon("littlemetronome", 128))
        about.set_name(NAME)
        about.set_version(VERSION)
        about.set_authors(["Jonas Wagner"])
#        about.set_translator_credits(_("translator-credits"))
        about.set_copyright("Copyright (c) 2011 Jonas Wagner")
        about.set_website(WEBSITE)
        about.set_website_label(WEBSITE)
        about.set_license("""
Copyright (C) 2011 Jonas Wagner
This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
""")
        about.run()
        about.destroy()




def run():
    metronome = Metronome(sink_config)

    win = MainWindow(metronome)
    win.show_all()

    gtk.main()


if __name__ == "__main__":
    run()
