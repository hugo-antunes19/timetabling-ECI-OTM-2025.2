import json

def verificar_creditos_disponiveis():
    """
    Este script de diagnóstico verifica se os créditos mínimos podem ser satisfeitos
    com as disciplinas que possuem ofertas reais.
    """
    CAMINHO_DISCIPLINAS = './attempt1/disciplinas.json'
    CAMINHO_OFERTAS = './attempt1/ofertas.json'

    # Requisitos definidos no main.py
    CREDITOS_MINIMOS = {
        "restrita": 8,
        "condicionada": 40,
        "livre": 8
    }

    try:
        with open(CAMINHO_DISCIPLINAS, 'r', encoding='utf-8') as f:
            disciplinas_data = json.load(f)
        with open(CAMINHO_OFERTAS, 'r', encoding='utf-8') as f:
            ofertas_data = json.load(f)
    except FileNotFoundError as e:
        print(f"Erro: Arquivo não encontrado - {e}")
        return

    # Pega os IDs de todas as disciplinas que têm pelo menos uma oferta
    disciplinas_com_oferta = {o['disciplina_id'] for o in ofertas_data}
    
    # Dicionário para somar os créditos disponíveis de cada categoria
    creditos_disponiveis = {
        "restrita": 0,
        "condicionada": 0,
        "livre": 0
    }

    # Itera sobre TODAS as disciplinas do arquivo principal
    for d in disciplinas_data:
        d_id = d["id"]
        
        # Pula a disciplina se ela não tiver nenhuma oferta
        if d_id not in disciplinas_com_oferta:
            continue
            
        tipo = d.get("tipo", "")
        creditos = d.get("creditos", 0)

        if "Escolha Restrita" in tipo:
            creditos_disponiveis["restrita"] += creditos
        elif "Escolha Condicionada" in tipo:
            creditos_disponiveis["condicionada"] += creditos
        elif "Livre Escolha" in tipo or d_id.startswith("ARTIFICIAL"):
            creditos_disponiveis["livre"] += creditos

    # --- RELATÓRIO FINAL ---
    print("\n--- Diagnóstico de Créditos Disponíveis ---")
    
    problema_encontrado = False
    for categoria, minimo in CREDITOS_MINIMOS.items():
        disponivel = creditos_disponiveis[categoria]
        status = "✅ OK" if disponivel >= minimo else "❌ FALHA"
        
        if disponivel < minimo:
            problema_encontrado = True
            
        print(f"\nCategoria: Escolha {categoria.capitalize()}")
        print(f"  - Mínimo Requerido: {minimo} créditos")
        print(f"  - Total Disponível com Ofertas: {disponivel} créditos")
        print(f"  - Status: {status}")

    if problema_encontrado:
        print("\n--- CONCLUSÃO DO DIAGNÓSTICO ---")
        print("O modelo é infactível porque não há créditos suficientes disponíveis em pelo menos uma das categorias de optativas.")
        print("Para resolver, você precisa adicionar mais ofertas de turmas no seu arquivo 'ofertas.json' para as categorias que falharam.")
    else:
        print("\n--- CONCLUSÃO DO DIAGNÓSTICO ---")
        print("A quantidade de créditos disponíveis é suficiente. O problema de inviabilidade está na INTERAÇÃO entre as restrições (ex: horários, pré-requisitos, etc.).")


if __name__ == '__main__':
    verificar_creditos_disponiveis()