import sqlite3
import asyncio
import os
from datetime import datetime, timedelta, timezone
from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError
from dotenv import load_dotenv
from database import db

# Carrega variáveis de ambiente
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID"))
TIMEZONE_OFFSET = -3

async def desafixar_mensagem_anterior(bot):
    """Desafixa a mensagem 'Apostas de hoje!' do dia anterior"""
    try:
        # Obtém mensagens fixadas
        chat = await bot.get_chat(GROUP_ID)
        if chat.pinned_message:
            # Verifica se é a mensagem de apostas
            if "Apostas de hoje" in chat.pinned_message.text:
                await bot.unpin_chat_message(chat_id=GROUP_ID, message_id=chat.pinned_message.message_id)
                print("✅ Mensagem anterior desafixada")
    except Exception as e:
        print(f"⚠️  Não foi possível desafixar mensagem anterior: {e}")

async def postar_apostas_e_enquetes():
    # Verificar se já executou hoje
    if db.execucao_hoje_feita():
        print("Enquetes de hoje já foram criadas.")
        return

    bot = Bot(BOT_TOKEN)
    
    # Desafixar mensagem do dia anterior
    await desafixar_mensagem_anterior(bot)
    
    # Obter data atual no Brasil
    hoje_brasil = datetime.now().strftime('%Y-%m-%d')
    jogos = db.obter_jogos_do_dia(hoje_brasil)
    
    if not jogos:
        print("Nenhum jogo encontrado para hoje.")
        return

    # Converter jogos para lista de dicionários
    jogos_processados = []
    
    for jogo in jogos:
        # Estrutura das colunas do SELECT:
        # 0=id, 1=game_id, 2=data_utc, 3=hora_utc, 4=mandante, 5=visitante, 
        # 6=canal_original, 7=canal_brasil, 8=status, 9=enquete_message_id, 
        # 10=created_at, 11=updated_at
        
        jogo_id = jogo[0]
        game_id = jogo[1]
        data_utc = jogo[2]
        hora_utc = jogo[3]
        mandante = jogo[4]
        visitante = jogo[5]
        canal_original = jogo[6]
        canal_brasil = jogo[7]
        
        # Apenas usar canal brasileiro (ignorar transmissões estrangeiras)
        canal = canal_brasil if canal_brasil else None

        # Converter horário UTC para local
        try:
            data_hora_utc_str = f"{data_utc} {hora_utc}"
            hora_utc_dt = datetime.strptime(data_hora_utc_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            hora_local = hora_utc_dt + timedelta(hours=TIMEZONE_OFFSET)
        except Exception as e:
            print(f"❌ Erro ao converter horário do jogo {jogo_id}: {e}")
            print(f"   data_utc={data_utc}, hora_utc={hora_utc}")
            continue

        jogos_processados.append({
            'jogo_id': jogo_id,
            'mandante': mandante,
            'visitante': visitante,
            'canal': canal,
            'hora_local': hora_local,
            'data_utc': data_utc,
            'hora_utc': hora_utc,
            'hora_timestamp': hora_local.timestamp()  # Para ordenação precisa
        })
    
    # Ordenar jogos por horário local (data + hora completa)
    # Usar tupla (data, hora) para garantir ordem correta
    jogos_processados.sort(key=lambda x: (x['hora_local'].date(), x['hora_local'].time()))
    
    print(f"\n📋 Ordem cronológica dos jogos:")
    for idx, jogo in enumerate(jogos_processados, 1):
        canal_info = f" ({jogo['canal']})" if jogo['canal'] else ""
        print(f"  {idx}. {jogo['hora_local'].strftime('%Hh%M')}{canal_info} - {jogo['visitante']} vs {jogo['mandante']}")
    print()
    
    # Envia e fixa a mensagem principal
    try:
        msg = await bot.send_message(
            chat_id=GROUP_ID,
            text="*Apostas de hoje!*",
            parse_mode=ParseMode.MARKDOWN
        )
        await bot.pin_chat_message(chat_id=GROUP_ID, message_id=msg.message_id)
        print(f"✅ Mensagem principal fixada (ID: {msg.message_id})")
    except Exception as e:
        print(f"❌ Erro ao fixar mensagem principal: {e}")

    enquetes_criadas = 0

    for idx, jogo in enumerate(jogos_processados, 1):
        # Montar título
        horario_formatado = jogo['hora_local'].strftime('%Hh%M')
        
        if jogo['canal']:
            # Com canal brasileiro
            titulo = f"{horario_formatado} 📺 {jogo['canal']}"
        else:
            # Sem transmissão no Brasil
            titulo = f"{horario_formatado}"

        # Criar enquete
        try:
            poll = await bot.send_poll(
                chat_id=GROUP_ID,
                question=titulo,
                options=[jogo['visitante'], jogo['mandante']],
                is_anonymous=False,
                allows_multiple_answers=False
            )

            # Atualizar banco com message_id da enquete
            conn = sqlite3.connect(db.db_name)
            cursor = conn.cursor()
            cursor.execute('UPDATE jogos SET enquete_message_id = ? WHERE id = ?', 
                         (poll.message_id, jogo['jogo_id']))
            conn.commit()
            conn.close()

            enquetes_criadas += 1
            print(f"✅ [{idx}/{len(jogos_processados)}] Enquete criada: {titulo} | {jogo['visitante']} vs {jogo['mandante']}")
            
            # Aguardar 3 segundos antes da próxima enquete (evita problemas de ordem)
            if idx < len(jogos_processados):  # Não espera após a última
                await asyncio.sleep(3)
            
        except TelegramError as e:
            print(f"❌ Erro do Telegram ao criar enquete: {e}")
        except Exception as e:
            print(f"❌ Erro ao criar enquete: {e}")

    # Marcar como executado hoje
    db.marcar_execucao_hoje()
    print(f"\n✅ Processo concluído! {enquetes_criadas} enquetes criadas em ordem cronológica.")

if __name__ == "__main__":
    asyncio.run(postar_apostas_e_enquetes())