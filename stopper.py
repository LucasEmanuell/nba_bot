import sqlite3 
import os
from datetime import datetime, timedelta, timezone
from telegram import Bot
from dotenv import load_dotenv
from dateutil import parser
from database import db

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID"))
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
    
    if not enquetes_abertas:
        print("ℹ️  Nenhuma enquete aberta para encerrar.")
        return
    
    for enquete in enquetes_abertas:
        # Estrutura das colunas do SELECT:
        # 0=id, 1=game_id, 2=data_utc, 3=hora_utc, 4=mandante, 5=visitante, 
        # 6=canal_original, 7=canal_brasil, 8=status, 9=enquete_message_id, 
        # 10=created_at, 11=updated_at
        
        jogo_id = enquete[0]
        data_utc = enquete[2]
        hora_utc = enquete[3]
        mandante = enquete[4]
        visitante = enquete[5]
        enquete_message_id = enquete[9]
        
        try:
            # Construir datetime do jogo
            hora_jogo = parser.isoparse(f"{data_utc}T{hora_utc}").replace(tzinfo=timezone.utc)
            limite_encerramento = hora_jogo - timedelta(minutes=LIMIAR_ENCERRAMENTO_MINUTOS)
            
            if agora >= limite_encerramento:
                await bot.stop_poll(chat_id=GROUP_ID, message_id=enquete_message_id)
                print(f"✅ Enquete encerrada: {visitante} vs {mandante}")
                
                # Limpar message_id no banco
                conn = sqlite3.connect(db.db_name)
                cursor = conn.cursor()
                cursor.execute('UPDATE jogos SET enquete_message_id = NULL WHERE id = ?', (jogo_id,))
                conn.commit()
                conn.close()
            else:
                tempo_restante = limite_encerramento - agora
                print(f"⏳ Enquete {visitante} vs {mandante} será encerrada em {tempo_restante}")
                
        except Exception as e:
            print(f"❌ Erro ao encerrar enquete {jogo_id}: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(encerrar_enquetes())