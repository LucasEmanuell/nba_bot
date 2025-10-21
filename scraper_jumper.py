import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
from database import db

def converter_data_brasil_para_utc(data_brasil):
    """Converte data no formato BR para UTC"""
    try:
        # Formato: 12/10/25 -> 2025-10-12
        data_obj = datetime.strptime(data_brasil, '%d/%m/%y')
        return data_obj.strftime('%Y-%m-%d')
    except ValueError:
        return None

def extrair_horario_utc(horario_brasil, data_brasil):
    """Converte horário Brasil para UTC (GMT-3 -> UTC)"""
    try:
        # Formato: 20h, 22h30
        horario_limpo = horario_brasil.replace('h', ':').replace('h30', ':30')
        if ':' not in horario_limpo:
            horario_limpo += ':00'
        
        # Converter data BR para objeto
        data_obj = datetime.strptime(data_brasil, '%d/%m/%y')
        
        # Criar datetime com horário Brasil (assumindo GMT-3)
        datetime_brasil = datetime.strptime(f"{data_obj.strftime('%Y-%m-%d')} {horario_limpo}", '%Y-%m-%d %H:%M')
        
        # Converter para UTC (Brasil é GMT-3)
        datetime_utc = datetime_brasil.replace(hour=datetime_brasil.hour + 3)
        if datetime_utc.hour >= 24:
            datetime_utc = datetime_utc.replace(day=datetime_utc.day + 1, hour=datetime_utc.hour - 24)
        
        return datetime_utc.strftime('%Y-%m-%d'), datetime_utc.strftime('%H:%M:%S')
    
    except Exception as e:
        print(f"Erro ao converter horário {horario_brasil}: {e}")
        return None, None

def scraper_jumper_brasil():
    url = "https://jumperbrasil.com.br/nba-2025-26-calendario-de-transmissoes-da-tv-para-o-brasil/"
    
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Encontrar todas as seções de datas
        padrao_data = re.compile(r'(\d{1,2}/\d{1,2}/\d{2,4})')
        atual_data = None
        
        for elemento in soup.find_all(['h2', 'h3', 'h4', 'p', 'div']):
            texto = elemento.get_text().strip()
            
            # Verificar se é uma linha de data
            match_data = padrao_data.search(texto)
            if match_data:
                atual_data = match_data.group(1)
                print(f"Data encontrada: {atual_data}")
                continue
            
            # Verificar se é uma linha de jogo
            if atual_data and 'x' in texto and 'h' in texto:
                try:
                    # Padrão: "Time A x Time B – Horário (Canal)"
                    partes = texto.split('–')
                    if len(partes) >= 2:
                        times_part = partes[0].strip()
                        horario_canal_part = partes[1].strip()
                        
                        # Extrair times
                        times = times_part.split('x')
                        if len(times) == 2:
                            visitante = times[0].strip()
                            mandante = times[1].strip()
                            
                            # Extrair horário e canal
                            horario_match = re.search(r'(\d{1,2}h\d{0,2})', horario_canal_part)
                            canal_match = re.search(r'\(([^)]+)\)', horario_canal_part)
                            
                            horario = horario_match.group(1) if horario_match else None
                            canal = canal_match.group(1) if canal_match else "TBD"
                            
                            if horario and visitante and mandante:
                                data_utc, hora_utc = extrair_horario_utc(horario, atual_data)
                                
                                if data_utc and hora_utc:
                                    # Atualizar banco de dados
                                    conn = sqlite3.connect(db.db_name)
                                    cursor = conn.cursor()
                                    
                                    cursor.execute('''
                                        UPDATE jogos 
                                        SET canal_brasil = ?
                                        WHERE mandante LIKE ? AND visitante LIKE ?
                                        AND data_utc = ?
                                    ''', (
                                        canal,
                                        f'%{mandante}%',
                                        f'%{visitante}%',
                                        data_utc
                                    ))
                                    
                                    if cursor.rowcount > 0:
                                        print(f"✅ Atualizado: {visitante} x {mandante} - {canal}")
                                    else:
                                        print(f"❌ Não encontrado: {visitante} x {mandante}")
                                    
                                    conn.commit()
                                    conn.close()
                
                except Exception as e:
                    print(f"Erro ao processar linha: {texto} - {e}")
    
    except Exception as e:
        print(f"Erro no scraping: {e}")

if __name__ == "__main__":
    scraper_jumper_brasil()