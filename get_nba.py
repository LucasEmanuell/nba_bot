import requests
from datetime import datetime
from database import db

URL = "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_1.json"

def processar_calendario_nba():
    try:
        response = requests.get(URL, timeout=15)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"❌ Erro ao baixar calendário: {e}")
        return

    jogos_processados = 0
    jogos_com_erro = 0

    # Percorrer TODOS os jogos, ignorando o agrupamento por gameDate
    for dia in data["leagueSchedule"]["gameDates"]:
        for jogo in dia["games"]:
            try:
                home = jogo["homeTeam"]
                away = jogo["awayTeam"]
                game_id = jogo["gameId"]
                
                # USAR APENAS gameDateTimeUTC (data + hora corretas juntas!)
                game_datetime_utc = jogo.get("gameDateTimeUTC")
                
                if not game_datetime_utc:
                    print(f"⚠️  Jogo {game_id} sem gameDateTimeUTC")
                    jogos_com_erro += 1
                    continue
                
                # Converter ISO 8601 para datetime
                # Exemplo: "2025-10-23T23:30:00Z" -> 2025-10-23 23:30:00
                try:
                    dt_utc = datetime.fromisoformat(game_datetime_utc.replace('Z', ''))
                    data_utc = dt_utc.strftime('%Y-%m-%d')
                    hora_utc = dt_utc.strftime('%H:%M:%S')
                except ValueError as e:
                    print(f"❌ Erro ao parsear {game_id}: {game_datetime_utc} - {e}")
                    jogos_com_erro += 1
                    continue
                
                # Extrair canais de transmissão (apenas para referência, não usado no Brasil)
                broadcasters = jogo.get("broadcasters", {}).get("nationalTvBroadcasters", [])
                canais = [b["broadcasterDisplay"] for b in broadcasters if b.get("broadcasterMedia") == "tv"]
                
                jogo_processado = {
                    "game_id": game_id,
                    "data_utc": data_utc,
                    "hora_utc": hora_utc,
                    "mandante": f"{home['teamCity']} {home['teamName']}",
                    "visitante": f"{away['teamCity']} {away['teamName']}",
                    "canal_original": canais[0] if canais else None,
                    "canal_brasil": None  # Será preenchido pelo scraper
                }
                
                db.salvar_jogo(jogo_processado)
                jogos_processados += 1
                
            except KeyError as e:
                print(f"❌ Campo faltando: {e}")
                jogos_com_erro += 1
            except Exception as e:
                print(f"❌ Erro ao processar jogo: {e}")
                jogos_com_erro += 1

    print(f"\n{'='*80}")
    print(f"✅ Calendário NBA processado:")
    print(f"   • {jogos_processados} jogos salvos")
    if jogos_com_erro > 0:
        print(f"   • {jogos_com_erro} jogos com erro (ignorados)")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    processar_calendario_nba()