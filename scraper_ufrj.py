import json
import re
from bs4 import BeautifulSoup

def extrair_prerequisitos(td_requisitos):
    """
    Função auxiliar para extrair e limpar os códigos dos pré-requisitos.
    Esta é a parte mais complexa, pois os requisitos vêm em texto livre.
    Usaremos expressões regulares (regex) para encontrar padrões como 'COD123 (P)'.
    """
    if not td_requisitos:
        return []

    # O padrão [A-Z]{3}\d{3} procura por 3 letras maiúsculas seguidas de 3 números (o formato dos códigos).
    # O \s*\(P|C\) procura por (P) ou (C) (Pré-requisito ou Co-requisito), que indicam uma dependência real.
    # Usamos re.findall para pegar todos que correspondem ao padrão na célula.
    # Isso inteligentemente ignora as linhas de equivalência (ex: MAC118 = MAW111).
    requisitos_encontrados = re.findall(r'([A-Z]{3}\d{3})\s*\([PC]\)', td_requisitos.get_text())
    
    # Remove duplicados caso existam e retorna a lista
    return sorted(list(set(requisitos_encontrados)))

def analisar_html_grade(caminho_arquivo):
    """
    Função principal que lê o arquivo HTML e extrai todas as disciplinas.
    """
    print(f"Lendo o arquivo HTML: {caminho_arquivo}")
    with open(caminho_arquivo, 'r', encoding='utf-8') as f:
        conteudo = f.read()

    soup = BeautifulSoup(conteudo, 'html.parser')

    # Identificamos que todas as tabelas de disciplinas possuem uma linha de cabeçalho
    # com a classe 'tableTitleBlue'. Vamos encontrar todas elas.
    tabelas_de_periodos = soup.find_all('table', class_='cellspacingTable')
    
    disciplinas_extraidas = []
    print(f"Analisando {len(tabelas_de_periodos)} tabelas encontradas...")

    for tabela in tabelas_de_periodos:
        # Pega o título da tabela (ex: "1º Período", "Disciplinas Optativas")
        titulo_tag = tabela.find('tr', class_='tableTitle')
        if not titulo_tag or not titulo_tag.text.strip():
            continue # Pula tabelas que não são de disciplinas (como as do cabeçalho)
        
        titulo_secao = titulo_tag.text.strip()
        
        # Cada disciplina está numa linha com classe 'tableBodyBlue1' ou 'tableBodyBlue2'
        linhas = tabela.find_all('tr', class_=re.compile(r'tableBodyBlue'))

        for linha in linhas:
            celulas = linha.find_all('td')
            
            # Uma linha de disciplina válida tem pelo menos 7 colunas
            if len(celulas) < 7:
                continue

            try:
                codigo = celulas[0].text.strip()
                nome = celulas[1].text.strip()
                creditos_str = celulas[2].text.strip()

                # Ignora linhas que não têm um código de disciplina válido
                if not re.match(r'^[A-Z]{3}\d{3}$', codigo):
                    continue

                disciplina = {
                    "id": codigo,
                    "nome": nome,
                    "creditos": float(creditos_str) if creditos_str else 0.0,
                    "prerequisitos": extrair_prerequisitos(celulas[6]),
                    "tipo": titulo_secao # Adiciona de qual seção a disciplina pertence
                }
                
                disciplinas_extraidas.append(disciplina)
                
            except (ValueError, IndexError) as e:
                # Se algo der errado na conversão ou se uma linha não tiver o formato esperado
                print(f"Aviso: Linha ignorada na seção '{titulo_secao}' devido a formato inesperado. Erro: {e}")
                continue
    
    return disciplinas_extraidas


def salvar_em_json(dados, nome_arquivo):
    """
    Salva a lista de dicionários em um arquivo JSON bem formatado.
    """
    with open(nome_arquivo, 'w', encoding='utf-8') as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    print(f"\nSucesso! {len(dados)} disciplinas foram extraídas e salvas em '{nome_arquivo}'.")


# --- PONTO DE PARTIDA DO SCRIPT ---
if __name__ == '__main__':
    ARQUIVO_HTML = "htmlSiga.html"
    
    disciplinas = analisar_html_grade(ARQUIVO_HTML)
    
    if disciplinas:
        salvar_em_json(disciplinas, "disciplinas.json")