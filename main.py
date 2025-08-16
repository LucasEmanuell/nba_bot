import json
import os
from datetime import datetime, timedelta, timezone
from telegram import Bot
from telegram.constants import ParseMode
from dotenv import load_dotenv
from dateutil import parser

# Carrega variáveis de ambiente (.env)
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID"))

# Para exibição no título da enquete (GMT-3)
TIMEZONE_OFFSET = -3

# Carrega o calendário local da temporada (datas em UTC)
with open("calendario_nba_2025.json", "r", encoding="utf-8") as f:
    calendario = json.load(f)

def jogos_de_hoje():
    hoje_utc = datetime.utcnow().date()
    return [j for j in calendario if j["data"] == hoje_utc.strftime("%Y-%m-%d")]

async def postar_apostas_e_enquetes():
    bot = Bot(BOT_TOKEN)
    jogos = jogos_de_hoje()

    if not jogos:
        print("Nenhum jogo encontrado para hoje.")
        return

    # Envia e fixa a mensagem principal
    msg = await bot.send_message(
        chat_id=GROUP_ID,
        text="📅 *Apostas de hoje!*",
        parse_mode=ParseMode.MARKDOWN
    )
    await bot.pin_chat_message(chat_id=GROUP_ID, message_id=msg.message_id)

    for jogo in jogos:
        mandante = jogo["mandante"]
        visitante = jogo["visitante"]
        canal = jogo["canal"]

        # Parse do horário UTC e força timezone explícito
        hora_utc = parser.isoparse(jogo["hora_utc"]).replace(tzinfo=timezone.utc)
        hora_local = hora_utc + timedelta(hours=TIMEZONE_OFFSET)

        titulo = f"{hora_local.strftime('%Hh%M')} 📺 {canal} | {visitante} vs {mandante}"

        # Garante close_date entre 5min e 10 dias (Telegram requirement)
        agora = datetime.now(timezone.utc)
        min_close = agora + timedelta(minutes=5)
        max_close = agora + timedelta(days=10)

        if hora_utc < min_close:
            close_ts = round(min_close.timestamp())
        elif hora_utc > max_close:
            close_ts = round(max_close.timestamp())
        else:
            close_ts = round(hora_utc.timestamp())

        # Debug para teste
        print(f"[ENQUETE] {titulo}")
        print(f" - agora (UTC): {agora.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f" - fecha às (UTC): {datetime.fromtimestamp(close_ts).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f" - fecha às (local): {datetime.fromtimestamp(close_ts) + timedelta(hours=TIMEZONE_OFFSET)}")

        await bot.send_poll(
            chat_id=GROUP_ID,
            question=titulo,
            options=[visitante, mandante],
            is_anonymous=False,
            allows_multiple_answers=False,
            close_date=close_ts
        )

# Execução direta
if __name__ == "__main__":
    import asyncio
    asyncio.run(postar_apostas_e_enquetes())
