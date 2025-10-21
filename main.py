import json
import os
from datetime import datetime, timedelta, timezone
from telegram import Bot
from telegram.constants import ParseMode
from dotenv import load_dotenv
from dateutil import parser
from database import db

# Carrega variáveis de ambiente
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID"))
TIMEZONE_OFFSET = -3

async def postar_apostas_e_enquetes():
    # Verificar se já executou hoje
    if db.execucao_hoje_feita():
        print("Enquetes de hoje já foram criadas.")
        return

    bot = Bot(BOT_TOKEN)
    
    # Obter data atual no Brasil
    hoje_brasil = datetime.now().strftime('%Y-%m-%d')
    jogos = db.obter_jogos_do_dia(hoje_brasil)
    
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

    enquetes_info = []

    for jogo in jogos:
        # jogo[3] = mandante, jogo[4] = visitante, jogo[6] = canal_brasil
        mandante = jogo[3]
        visitante = jogo[4]
        canal = jogo[6] or "TBD"  # Usa canal Brasil se disponível

        # Converter horário UTC para local
        hora_utc = parser.isoparse(f"{jogo[1]}T{jogo[2]}").replace(tzinfo=timezone.utc)
        hora_local = hora_utc + timedelta(hours=TIMEZONE_OFFSET)

        # Montar título
        if canal and canal != "TBD":
            titulo = f"{hora_local.strftime('%Hh%M')} 📺 {canal} | {visitante} vs {mandante}"
        else:
            titulo = f"{hora_local.strftime('%Hh%M')} | {visitante} vs {mandante}"

        # Criar enquete
        poll = await bot.send_poll(
            chat_id=GROUP_ID,
            question=titulo,
            options=[visitante, mandante],
            is_anonymous=False,
            allows_multiple_answers=False
        )

        # Atualizar banco com message_id da enquete
        conn = sqlite3.connect(db.db_name)
        cursor = conn.cursor()
        cursor.execute('UPDATE jogos SET enquete_message_id = ? WHERE id = ?', (poll.message_id, jogo[0]))
        conn.commit()
        conn.close()

        enquetes_info.append({
            "message_id": poll.message_id,
            "chat_id": GROUP_ID,
            "hora_utc": f"{jogo[1]}T{jogo[2]}",
            "titulo": titulo
        })

    # Marcar como executado hoje
    db.marcar_execucao_hoje()
    print(f"Enquetes criadas para {len(jogos)} jogos.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(postar_apostas_e_enquetes())