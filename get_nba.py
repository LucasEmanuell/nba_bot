import requests
import json
from datetime import datetime

URL = "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_1.json"

def baixar_e_processar_calendario():
    response = requests.get(URL)
    data = response.json()

    jogos_processados = []

    for dia in data["leagueSchedule"]["gameDates"]:
        game_date = dia["gameDate"]
        for jogo in dia["games"]:
            home = jogo["homeTeam"]
            away = jogo["awayTeam"]
            horario_utc = jogo["gameDateTimeUTC"]  # exemplo: "2025-10-16T02:00:00Z"

            broadcasters = jogo.get("broadcasters", {}).get("nationalTvBroadcasters", [])
            canais = [b["broadcasterDisplay"] for b in broadcasters if b.get("broadcasterMedia") == "tv"]

            jogos_processados.append({
                "data": game_date.split(" ")[0],
                "hora_utc": horario_utc,
                "mandante": f"{home['teamCity']} {home['teamName']}",
                "visitante": f"{away['teamCity']} {away['teamName']}",
                "canal": canais[0] if canais else "TBD"
            })

    with open("calendario_nba_2025.json", "w", encoding="utf-8") as f:
        json.dump(jogos_processados, f, indent=2, ensure_ascii=False)

baixar_e_processar_calendario()
