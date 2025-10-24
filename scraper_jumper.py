import requests
import sqlite3
import time
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta
from database import db

def extrair_horario_utc(horario_brasil, data_brasil):
    """Converte horário Brasil para UTC (GMT-3 -> UTC)"""
    try:
        # Formato: 20h, 22h30, 20h00
        horario_limpo = horario_brasil.replace('h', ':')
        
        # Se terminar com ':', adicionar '00'
        if horario_limpo.endswith(':'):
            horario_limpo += '00'
        
        # Se não tiver ':', adicionar ':00'
        if ':' not in horario_limpo:
            horario_limpo += ':00'
        
        # Converter data BR para objeto (formato: dd/mm/yy)
        data_obj = datetime.strptime(data_brasil, '%d/%m/%y')
        
        # Criar datetime com horário Brasil (assumindo GMT-3)
        datetime_brasil_str = f"{data_obj.strftime('%Y-%m-%d')} {horario_limpo}"
        datetime_brasil = datetime.strptime(datetime_brasil_str, '%Y-%m-%d %H:%M')
        
        # Converter para UTC (Brasil é GMT-3, então adiciona 3 horas)
        datetime_utc = datetime_brasil + timedelta(hours=3)
        
        return datetime_utc.strftime('%Y-%m-%d'), datetime_utc.strftime('%H:%M:%S')
    
    except Exception as e:
        print(f"❌ Erro ao converter horário '{horario_brasil}' na data '{data_brasil}': {e}")
        return None, None

def normalizar_nome_time(nome):
    """Normaliza nome do time para facilitar correspondência"""
    nome = nome.strip()
    
    # Mapeamento de nomes alternativos
    mapeamentos = {
        'LA Clippers': 'Los Angeles Clippers',
#        'LA Lakers': 'Los Angeles Lakers',
        'Los Angeles Clippers': 'LA Clippers',  # Reverso também
#        'Los Angeles Lakers': 'LA Lakers',      # Reverso também
    }
    
    return mapeamentos.get(nome, nome)

