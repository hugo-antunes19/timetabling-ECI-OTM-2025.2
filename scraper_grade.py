# scraper_grade.py

import json
import re
from bs4 import BeautifulSoup

def parse_requisitos(texto_requisito):
    """
    🧹 Função auxiliar para limpar a string de pré-requisitos.
    Ela usa regex para encontrar todos os códigos de disciplinas (padrão 3 letras + 3 números).
    """
    if not texto_requisito:
        return []
    
    # Encontra todos os códigos no formato 'ABC123'
    codigos = re.findall(r'[A-Z]{3}\d{3}', texto_requisito)
    return list(set(codigos)) # Usa set para garantir que não haja duplicatas

def extrair_dados_curriculo(nome_arquivo_html):
    """
    Função principal que lê o arquivo HTML e extrai todas as disciplinas.
    """
    try:
        with open(nome_arquivo_html, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f.read(), 'html.parser')
    except FileNotFoundError:
        print(f"Erro: O arquivo '{nome_arquivo_html}' não foi encontrado.")
        return None

    dados_curriculo = {}

    # Encontra todas as tabelas principais que contêm os períodos e seções
    tabelas_principais = soup.find_all('table', class_='lineBorder')

    for tabela in tabelas_principais:
        # O título (ex: "1º Período") está em uma tag <b> dentro de uma linha de título
        titulo_tag = tabela.find('tr', class_='tableTitle')
        if not titulo_tag or not titulo_tag.b:
            continue
            
        titulo_secao = titulo_tag.b.text.strip()
        
        # Ignora tabelas que não são de disciplinas
        if "Período" not in titulo_secao and "Optativas" not in titulo_secao:
            continue

        print(f"Processando seção: {titulo_secao}...")
        dados_curriculo[titulo_secao] = []

        # Encontra todas as linhas de disciplinas dentro da tabela atual
        linhas_disciplinas = tabela.find_all('tr', class_=['tableBodyBlue1', 'tableBodyBlue2'])

        for linha in linhas_disciplinas:
            celulas = linha.find_all('td')
            
            # Pula linhas que não são de disciplinas (ex: "Total de Créditos")
            if not celulas or not celulas[0].a:
                continue

            try:
                codigo = celulas[0].a.text.strip()
                nome = celulas[1].text.strip()
                creditos = float(celulas[2].text.strip())
                
                # Para os requisitos, pegamos o texto completo da célula
                requisitos_raw = celulas[-1].get_text(separator=' ', strip=True)
                requisitos_limpos = parse_requisitos(requisitos_raw)

                disciplina = {
                    "id": codigo,
                    "nome": nome,
                    "creditos": creditos,
                    "prerequisitos": requisitos_limpos
                }
                dados_curriculo[titulo_secao].append(disciplina)

            except (IndexError, ValueError) as e:
                # Ignora linhas mal formatadas, se houver
                # print(f"Aviso: Pulando linha mal formatada. Erro: {e}")
                pass
                
    return dados_curriculo


def salvar_em_json(dados, nome_arquivo):
    """
    Salva o dicionário de dados em um arquivo JSON formatado.
    """
    with open(nome_arquivo, 'w', encoding='utf-8') as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Dados extraídos e salvos com sucesso em '{nome_arquivo}'!")


# --- PONTO DE PARTIDA DO SCRIPT ---
if __name__ == '__main__':
    ARQUIVO_HTML = "htmlSiga.html"
    
    dados_completos = extrair_dados_curriculo(ARQUIVO_HTML)
    
    if dados_completos:
        salvar_em_json(dados_completos, "disciplinas.json")