import sys
import time

import lvgl as lv
import network

from board_lvgl import start_board
from debug_log import log
from secrets import WIFI_SSID, WIFI_PASSWORD


class Application:
    def __init__(self):
        self.display, self.touch, self.handler = start_board()
        self.tile2_dark = False
        self.create_ui()
        self.connect_wifi()
        log("student application ready")

    @staticmethod
    def apply_tile_colors(tile, label, dark):
        """Apply matching background and text colours."""
        tile.set_style_bg_opa(lv.OPA.COVER, 0)
        tile.set_style_bg_color(
            lv.color_hex(0x000000 if dark else 0xFFFFFF), 0
        )
        label.set_style_text_color(
            lv.color_hex(0xFFFFFF if dark else 0x000000), 0
        )

    def on_tile2_clicked(self, _event):
        """Toggle the colours on the second screen."""
        self.tile2_dark = not self.tile2_dark
        self.apply_tile_colors(
            self.tile2, self.tile2_label, self.tile2_dark
        )

    def create_ui(self):
        """Create the startup screen and the workshop screen."""
        self.tileview = lv.tileview(lv.screen_active())
        self.tileview.set_size(600, 450)
        self.tileview.set_scrollbar_mode(lv.SCROLLBAR_MODE.OFF)

        self.tile1 = self.tileview.add_tile(0, 0, lv.DIR.RIGHT)
        self.tile2 = self.tileview.add_tile(1, 0, lv.DIR.LEFT)

        # WBS 2.2 / FR1: project and team information.
        self.tile1_label = lv.label(self.tile1)
        self.tile1_label.set_text(
            "Public Transport Info\n"
            "Version 1.2\n"
            "Group 21\n\n"
            "Blediona Huskaj\n"
            "Alexandros Salama\n"
            "Alan Khalil\n"
            "Alind Khudeeda\n"
            "Leon Bönström\n"
            "Ahmad lahm-Alajanje"
        )
        self.tile1_label.set_style_text_font(lv.font_montserrat_28, 0)
        self.tile1_label.set_width(560)
        self.tile1_label.set_style_text_align(lv.TEXT_ALIGN.CENTER, 0)
        self.tile1_label.center()
        self.apply_tile_colors(self.tile1, self.tile1_label, False)

        self.tile2_label = lv.label(self.tile2)
        self.tile2_label.set_text("Welcome to the workshop")
        self.tile2_label.set_style_text_font(lv.font_montserrat_28, 0)
        self.tile2_label.center()
        self.apply_tile_colors(self.tile2, self.tile2_label, False)

        self.tile2.add_flag(lv.obj.FLAG.CLICKABLE)
        self.tile2.add_event_cb(
            self.on_tile2_clicked, lv.EVENT.CLICKED, None
        )

    @staticmethod
    def connect_wifi():
        """Connect to Wi-Fi with a 15-second timeout."""
        log("connecting to Wi-Fi SSID: " + WIFI_SSID)
        station = network.WLAN(network.STA_IF)
        station.active(True)
        station.connect(WIFI_SSID, WIFI_PASSWORD)

        started = time.ticks_ms()
        while (
            not station.isconnected()
            and time.ticks_diff(time.ticks_ms(), started) < 15_000
        ):
            time.sleep_ms(250)

        log(
            "Wi-Fi connected"
            if station.isconnected()
            else "Wi-Fi could not connect (timeout)"
        )


try:
    app = Application()
except Exception as error:
    log("FATAL: %r" % (error,))
    sys.print_exception(error)
    raise