import sqlite3
import os
from datetime import datetime, timedelta, timezone

class Database:
    def __init__(self, db_name="nba_bot.db"):
        self.db_name = db_name
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Tabela de jogos (TUDO EM UTC!)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS jogos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id TEXT UNIQUE,
                data_utc TEXT NOT NULL,
                hora_utc TEXT NOT NULL,
                mandante TEXT NOT NULL,
                visitante TEXT NOT NULL,
                canal_original TEXT,
                canal_brasil TEXT,
                status TEXT DEFAULT 'agendado',
                enquete_message_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela para controle de execução diária
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS execucoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_execucao DATE UNIQUE,
                enquetes_criadas BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def salvar_jogo(self, jogo):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO jogos 
            (game_id, data_utc, hora_utc, mandante, visitante, canal_original, canal_brasil)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            jogo.get('game_id'),
            jogo['data_utc'],
            jogo['hora_utc'],
            jogo['mandante'],
            jogo['visitante'],
            jogo.get('canal_original'),
            jogo.get('canal_brasil')
        ))
        
        conn.commit()
        conn.close()
    
    def obter_jogos_do_dia(self, data_brasil):
        """
        Obtém jogos do 'dia' considerando horário Brasil (GMT-3)
        
        Jogos são considerados do "dia" se acontecerem entre:
        - 06:00 UTC do dia (03:00 Brasil) até
        - 05:59 UTC do dia seguinte (02:59 Brasil do dia seguinte, ou seja, madrugada)
        
        Exemplo: Dia 23/10 no Brasil inclui jogos de:
        - 2025-10-23 06:00 UTC (23/10 03:00 BR) até
        - 2025-10-24 05:59 UTC (24/10 02:59 BR, ainda é "noite de 23")
        """
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Converter data Brasil para datetime
        data_obj = datetime.strptime(data_brasil, '%Y-%m-%d')
        
        # Início do dia em UTC: 03:00 Brasil = 06:00 UTC
        inicio_utc = data_obj.replace(hour=6, minute=0, second=0)
        
        # Fim do dia em UTC: 02:59 Brasil do dia seguinte = 05:59 UTC do dia seguinte
        fim_utc = (data_obj + timedelta(days=1)).replace(hour=5, minute=59, second=59)
        
        cursor.execute('''
            SELECT * FROM jogos 
            WHERE datetime(data_utc || ' ' || hora_utc) >= datetime(?)
              AND datetime(data_utc || ' ' || hora_utc) <= datetime(?)
            ORDER BY data_utc, hora_utc
        ''', (
            inicio_utc.strftime('%Y-%m-%d %H:%M:%S'),
            fim_utc.strftime('%Y-%m-%d %H:%M:%S')
        ))
        
        jogos = cursor.fetchall()
        conn.close()
        
        return jogos
    
    def marcar_execucao_hoje(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        hoje = datetime.now().strftime('%Y-%m-%d')
        cursor.execute('''
            INSERT OR REPLACE INTO execucoes (data_execucao, enquetes_criadas)
            VALUES (?, ?)
        ''', (hoje, True))
        
        conn.commit()
        conn.close()
    
    def execucao_hoje_feita(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        hoje = datetime.now().strftime('%Y-%m-%d')
        cursor.execute('SELECT * FROM execucoes WHERE data_execucao = ?', (hoje,))
        resultado = cursor.fetchone()
        conn.close()
        
        return resultado is not None

# Singleton
db = Database()