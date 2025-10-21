import sqlite3
import os
from datetime import datetime

class Database:
    def __init__(self, db_name="nba_bot.db"):
        self.db_name = db_name
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Tabela de jogos
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
        """Obtém jogos considerando que jogos após meia-noite ainda são do 'dia anterior'"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Converte data Brasil para UTC (considera que jogos até 06:00 UTC ainda são do dia anterior)
        cursor.execute('''
            SELECT * FROM jogos 
            WHERE date(data_utc) = date(?) 
               OR (date(data_utc) = date(?, '+1 day') AND time(hora_utc) < '06:00:00')
            ORDER BY hora_utc
        ''', (data_brasil, data_brasil))
        
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