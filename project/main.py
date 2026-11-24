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

Refresh_intervall = 60_000 #I milisekunder
#US3.4 Här sparas inställningarna
Settings_file = "settings.json"
#---------------------------------

class Application:
    def __init__(self):
        self.display, self.touch, self.handler = start_board()
        self.tile2_dark = False
        self.create_ui()

        #US3.4 Tog bort koden som tvingade inställningarna att visa Campus gräsvik (index 0) och transport typen "ALL" som va index 3. Nu läser den av settings saved filen istället.
        self.saved_stop_index, self.saved_transport_index = self.load_saved_settings()
        self.stop_dropdown.set_selected(self.saved_stop_index)
        self.transport_dropdown.set_selected(self.saved_transport_index)
        #----------------------------------------------------------------

        self.connect_wifi()

        #Detta las till för att visa att vi väntar på första uppdateringen, annars visas bara "Welcome to the workshop" tills vi får data från API:et
        self.data_status = "Waiting for first update"
        self.fetch_trafiklab_data()
        #4.1 Här bärjar timern ticka när ESP32 startar
        self.refresh_timer = lv.timer_create(self.when_auto_refresh, Refresh_intervall, None)
        log("student application ready")



    @staticmethod
    #Här är en funktion som ändrar färgen på bakgrunden och texten på en tile, vi bytte ut till skolans logga färg, alla tiles är samma färg
    def apply_tile_colors(tile, label, dark):
        tile.set_style_bg_opa(lv.OPA.COVER, 0)
        tile.set_style_bg_color(
            lv.color_hex(0x033B4A if dark else 0x055065), 0
        )
        label.set_style_text_color(lv.color_hex(0xFFFFFF), 0)


    # US4.3 (Wi-Fi & Data Status)
    # Funktionen som kollar systemets WIFI anslutning och uppdaterar texten
    def update_status(self):
        wifi_status = "Connected" if network.WLAN(network.STA_IF).isconnected() else "Disconnected"
        if hasattr(self, 'status_label'):
            self.status_label.set_text(f"Wi-Fi: {wifi_status}\nData: {self.data_status}")



    def fetch_trafiklab_data(self):
        # Här kollas om makapären har WIFI annars visas felmeddelandet
        if not network.WLAN(network.STA_IF).isconnected():
            self.tile2_label.set_text("Wi-Fi is not connected.")
            return

       # Vår valda hållplats
        stop_index = self.stop_dropdown.get_selected() if hasattr(self, 'stop_dropdown') else 0
        stop_index = min(max(stop_index, 0), len(STATIONS) - 1)
        stop_name, area_id = STATIONS[stop_index]

        # US3.3
        transport_index = self.transport_dropdown.get_selected() if hasattr(self, 'transport_dropdown') else 3
        transport_index = min(max(transport_index, 0), len(TRANSPORT_MODES) - 1)
        selected_mode = TRANSPORT_MODES[transport_index]

        self.tile2_label.set_text("Loading live data...")

        # U4.3 - 1
        self.data_status = "Updated"
        self.update_status()
        # -----------------------------------

        # Från trafiklab API url länken
        try:
            url = f"https://realtime-api.trafiklab.se/v1/departures/{area_id}?key={API_key}"
            response = urequests.get(url)
            data = response.json()
            response.close()

            lines = ["-------DEPARTURES-------", stop_name, ""]

            #US3.3 I denna for loop filtreras avgångarna beroende på den valda tranport typen man har valt, om man väljer "all" så visas alla avgångar
            # Dock den behöver en refresh för uppdatera datan
            matching_departures = []
            for dep in data.get("departures", []):
                route = dep.get("route", {})
                if selected_mode is None or route.get("transport_mode") == selected_mode:
                    matching_departures.append(dep)

            for dep in matching_departures[:3]:
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

            #Detta dycker upp om det inte finns avgångar för den valda transport typen
            if not matching_departures:
                lines.append("No departures found for the selected transport type.")

            #Denna ska vara längst ner på tilen när det inte finns transport 
            lines.append("Data: Trafiklab.se")
            self.tile2_label.set_text("\n".join(lines))
            
        except Exception as e:
            self.tile2_label.set_text("Error loading data:\n" + str(e)[:50])
            # U4.3 - 3
            self.data_status = "Update failed"
            self.update_status()
            # ------------------------------------------------




    def when_refresh_clicked(self, _event):
        self.fetch_trafiklab_data()

    #4.1 För hämta ny trafik data när den gör en auto refresh
    def when_auto_refresh(self, _timer):
        self.fetch_trafiklab_data()

    def action_button(self, parent, text, x, y, width, callback):
        button = lv.button(parent)
        button.set_size(width, 52)
        button.set_pos(x, y)
        button.set_style_bg_color(lv.color_hex(0x0B7688), 0)
        button.add_event_cb(callback, lv.EVENT.CLICKED, None)
        label = lv.label(button)
        label.set_text(text)
        label.set_style_text_font(lv.font_montserrat_20, 0)
        label.set_style_text_color(lv.color_hex(0xFFFFFF), 0)
        label.center()
        return button

    # US3.2B 
    # När användaren ändrar en dropdown, säger vi till dem via status-texten att de måste uppdatera manuellt för att se den nya datan.
    def on_settings_changed(self, _event):
        self.data_status = "Settings changed: tap Refresh"
        self.update_status()
    #------------------------------------------------------------------------

    #US3.4 Försöker läsa in tidigare sparade val från filen.
    # Det också om filen saknar eller innehåller fel värde då skickas stadnravärde 0 eller 3 tillbaka istället. 
    def load_saved_settings(self):
        try:
            with open(Settings_file,"r") as f:
                settings = json.load(f)
                stop_index = int(settings.get("stop", 0))
                transport_index = int(settings.get("transport",3))
                if stop_index not in range(len(STATIONS)): stop_index = 0
                if transport_index not in range(len(TRANSPORT_OPTIONS)): transport_index = 3
                return stop_index, transport_index
        except Exception:
            return 0, 3
    #-------------------------------------------------------------------------

    #US3.4 Hämtar de val som användaren just nu har gjort i dropdown menyn i inställningarna och sparar de i en JSON-fil så att den minns till nästa restart.
    def when_save_settings_clicked(self, _event):
        settings = {
            "stop": self.stop_dropdown.get_selected(),
            "transport": self.transport_dropdown.get_selected(),
        }
        try:
            with open(Settings_file, "w") as f:
                json.dump(settings, f)
            self.saved_stop_index = settings["stop"]
            self.saved_transport_index = settings["transport"]
            self.data_status = "Settings saved"
        except Exception:
            self.data_status = "Couldnt save settings"
        self.update_status()
    #--------------------------------------------------------------------


    # 3.5 - 1
    def when_reset_clicked(self, _event):
        self.stop_dropdown.set_selected(self.saved_stop_index)
        self.transport_dropdown.set_selected(self.saved_transport_index)
        self.stop_dropdown.send_event(lv.EVENT.VALUE_CHANGED, None)
        
        self.fetch_trafiklab_data()
    # ---------------------------------------------------


    def create_ui(self):
        'Function: Creates UI'
        self.tileview = lv.tileview(lv.screen_active())
        self.tileview.set_size(600, 450)
        self.tileview.set_scrollbar_mode(lv.SCROLLBAR_MODE.OFF)

        #Detta är vår US,2.1
        self.tile1 = self.tileview.add_tile(0, 0, lv.DIR.BOTTOM | lv.DIR.RIGHT)
        self.tile4 = self.tileview.add_tile(1, 0, lv.DIR.BOTTOM | lv.DIR.LEFT)
        self.tile2 = self.tileview.add_tile(0, 1, lv.DIR.TOP | lv.DIR.RIGHT)
        self.tile3 = self.tileview.add_tile(1, 1, lv.DIR.TOP | lv.DIR.LEFT)

        self.tile1_label = lv.label(self.tile1)
        self.tile1_label.set_text(
        "    ---------Public Transport Info---------\n                         Version 1.2     \n                         Group 21 \n"
        "* Blediona Huskaj\n* Alexandros Salama\n* Alan Khalil\n"
        "* Alind Khudeeda\n* Leon Bönström\n* Ahmad lahm-Alajanje"
        )


        self.tile1_label.set_style_text_font(lv.font_montserrat_28, 0)
        self.tile1_label.set_width(550)
        self.tile1_label.center()
        self.apply_tile_colors(self.tile1, self.tile1_label, False)


        self.tile2_label = lv.label(self.tile2)
        self.tile2_label.set_text(
            "        ------DEPARTURES------\nLoading live data...\n\n"
            "Data: Trafiklab.se "
        )
        self.tile2_label.set_style_text_font(lv.font_montserrat_28, 0)
        self.tile2_label.set_width(560)
        self.tile2_label.set_height(330)
        self.tile2_label.set_pos(40, 20)
        self.apply_tile_colors(self.tile2, self.tile2_label, False)
        self.action_button(self.tile2, "Refresh", 390, 380, 170, self.when_refresh_clicked)

        #US3.4 Själva "Save" knappen
        self.action_button(self.tile3, "Save", 24, 340, 176, self.when_save_settings_clicked)
        #--------------------------------------------------

        # 3.5 - 2
        self.action_button(self.tile3, "Reset", 212, 340, 176, self.when_reset_clicked)
        # ---------------------------------------------------

        #US3.1 Settings skärmen med alla inställningar
        settings_title = lv.label(self.tile3)
        settings_title.set_text("-----SETTINGS-----")
        settings_title.set_style_text_font(lv.font_montserrat_28, 0)
        self.apply_tile_colors(self.tile3, settings_title, False)
        settings_title.set_pos(150, 20)

        #US4.2 vår knapp i tile 2 och 3
        self.action_button(self.tile3, "Refresh",400,340,176, self.when_refresh_clicked)

        # US4.3: Wi-Fi och datastatus
        # Detta gör så att användaren kan kan se nätverkstatusen på inställningarna
        self.status_label = lv.label(self.tile3)
        self.status_label.set_text("Wi-Fi: checking..\nLive Data: waiting..")
        self.status_label.set_style_text_font(lv.font_montserrat_20, 0)
        self.status_label.set_style_text_color(lv.color_hex(0xFFFFFF), 0)
        self.status_label.set_pos(40, 230)
        #------------------------------------------------

        #US5.1 Journey skärm
        self.tile4_label = lv.label(self.tile4)
        self.tile4_label.set_text( "-----Journey Screen-----      " )
        self.tile4_label.set_style_text_font(lv.font_montserrat_28, 0)
        self.apply_tile_colors(self.tile4, self.tile4_label, False)
        self.tile4_label.set_pos(150, 20)


        # US3.2B Val av hållplats ligger här 
        stop_label = lv.label(self.tile3)
        stop_label.set_text("Choose a stop station:")
        stop_label.set_style_text_font(lv.font_montserrat_20, 0)
        stop_label.set_style_text_color(lv.color_hex(0xFFFFFF), 0)
        stop_label.set_pos(40, 60)
        self.stop_dropdown = lv.dropdown(self.tile3)
        self.stop_dropdown.set_options("\n".join(name for name, _ in STATIONS))
        self.stop_dropdown.set_size(520, 48)
        self.stop_dropdown.set_pos(40, 88)
        self.stop_dropdown.add_event_cb(self.on_settings_changed, lv.EVENT.VALUE_CHANGED, None)
        #-----------------------------------------------------------------------------------------
        #US3.3 Här väljs transporttyp dvs bus, tåg osv
        transport_label = lv.label(self.tile3)
        transport_label.set_text("Choose a transport type")
        transport_label.set_style_text_font(lv.font_montserrat_20, 0)
        transport_label.set_style_text_color(lv.color_hex(0xFFFFFF), 0)
        transport_label.set_pos(40, 145)
        self.transport_dropdown = lv.dropdown(self.tile3)
        self.transport_dropdown.set_options("\n".join(TRANSPORT_OPTIONS))
        self.transport_dropdown.set_size(520, 48)
        self.transport_dropdown.set_pos(40, 173)
        self.transport_dropdown.add_event_cb(
            self.on_settings_changed, lv.EVENT.VALUE_CHANGED, None
        )
        #-----------------------------------------------------------------------------------------

        self.add_swipe_indicator(self.tile1, f"Journey {lv.SYMBOL.RIGHT}", 450, 410)
        self.add_swipe_indicator(self.tile1, f"{lv.SYMBOL.DOWN} Departures", 40, 410)

        self.add_swipe_indicator(self.tile4, f"{lv.SYMBOL.LEFT} Start", 40, 410)
        self.add_swipe_indicator(self.tile4, f"{lv.SYMBOL.DOWN} Settings", 450, 410)

        self.add_swipe_indicator(self.tile2, f"{lv.SYMBOL.UP} Start", 40, 10)
        self.add_swipe_indicator(self.tile2, f"Settings {lv.SYMBOL.RIGHT}", 450, 10)

        self.add_swipe_indicator(self.tile3, f"{lv.SYMBOL.UP} Journey", 450, 10)
        self.add_swipe_indicator(self.tile3, f"{lv.SYMBOL.LEFT} Departures", 40, 10)

    def add_swipe_indicator(self, parent, text, x, y):
      # Svajp indikator
        indicator = lv.label(parent)
        indicator.set_text(text)
        indicator.set_style_text_font(lv.font_montserrat_16, 0)
        indicator.set_style_text_color(lv.color_hex(0x88CCDD), 0)  # Ljusare blå/turkos ton
        indicator.set_pos(x, y)
        return indicator


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