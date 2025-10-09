# main.py
import time
from ortools.sat.python import cp_model

# Importa as funções dos outros módulos
from data_loader import carregar_dados
from optimizer import resolver_grade
from visualizer import gerar_visualizacao_html, imprimir_grade_terminal

def main():
    """
    Função principal que orquestra o processo de otimização da grade.
    """
    start_time = time.time()

    # --- Parâmetros ---
    CAMINHO_DISCIPLINAS = './attempt1/disciplinas.json'
    CAMINHO_OFERTAS = './attempt1/ofertas.json'
    NUM_SEMESTRES = 10
    CREDITOS_MAXIMOS_POR_SEMESTRE = 32

    # 1. Carregar e processar os dados
    try:
        dados = carregar_dados(CAMINHO_DISCIPLINAS, CAMINHO_OFERTAS)
    except FileNotFoundError as e:
        print(f"Erro ao carregar dados: {e}")
        return

    # 2. Chamar o otimizador para resolver o modelo
    grade, creditos, status, obj_value = resolver_grade(
        dados, NUM_SEMESTRES, CREDITOS_MAXIMOS_POR_SEMESTRE
    )

    # 3. Exibir os resultados
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        print(f'\nSolução encontrada em {time.time() - start_time:.2f} segundos.')
        print(f'Número mínimo de semestres: {obj_value}')
        
        # Imprime a grade no terminal
        imprimir_grade_terminal(grade, creditos)
        
        # Gera o arquivo HTML com a visualização
        gerar_visualizacao_html(grade, creditos)

    elif status == cp_model.INFEASIBLE:
        print('\nNenhuma solução encontrada: O modelo é infactível.')
        print('Verifique se a combinação de restrições (período, pré-requisitos, horários) é possível.')
    else:
        print('Nenhuma solução encontrada: O solver parou por outro motivo (ex: tempo limite).')


if __name__ == '__main__':
    main()