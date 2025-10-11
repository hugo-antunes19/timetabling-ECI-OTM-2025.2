# app.py
import json
import re # Importa o módulo de expressões regulares
from flask import Flask, render_template, request
from ortools.sat.python import cp_model

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
CREDITOS_MINIMOS = {
    "restrita": 4,
    "condicionada": 40,
    "livre": 8
}

@app.route('/')
def index():
    """ Rota principal que exibe a página inicial com o formulário. """
    try:
        with open(CAMINHO_DISCIPLINAS, 'r', encoding='utf-8') as f:
            todas_disciplinas = json.load(f)
        todas_disciplinas.sort(key=lambda x: (x.get('tipo', 'Z'), x.get('nome', '')))
        return render_template('index.html', disciplinas=todas_disciplinas)
    except FileNotFoundError:
        return "Erro: O arquivo 'disciplinas.json' não foi encontrado.", 500


@app.route('/gerar', methods=['POST'])
def gerar_grade():
    """
    Rota que recebe os dados do formulário (POST), executa o otimizador
    e renderiza a página de resultados com a grade otimizada.
    """
    disciplinas_concluidas = request.form.getlist('concluidas')
    print(f"Disciplinas recebidas como concluídas: {disciplinas_concluidas}")

    try:
        dados = carregar_dados(CAMINHO_DISCIPLINAS, CAMINHO_OFERTAS, disciplinas_concluidas)
    except FileNotFoundError as e:
        return f"Erro ao carregar arquivos de dados: {e}", 500

    grade_result, creditos, status, obj_value = resolver_grade(
        dados, CREDITOS_MINIMOS, NUM_SEMESTRES, CREDITOS_MAXIMOS_POR_SEMESTRE
    )

    status_str = 'UNKNOWN'
    if status is not None:
        if status == cp_model.OPTIMAL: status_str = 'OPTIMAL'
        elif status == cp_model.FEASIBLE: status_str = 'FEASIBLE'
        elif status == cp_model.INFEASIBLE: status_str = 'INFEASIBLE'

    # --- NOVA LÓGICA DE PROCESSAMENTO (CORREÇÃO) ---
    # Esta seção agora interpreta a string retornada pelo optimizer.py
    grades_processadas = {}
    if grade_result:
        dias = ['SEG', 'TER', 'QUA', 'QUI', 'SEX']
        horarios_label = ['08-10', '10-12', '13-15', '15-17']
        
        # Regex para extrair: 1=Nome, 2=Turma, 3=Horários
        # Exemplo da string: "Nome da Disciplina (Turma: IDTURMA) --- Horários: [HORARIO1, HORARIO2]"
        parse_pattern = re.compile(r'^(.*?) \(Turma: (.*?)\) --- Horários: \[(.*?)\]$')

        for s, disciplinas_do_semestre_str in grade_result.items():
            if not disciplinas_do_semestre_str:
                continue

            grade_semanal = {h: {d: None for d in dias} for h in horarios_label}

            for disciplina_str in disciplinas_do_semestre_str:
                match = parse_pattern.match(disciplina_str)
                if match:
                    # Extrai os dados da string usando o regex
                    nome, turma, horarios_str = match.groups()
                    horarios = [h.strip() for h in horarios_str.split(',')]
                    
                    disciplina_info = {"nome": nome, "turma": turma}

                    # Preenche a grade semanal com os dados extraídos
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
    # --- FIM DA NOVA LÓGICA ---

    return render_template(
        'resultado.html',
        grades_processadas=grades_processadas,
        status=status_str,
        obj_value=obj_value
    )


if __name__ == '__main__':
    app.run(debug=True)

