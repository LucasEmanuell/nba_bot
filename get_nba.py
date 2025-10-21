import requests
import json
from datetime import datetime
from database import db
from dateutil import parser

URL = "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_1.json"

def processar_calendario_nba():
    response = requests.get(URL)
    data = response.json()

    for dia in data["leagueSchedule"]["gameDates"]:
        game_date_str = dia["gameDate"]  # Formato: "10/02/2025 00:00:00"
        
        # Converter data para formato padrão
        game_date = datetime.strptime(game_date_str.split(" ")[0], "%m/%d/%Y")
        data_utc = game_date.strftime("%Y-%m-%d")
        
        for jogo in dia["games"]:
            home = jogo["homeTeam"]
            away = jogo["awayTeam"]
            
            # Extrair informações de transmissão original
            broadcasters = jogo.get("broadcasters", {}).get("nationalTvBroadcasters", [])
            canais = [b["broadcasterDisplay"] for b in broadcasters if b.get("broadcasterMedia") == "tv"]
            
            jogo_processado = {
                "game_id": jogo["gameId"],
                "data_utc": data_utc,
                "hora_utc": jogo["gameDateTimeUTC"],  # "2025-10-02T16:00:00Z"
                "mandante": f"{home['teamCity']} {home['teamName']}",
                "visitante": f"{away['teamCity']} {away['teamName']}",
                "canal_original": canais[0] if canais else "TBD",
                "canal_brasil": None  # Será preenchido pelo scraper
            }
            
            db.salvar_jogo(jogo_processado)

    print("Calendário NBA processado e salvo no banco de dados.")

if __name__ == "__main__":
    processar_calendario_nba()