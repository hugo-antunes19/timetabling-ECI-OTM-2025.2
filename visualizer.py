# visualizer.py
import re

def gerar_visualizacao_html(grade, creditos_por_semestre, nome_arquivo="grade_horaria.html"):
    """
    Gera um arquivo HTML com a grade horária formatada em tabelas de grade semanal.
    """
    # Define o estilo CSS para a página, agora com estilos para a grade
    html_content = """
    <html>
    <head>
        <title>Grade Horária Otimizada</title>
        <style>
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                margin: 0;
                padding: 2em;
                background-color: #f8f9fa;
                color: #212529;
            }
            .container { 
                max-width: 1200px; 
                margin: auto;
            }
            h1 { 
                color: #003366; 
                text-align: center;
                border-bottom: 3px solid #003366;
                padding-bottom: 10px;
            }
            h2 { 
                color: #343a40; 
                border-bottom: 2px solid #dee2e6;
                padding-bottom: 8px;
                margin-top: 50px;
            }
            table.grade-semanal { 
                border-collapse: collapse; 
                width: 100%; 
                margin-top: 20px;
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                table-layout: fixed;
            }
            .grade-semanal th, .grade-semanal td { 
                border: 1px solid #dee2e6; 
                padding: 10px; 
                text-align: center; 
                height: 80px;
                vertical-align: top;
            }
            .grade-semanal thead { 
                background-color: #003366; 
                color: white;
            }
            .grade-semanal tbody tr:nth-child(even) { 
                background-color: #fdfdfd; 
            }
            .grade-semanal td.horario-label {
                font-weight: bold;
                background-color: #f8f9fa;
                width: 12%;
            }
            .materia-cell {
                background-color: #e7f5ff;
                font-size: 0.9em;
                line-height: 1.4;
            }
            .materia-cell small {
                color: #555;
            }
            .notas {
                margin-top: 15px;
                padding: 10px;
                background-color: #fffbe6;
                border-left: 4px solid #ffc107;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Grade Horária Otimizada</h1>
    """

    # --- LÓGICA DA GRADE SEMANAL ---
    DIAS = ["SEG", "TER", "QUA", "QUI", "SEX"]
    DIAS_DISPLAY = {"SEG": "Segunda-feira", "TER": "Terça-feira", "QUA": "Quarta-feira", "QUI": "Quinta-feira", "SEX": "Sexta-feira"}
    SLOTS_PADRAO = ["08-10", "10-12", "13-15", "15-17"]
    SLOTS_DISPLAY = {
        "08-10": "08:00 - 10:00", "10-12": "10:00 - 12:00", 
        "13-15": "13:00 - 15:00", "15-17": "15:00 - 17:00"
    }

    # Itera sobre cada semestre
    for s, disciplinas_semestre in sorted(grade.items()):
        if not disciplinas_semestre:
            continue

        html_content += f"<h2>Semestre {s} (Créditos: {creditos_por_semestre.get(s, 0)})</h2>\n"
        
        # Prepara a estrutura de dados da grade para o semestre atual
        grade_semestre = {slot: {dia: "" for dia in DIAS} for slot in SLOTS_PADRAO}
        horarios_nao_padrao = []

        # Preenche a estrutura com as disciplinas alocadas
        for disciplina_str in sorted(disciplinas_semestre):
            match = re.search(r'(.+?)\s\(Turma:\s(.*?)\)\s---\sHorários:\s\[(.*?)\]', disciplina_str)
            if not match: continue
            
            nome, turma, horarios_str = match.groups()
            horarios = [h.strip() for h in horarios_str.split(',')]

            for horario in horarios:
                try:
                    dia, inicio, fim = horario.split('-')
                    slot = f"{inicio}-{fim}"
                    if dia in DIAS and slot in SLOTS_PADRAO:
                        grade_semestre[slot][dia] = f"<b>{nome}</b><br><small>({turma})</small>"
                    else:
                        horarios_nao_padrao.append(f"{nome} ({turma}): {horario}")
                except ValueError:
                    horarios_nao_padrao.append(f"{nome} ({turma}): {horario}")

        # Gera a tabela HTML a partir da estrutura de dados preenchida
        html_content += "<table class='grade-semanal'><thead><tr><th>Horário</th>"
        for dia in DIAS:
            html_content += f"<th>{DIAS_DISPLAY[dia]}</th>"
        html_content += "</tr></thead><tbody>"

        for slot in SLOTS_PADRAO:
            html_content += f"<tr><td class='horario-label'>{SLOTS_DISPLAY[slot]}</td>"
            for dia in DIAS:
                cell_content = grade_semestre[slot][dia]
                cell_class = "materia-cell" if cell_content else ""
                html_content += f"<td class='{cell_class}'>{cell_content}</td>"
            html_content += "</tr>"
        
        html_content += "</tbody></table>"

        # Se houver horários não padronizados, lista-os abaixo da tabela
        if horarios_nao_padrao:
            html_content += "<div class='notas'><strong>Horários não padronizados ou com formato irregular:</strong><ul>"
            for item in sorted(list(set(horarios_nao_padrao))):
                html_content += f"<li>{item}</li>"
            html_content += "</ul></div>"

    html_content += "</div></body></html>"
    
    with open(nome_arquivo, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print("-" * 50)
    print(f"\n✅ Visualização da grade foi salva no arquivo: '{nome_arquivo}'")
    print("Abra este arquivo em um navegador para ver a grade formatada.")
    print("-" * 50)


def imprimir_grade_terminal(grade, creditos_por_semestre):
    """Imprime a grade formatada no terminal."""
    for s, disciplinas_semestre in sorted(grade.items()):
        if disciplinas_semestre:
            print(f'\n--- Semestre {s} (Créditos: {creditos_por_semestre.get(s, 0)}) ---')
            for d_str in sorted(disciplinas_semestre):
                print(f'  - {d_str}')