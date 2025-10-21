from get_nba import processar_calendario_nba
from scraper_jumper import scraper_jumper_brasil

def atualizar_tudo():
    print("🔄 Atualizando calendário NBA...")
    processar_calendario_nba()
    
    print("🔄 Atualizando canais Brasil...")
    scraper_jumper_brasil()
    
    print("✅ Atualização completa!")

if __name__ == "__main__":
    atualizar_tudo()