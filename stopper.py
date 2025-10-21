import os
from datetime import datetime, timedelta, timezone
from telegram import Bot
from dotenv import load_dotenv
from dateutil import parser
from database import db

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
LIMIAR_ENCERRAMENTO_MINUTOS = 10

async def encerrar_enquetes():
    bot = Bot(BOT_TOKEN)
    agora = datetime.now(timezone.utc)
    
    # Buscar enquetes abertas no banco
    conn = sqlite3.connect(db.db_name)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM jogos WHERE enquete_message_id IS NOT NULL')
    enquetes_abertas = cursor.fetchall()
    conn.close()
    
    for enquete in enquetes_abertas:
        hora_jogo = parser.isoparse(f"{enquete[1]}T{enquete[2]}").replace(tzinfo=timezone.utc)
        limite_encerramento = hora_jogo - timedelta(minutes=LIMIAR_ENCERRAMENTO_MINUTOS)
        
        if agora >= limite_encerramento:
            try:
                await bot.stop_poll(chat_id=GROUP_ID, message_id=enquete[8])
                print(f"✅ Enquete encerrada: {enquete[4]} vs {enquete[3]}")
                
                # Limpar message_id no banco
                conn = sqlite3.connect(db.db_name)
                cursor = conn.cursor()
                cursor.execute('UPDATE jogos SET enquete_message_id = NULL WHERE id = ?', (enquete[0],))
                conn.commit()
                conn.close()
                
            except Exception as e:
                print(f"❌ Erro ao encerrar enquete: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(encerrar_enquetes())