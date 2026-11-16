import json
import sys
import time
import lvgl as lv
import network

# ny library
import urequests

from board_lvgl import start_board
from debug_log import log
from secrets import WIFI_SSID, WIFI_PASSWORD, API_key


#Här ska våra STATIONER med deras id som vi fick från API:et + de olika transport typerna
STATIONS = (
    ("Campus Gräsvik", "740032188"),
    ("Karlskrona C", "740000230"),
)
TRANSPORT_OPTIONS = ("Bus", "Train", "Ferry", "All")
TRANSPORT_MODES = ("BUS", "TRAIN", "BOAT", None)



class Application:
    def __init__(self):
        self.display, self.touch, self.handler = start_board()
        self.tile2_dark = False
        self.create_ui()
        self.connect_wifi()

        #Detta las till för att visa att vi väntar på första uppdateringen, annars visas bara "Welcome to the workshop" tills vi får data från API:et
        self.data_status = "Waiting for first update"
        self.fetch_trafiklab_data()

        log("student application ready")

    @staticmethod
    #Här är en funktion som ändrar färgen på bakgrunden och texten på en tile, vi bytte ut till skolans logga färg, alla tiles är samma färg
    def apply_tile_colors(tile, label, dark):
        tile.set_style_bg_opa(lv.OPA.COVER, 0)
        tile.set_style_bg_color(
            lv.color_hex(0x033B4A if dark else 0x055065), 0
        )
        label.set_style_text_color(lv.color_hex(0xFFFFFF), 0)

    def update_status(self):
        pass



    def fetch_trafiklab_data(self):
        # Här kollas om makapären har WIFI annars visas felmeddelandet
        if not network.WLAN(network.STA_IF).isconnected():
            self.tile2_label.set_text("Wi-Fi is not connected.")
            return

       
        stop_dropdown = getattr(self, 'stop_dropdown', None)
        stop_idx = stop_dropdown.get_selected() if stop_dropdown else 0
        stop_idx = min(max(stop_idx, 0), len(STATIONS) - 1)
        stop_name, area_id = STATIONS[stop_idx]

        self.tile2_label.set_text("Loading live data...")

        
        #Från trafiklab APIE url länken
        try:
            url = f"https://realtime-api.trafiklab.se/v1/departures/{area_id}?key={API_key}"
            response = urequests.get(url)
            data = response.json()
            response.close()

            lines = ["DEPARTURES", stop_name, ""]
            
            for dep in data.get("departures", [])[:3]:
                route = dep.get("route", {})
                line = route.get("designation") or "?"
                direction = route.get("direction") or "Unknown"
                
                time_raw = dep.get("realtime") or dep.get("scheduled", "")
                time_text = time_raw[11:16] if len(time_raw) >= 16 else "--:--"

                status = "CANCELLED" if dep.get("canceled") else "LIVE" if dep.get("is_realtime") else "SCHEDULED"

                lines.append(f"{time_text}  Line {line}")
                lines.append(direction)
                lines.append(status)
                lines.append("")

            lines.append("Data: Trafiklab.se")
            self.tile2_label.set_text("\n".join(lines))
            
        except Exception as e:
            self.tile2_label.set_text("Error loading data:\n" + str(e)[:50])




    def create_ui(self):
        'Function: Creates UI'
        self.tileview = lv.tileview(lv.screen_active())
        self.tileview.set_size(600, 450)
        self.tileview.set_scrollbar_mode(lv.SCROLLBAR_MODE.OFF)

        #Detta är vår US,2.1
        self.tile1 = self.tileview.add_tile(0, 0, lv.DIR.RIGHT)
        self.tile2 = self.tileview.add_tile(1, 0, lv.DIR.RIGHT | lv.DIR.LEFT)
        self.tile3 = self.tileview.add_tile(2, 0, lv.DIR.LEFT)


        self.tile1_label = lv.label(self.tile1)
        self.tile1_label.set_text(
        "Public Transport Info\nVersion 1.2\nGroup 21:\n"
        "* Blediona Huskaj\n* Alexandros Salama\n* Alan Khalil\n"
        "* Alind Khudeeda\n* Leon Bönström\n* Ahmad lahm-Alajanje"
        )
        self.tile1_label.set_style_text_font(lv.font_montserrat_28, 0)
        self.tile1_label.set_width(550)
        self.tile1_label.center()
        self.apply_tile_colors(self.tile1, self.tile1_label, False)



        self.tile2_label = lv.label(self.tile2)
        self.tile2_label.set_text(
            "DEPARTURES\nLoading live data...\n\n"
            "Data: Trafiklab.se "
        )
        self.tile2_label.set_style_text_font(lv.font_montserrat_28, 0)
        self.tile2_label.set_width(560)
        self.tile2_label.set_height(330)
        self.tile2_label.set_pos(24, 20)
        self.apply_tile_colors(self.tile2, self.tile2_label, False)


    #US3.1 Settings skärmen med alla inställningar
        settings_title = lv.label(self.tile3)
        settings_title.set_text("SETTINGS")
        settings_title.set_style_text_font(lv.font_montserrat_28, 0)
        self.apply_tile_colors(self.tile3, settings_title, False)
        settings_title.set_pos(250, 20)



    @staticmethod
    def connect_wifi():
        'Function: Connects to WiFi'
        log("connecting to Wi-Fi SSID: " + WIFI_SSID)
        station = network.WLAN(network.STA_IF)
        station.active(True)
        station.connect(WIFI_SSID, WIFI_PASSWORD)
        started = time.ticks_ms()
        while (not station.isconnected() and
               time.ticks_diff(time.ticks_ms(), started) < 15_000):
            time.sleep_ms(250)
        log("Wi-Fi connected" if station.isconnected()
            else "Wi-Fi could not connect (timeout)")


try:
    app = Application()
except Exception as error:
    log("FATAL: %r" % (error,))
    sys.print_exception(error)
    raise