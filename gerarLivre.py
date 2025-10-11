import json
import itertools

# --- Parâmetros que você pode alterar ---
disciplina_id = "ARTIFICIAL02"
periodo = "1,2"
nome_arquivo = "combinacoes_horarios.txt"
# ----------------------------------------

# Regras definidas: dias e horários de início
dias_semana = ["SEG", "TER", "QUA", "QUI", "SEX"]
horarios_inicio = [8, 10, 13, 15]

# 1. Gerar todos os blocos de aula únicos possíveis (total de 20 blocos)
# Ex: "SEG-08-10", "SEG-10-12", etc.
blocos_de_aula = []
for dia in dias_semana:
    for inicio in horarios_inicio:
        fim = inicio + 2
        # Formata a string do horário com zero à esquerda se necessário
        bloco = f"{dia}-{inicio:02d}-{fim:02d}"
        blocos_de_aula.append(bloco)

# 2. Gerar todas as combinações únicas de 2 blocos de aula
# A função itertools.combinations é perfeita para isso, pois evita duplicatas
# e pares na ordem inversa (ex: ("A", "B") é o mesmo que ("B", "A")).
combinacoes_horarios = list(itertools.combinations(blocos_de_aula, 2))

# 3. Formatar cada combinação no formato JSON desejado
lista_json_final = []
for i, combinacao in enumerate(combinacoes_horarios):
    turma_id = f"{disciplina_id}T{i+1}"
    
    disciplina_obj = {
        "disciplina_id": disciplina_id,
        "turma_id": turma_id,
        "horario": list(combinacao), # Converte a tupla da combinação em uma lista
        "periodo": periodo
    }
    lista_json_final.append(disciplina_obj)

# 4. Salvar a lista completa de objetos JSON em um arquivo de texto
try:
    with open(nome_arquivo, 'w', encoding='utf-8') as f:
        # Usa json.dump() para escrever a lista inteira no arquivo,
        # com formatação legível (indent=4)
        json.dump(lista_json_final, f, indent=4, ensure_ascii=False)
    
    print(f"\nArquivo '{nome_arquivo}' gerado com sucesso!")
    print(f"Total de combinações encontradas: {len(lista_json_final)}")

except Exception as e:
    print(f"\nOcorreu um erro ao tentar salvar o arquivo: {e}")