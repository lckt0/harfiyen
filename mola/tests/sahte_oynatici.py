#!/usr/bin/env python3
"""Ses çalmayan sahte MPRIS oynatıcısı: Pause/Play çağrılarını stdout'a yazar."""
import sys

import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

AD = "org.mpris.MediaPlayer2.harfiyentest"
OYNATICI = "org.mpris.MediaPlayer2.Player"


class Sahte(dbus.service.Object):
    def __init__(self, bus):
        super().__init__(bus, "/org/mpris/MediaPlayer2")
        self.durum = "Playing"

    def _durum(self, durum):
        self.durum = durum
        self.PropertiesChanged(OYNATICI, {"PlaybackStatus": durum}, [])

    @dbus.service.method(OYNATICI)
    def Pause(self):
        self._durum("Paused")
        print("Pause", flush=True)

    @dbus.service.method(OYNATICI)
    def Play(self):
        self._durum("Playing")
        print("Play", flush=True)

    @dbus.service.signal(dbus.PROPERTIES_IFACE, signature="sa{sv}as")
    def PropertiesChanged(self, arayuz, degisen, gecersiz):
        pass

    @dbus.service.method(dbus.PROPERTIES_IFACE, in_signature="ss", out_signature="v")
    def Get(self, arayuz, ozellik):
        if ozellik == "PlaybackStatus":
            return self.durum
        if ozellik == "Identity":
            return "Sahte Oynatıcı"
        raise dbus.exceptions.DBusException("yok")


DBusGMainLoop(set_as_default=True)
bus = dbus.SessionBus()
ad = dbus.service.BusName(AD, bus)
nesne = Sahte(bus)
print("hazir", flush=True)
GLib.MainLoop().run()
