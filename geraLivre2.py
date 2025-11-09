import json

# --- Parâmetros que você pode alterar ---
# Usei "ARTIFICIAL_2H" para ser claro, mas você pode chamar de "ARTIFICIAL03" se preferir
disciplina_id = "ARTIFICIAL_2H"
# Mantive o período "1, 2" para seguir o padrão das outras
periodo = "1, 2" 
nome_arquivo = "disciplinas_2h.txt"
# ----------------------------------------

# Regras definidas: dias e horários de início
dias_semana = ["SEG", "TER", "QUA", "QUI", "SEX"]
horarios_inicio = [8, 10, 13, 15]

lista_json_final = []
i = 1 # Contador para o turma_id

# Loop por todos os dias da semana
for dia in dias_semana:
    # Loop por todos os horários de início
    for inicio in horarios_inicio:
        fim = inicio + 2
        
        # 1. Formata o bloco de horário (ex: "SEG-08-10")
        bloco = f"{dia}-{inicio:02d}-{fim:02d}"
        
        # 2. Formata o ID da turma (ex: "ARTIFICIAL_2HT1")
        turma_id = f"{disciplina_id}T{i}"
        
        # 3. Cria o objeto JSON no formato correto
        disciplina_obj = {
            "disciplina_id": disciplina_id,
            "turma_id": turma_id,
            "horario": [bloco], # O horário é uma lista, mesmo com um só item
            "periodo": periodo
        }
        
        # 4. Adiciona o objeto à lista final
        lista_json_final.append(disciplina_obj)
        i += 1

# 5. Salva a lista completa de objetos JSON no arquivo
try:
    with open(nome_arquivo, 'w', encoding='utf-8') as f:
        # Usa json.dump() para escrever a lista inteira no arquivo,
        # com formatação legível (indent=4)
        json.dump(lista_json_final, f, indent=4, ensure_ascii=False)
    
    print(f"\nArquivo '{nome_arquivo}' gerado com sucesso!")
    print(f"Total de turmas de 2h geradas: {len(lista_json_final)}")

except Exception as e:
    print(f"\nOcorreu um erro ao tentar salvar o arquivo: {e}")