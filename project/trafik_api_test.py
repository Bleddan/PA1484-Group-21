import requests
from secrets import API_key

stationer = {
    "Karlskrona C": "740000230",
    "Campus Gräsvik": "740032188"
}

for namn, area_id in stationer.items():
    url = f"https://realtime-api.trafiklab.se/v1/departures/{area_id}?key={API_key}"
    
    try:
        response = requests.get(url)
        data = response.json()
        response.close()
        
        print(f"--- Avgångar för {namn} ---")
        departures = data.get("departures", [])
        
        for dep in departures[:4]:
            # Hämta linjenummer och destination från route-objektet
            route = dep.get("route", {})
            line = route.get("designation", "Okänd linje")
            direction = route.get("direction", "Okänd destination")
            
            # Hämta realtid i första hand, annars tidtabellstid
            time_raw = dep.get("realtime") or dep.get("scheduled", "")
            time_str = time_raw[11:16] if len(time_raw) >= 16 else "--:--"
            
            print(f"  * Linje {line} mot {direction} kl {time_str}")
        print("\n")
        
    except Exception as e:
        print(f"Ett fel uppstod för {namn}: {e}\n")