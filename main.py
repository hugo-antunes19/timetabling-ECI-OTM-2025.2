# main.py
import time
from ortools.sat.python import cp_model
from data_loader import carregar_dados
from optimizer import resolver_grade
from visualizer import gerar_visualizacao_html, imprimir_grade_terminal

def main():
    start_time = time.time()

    # --- Parâmetros ---
    CAMINHO_DISCIPLINAS = './data/disciplinas.json'
    CAMINHO_OFERTAS = './data/ofertas.json'
    NUM_SEMESTRES = 10
    CREDITOS_MAXIMOS_POR_SEMESTRE = 32

    CREDITOS_MINIMOS = {
        "restrita": 4,
        "condicionada": 40,
        "livre": 8
    }

    # --- NOVOS PARÂMETROS CONFIGURÁVEIS ---

    # 1. Defina o tipo do próximo período letivo da universidade.
    #    Use 'impar' se o próximo semestre for 2025.1, 2026.1, etc.
    #    Use 'par' se o próximo semestre for 2025.2, 2026.2, etc.
    #    Isso alinha a grade do aluno com o calendário da faculdade.
    PROXIMO_PERIODO_TIPO = 'impar' 

    # 2. Liste aqui os códigos das disciplinas que você já concluiu.
    #    O otimizador irá removê-las do planejamento e satisfazer seus pré-requisitos.
    #    Exemplo: DISCIPLINAS_CONCLUIDAS = ["MAC118", "COS110"]
    DISCIPLINAS_CONCLUIDAS = []

    # --- FIM DOS PARÂMETROS ---


    # 1. Carregar e processar os dados, agora passando as disciplinas concluídas
    try:
        dados = carregar_dados(CAMINHO_DISCIPLINAS, CAMINHO_OFERTAS, disciplinas_concluidas=DISCIPLINAS_CONCLUIDAS)
    except FileNotFoundError as e:
        print(f"Erro ao carregar dados: {e}")
        return

    # 2. Chamar o otimizador, agora passando o tipo do próximo período
    grade, creditos, status, obj_value = resolver_grade(
        dados, 
        CREDITOS_MINIMOS, 
        NUM_SEMESTRES, 
        CREDITOS_MAXIMOS_POR_SEMESTRE,
        PROXIMO_PERIODO_TIPO  # Passando o novo parâmetro
    )

    # 3. Exibir os resultados
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        print(f'\nSolução encontrada em {time.time() - start_time:.2f} segundos.')
        print(f'Número mínimo de semestres para concluir: {obj_value}')
        imprimir_grade_terminal(grade, creditos)
        gerar_visualizacao_html(grade, creditos)
    elif status == cp_model.INFEASIBLE:
        print('\nNenhuma solução encontrada: O modelo é infactível.')
        print('Verifique se a combinação de restrições é possível.')
    else:
        print('Nenhuma solução encontrada: O solver parou por outro motivo (ex: tempo limite).')


if __name__ == '__main__':
    main()