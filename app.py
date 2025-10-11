# app.py
import json
import re
from flask import Flask, render_template, request
from ortools.sat.python import cp_model
from collections import OrderedDict

# Importa as funções dos seus outros arquivos .py
from data_loader import carregar_dados
from optimizer import resolver_grade

# Inicializa a aplicação Flask
app = Flask(__name__)

# --- Constantes e Configurações ---
CAMINHO_DISCIPLINAS = './data/disciplinas.json'
CAMINHO_OFERTAS = './data/ofertas.json'
NUM_SEMESTRES = 10
CREDITOS_MAXIMOS_POR_SEMESTRE = 32
# Meta TOTAL de créditos de optativas para o curso
CREDITOS_MINIMOS_TOTAIS = {
    "restrita": 4,
    "condicionada": 40,
    "livre": 8
}

@app.route('/')
def index():
    """
    Rota principal que carrega e exibe a página inicial com o formulário,
    agrupando as disciplinas por período e tipo.
    """
    try:
        with open(CAMINHO_DISCIPLINAS, 'r', encoding='utf-8') as f:
            todas_disciplinas = json.load(f)
        
        disciplinas_agrupadas = OrderedDict()
        for disciplina in todas_disciplinas:
            tipo = disciplina.get('tipo', 'Outras')
            if tipo not in disciplinas_agrupadas:
                disciplinas_agrupadas[tipo] = []
            disciplinas_agrupadas[tipo].append(disciplina)
            
        for tipo in disciplinas_agrupadas:
            disciplinas_agrupadas[tipo].sort(key=lambda x: x.get('nome', ''))

        return render_template('index.html', disciplinas_agrupadas=disciplinas_agrupadas)
    
    except FileNotFoundError:
        return "Erro: O arquivo 'disciplinas.json' não foi encontrado.", 500


@app.route('/gerar', methods=['POST'])
def gerar_grade():
    """
    Recebe os dados, CALCULA os créditos de optativas restantes, executa o
    otimizador e renderiza a página de resultados.
    """
    disciplinas_concluidas_ids = request.form.getlist('concluidas')
    print(f"Disciplinas recebidas como concluídas: {disciplinas_concluidas_ids}")

    try:
        with open(CAMINHO_DISCIPLINAS, 'r', encoding='utf-8') as f:
            todas_disciplinas_info = {d['id']: d for d in json.load(f)}
    except FileNotFoundError:
        return "Erro: 'disciplinas.json' não encontrado para calcular créditos.", 500

    creditos_concluidos = {"restrita": 0, "condicionada": 0, "livre": 0}
    
    for disciplina_id in disciplinas_concluidas_ids:
        if disciplina_id in todas_disciplinas_info:
            disciplina = todas_disciplinas_info[disciplina_id]
            tipo = disciplina.get('tipo', '')
            creditos = disciplina.get('creditos', 0)

            if "Restrita" in tipo:
                creditos_concluidos["restrita"] += creditos
            elif "Condicionada" in tipo:
                creditos_concluidos["condicionada"] += creditos
            elif "Livre" in tipo or disciplina_id.startswith("ARTIFICIAL"):
                creditos_concluidos["livre"] += creditos

    # Calcula os créditos que AINDA FALTAM
    # >>>>> A CORREÇÃO ESTÁ AQUI: Convertendo o resultado para int() <<<<<
    creditos_restantes = {
        categoria: int(max(0, CREDITOS_MINIMOS_TOTAIS[categoria] - creditos_concluidos[categoria]))
        for categoria in CREDITOS_MINIMOS_TOTAIS
    }
    
    print(f"Créditos concluídos: {creditos_concluidos}")
    print(f"Créditos restantes a serem cumpridos: {creditos_restantes}")

    try:
        dados = carregar_dados(CAMINHO_DISCIPLINAS, CAMINHO_OFERTAS, disciplinas_concluidas_ids)
    except FileNotFoundError as e:
        return f"Erro ao carregar arquivos de dados: {e}", 500

    # Passa a meta de créditos JÁ AJUSTADA e do TIPO CORRETO para o otimizador
    grade_result, creditos, status, obj_value = resolver_grade(
        dados, creditos_restantes, NUM_SEMESTRES, CREDITOS_MAXIMOS_POR_SEMESTRE
    )

    status_str = 'UNKNOWN'
    if status is not None:
        if status == cp_model.OPTIMAL: status_str = 'OPTIMAL'
        elif status == cp_model.FEASIBLE: status_str = 'FEASIBLE'
        elif status == cp_model.INFEASIBLE: status_str = 'INFEASIBLE'

    grades_processadas = {}
    if grade_result:
        dias = ['SEG', 'TER', 'QUA', 'QUI', 'SEX']
        horarios_label = ['08-10', '10-12', '13-15', '15-17']
        parse_pattern = re.compile(r'^(.*?) \(Turma: (.*?)\) --- Horários: \[(.*?)\]$')

        for s, disciplinas_do_semestre_str in grade_result.items():
            if not disciplinas_do_semestre_str:
                continue

            grade_semanal = {h: {d: None for d in dias} for h in horarios_label}

            for disciplina_str in disciplinas_do_semestre_str:
                match = parse_pattern.match(disciplina_str)
                if match:
                    nome, turma, horarios_str = match.groups()
                    horarios = [h.strip() for h in horarios_str.split(',')]
                    disciplina_info = {"nome": nome, "turma": turma}
                    for horario_completo in horarios:
                        parts = horario_completo.split('-')
                        if len(parts) == 3:
                            dia = parts[0]
                            horario_key = f"{parts[1]}-{parts[2]}"
                            if horario_key in grade_semanal and dia in grade_semanal[horario_key]:
                                grade_semanal[horario_key][dia] = disciplina_info
            
            grades_processadas[s] = {
                "creditos": creditos.get(s, 0),
                "grade_semanal": grade_semanal
            }

    return render_template(
        'resultado.html',
        grades_processadas=grades_processadas,
        status=status_str,
        obj_value=obj_value
    )


if __name__ == '__main__':
    app.run(debug=True)