def scraper_jumper_brasil():
    url = "https://jumperbrasil.com.br/nba-2025-26-calendario-de-transmissoes-da-tv-para-o-brasil/"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Padrão para data: dd/mm/yy (captura apenas números)
        padrao_data = re.compile(r'(\d{1,2}/\d{1,2}/\d{2})(?:\s*\([^)]+\))?')
        atual_data = None
        jogos_atualizados = 0
        jogos_nao_encontrados = []
        
        # Buscar em todo o conteúdo do site
        texto_completo = soup.get_text()
        linhas = texto_completo.split('\n')
        
        for linha in linhas:
            linha = linha.strip()
            if not linha:
                continue
            
            # Verificar se é uma linha de data (ignora dia da semana entre parênteses)
            match_data = padrao_data.search(linha)
            if match_data and not ' x ' in linha:  # Data não misturada com jogo
                atual_data = match_data.group(1)
                print(f"\n📅 Data: {atual_data}")
                continue
            
            # Verificar se é uma linha de jogo
            # Padrões possíveis:
            # - Time A x Time B – HHh[MM] (Canal)
            # - Time A x Time B - HHh[MM] (Canal)  
            if atual_data and ' x ' in linha and 'h' in linha and '(' in linha:
                try:
                    # Remover possível data no início da linha
                    linha_limpa = re.sub(r'^\d{1,2}/\d{1,2}/\d{2}\s*\([^)]+\)\s*', '', linha)
                    
                    # Separar times da parte de horário/canal
                    if '–' in linha_limpa:
                        partes = linha_limpa.split('–', 1)
                    elif ' - ' in linha_limpa:
                        partes = linha_limpa.split(' - ', 1)
                    else:
                        continue
                    
                    if len(partes) < 2:
                        continue
                    
                    times_part = partes[0].strip()
                    horario_canal_part = partes[1].strip()
                    
                    # Extrair times
                    if ' x ' not in times_part:
                        continue
                    
                    times = times_part.split(' x ')
                    if len(times) != 2:
                        continue
                    
                    visitante = normalizar_nome_time(times[0])
                    mandante = normalizar_nome_time(times[1])
                    
                    # Extrair horário (formato: 20h30, 20h, 20h00)
                    horario_match = re.search(r'(\d{1,2}h\d{0,2})', horario_canal_part)
                    if not horario_match:
                        continue
                    
                    horario = horario_match.group(1)
                    
                    # Extrair canal(is) entre parênteses
                    canal_match = re.search(r'\(([^)]+)\)', horario_canal_part)
                    if not canal_match:
                        continue
                    
                    canais_texto = canal_match.group(1)
                    
                    # Se houver múltiplos canais separados por /, pegar todos
                    if '/' in canais_texto:
                        canais = [c.strip() for c in canais_texto.split('/')]
                        canal = ' / '.join(canais)
                    else:
                        canal = canais_texto.strip()
                    
                    # Converter horário para UTC
                    data_utc, hora_utc = extrair_horario_utc(horario, atual_data)
                    
                    if not data_utc or not hora_utc:
                        print(f"⚠️  Horário inválido: {horario}")
                        continue
                    
                    # Atualizar APENAS o campo canal_brasil no banco
                    # NÃO modifica data, hora ou outros campos!
                    try:
                        conn = sqlite3.connect(db.db_name, timeout=10.0)
                        cursor = conn.cursor()
                        
                        # Estratégia 1: Match exato (mandante, visitante, data)
                        cursor.execute('''
                            UPDATE jogos 
                            SET canal_brasil = ?
                            WHERE mandante = ? AND visitante = ?
                            AND data_utc = ?
                        ''', (canal, mandante, visitante, data_utc))
                        
                        rows_updated = cursor.rowcount
                        
                        # Estratégia 2: Match com LIKE (para nomes ligeiramente diferentes)
                        if rows_updated == 0:
                            cursor.execute('''
                                UPDATE jogos 
                                SET canal_brasil = ?
                                WHERE mandante LIKE ? AND visitante LIKE ?
                                AND data_utc = ?
                            ''', (canal, f'%{mandante}%', f'%{visitante}%', data_utc))
                            
                            rows_updated = cursor.rowcount
                        
                        # Estratégia 3: Buscar ID primeiro, depois atualizar
                        if rows_updated == 0:
                            cursor.execute('''
                                SELECT id FROM jogos
                                WHERE mandante LIKE ? AND visitante LIKE ?
                                ORDER BY data_utc
                            ''', (f'%{mandante}%', f'%{visitante}%'))
                            
                            resultado = cursor.fetchone()
                            if resultado:
                                jogo_id = resultado[0]
                                cursor.execute('''
                                    UPDATE jogos 
                                    SET canal_brasil = ?
                                    WHERE id = ?
                                ''', (canal, jogo_id))
                                rows_updated = cursor.rowcount
                        
                        conn.commit()
                        conn.close()
                    except sqlite3.OperationalError as e:
                        print(f"❌ Erro de banco de dados: {e}")
                        rows_updated = 0
                    
                    if rows_updated > 0:
                        print(f"✅ {visitante} x {mandante} → {canal}")
                        jogos_atualizados += 1
                    else:
                        info = f"{visitante} x {mandante} ({data_utc} {hora_utc})"
                        jogos_nao_encontrados.append(info)
                        print(f"⚠️  Não encontrado: {info}")
                
                except Exception as e:
                    print(f"❌ Erro ao processar linha: {e}")
                    print(f"   Linha: {linha[:80]}...")
        
        print(f"\n{'='*80}")
        print(f"✅ Scraping concluído!")
        print(f"   • {jogos_atualizados} jogos atualizados com canais brasileiros")
        print(f"   • {len(jogos_nao_encontrados)} jogos não encontrados no BD")
        
        if jogos_nao_encontrados and len(jogos_nao_encontrados) <= 10:
            print(f"\n⚠️  Jogos não encontrados:")
            for jogo in jogos_nao_encontrados:
                print(f"   - {jogo}")
    
    except requests.RequestException as e:
        print(f"❌ Erro ao acessar o site: {e}")
    except Exception as e:
        print(f"❌ Erro no scraping: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    scraper_jumper_brasil()