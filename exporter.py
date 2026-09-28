import os
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.chart import LineChart, Reference

def export_to_excel(matrix, simulation_history, preset_name, num_types, particles_per_type, population=None, generation=None):
    wb = openpyxl.Workbook()
    
    # --- HOJA 1: RESUMEN Y CONFIGURACIÓN ---
    ws1 = wb.active
    ws1.title = "Configuración y Métricas"
    ws1.views.sheetView[0].showGridLines = True
    
    # Estilos
    header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
    title_font = Font(name="Segoe UI", size=16, bold=True, color="0F172A")
    subtitle_font = Font(name="Segoe UI", size=12, bold=True, color="334155")
    data_font = Font(name="Segoe UI", size=10)
    border_thin = Border(left=Side(style='thin', color='CBD5E1'),
                         right=Side(style='thin', color='CBD5E1'),
                         top=Side(style='thin', color='CBD5E1'),
                         bottom=Side(style='thin', color='CBD5E1'))
    
    ws1["A1"] = "INFORME DE SIMULACIÓN TERMODINÁMICA"
    ws1["A1"].font = title_font
    
    ws1["A3"] = "Parámetro"
    ws1["B3"] = "Valor"
    for col in ["A", "B"]:
        cell = ws1[f"{col}3"]
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
    
    config_data = [
        ("Preset Activo", preset_name),
        ("Número de Elementos", num_types),
        ("Densidad (Partículas/Tipo)", particles_per_type),
        ("Total Partículas Iniciales", num_types * particles_per_type)
    ]
    if population is not None:
        config_data.append(("Población viva al exportar", population))
    if generation is not None:
        config_data.append(("Fotograma / generación", generation))
    
    for row_idx, (param, val) in enumerate(config_data, start=4):
        ws1[f"A{row_idx}"] = param
        ws1[f"B{row_idx}"] = val
        ws1[f"A{row_idx}"].font = data_font
        ws1[f"B{row_idx}"].font = data_font
        ws1[f"A{row_idx}"].border = border_thin
        ws1[f"B{row_idx}"].border = border_thin
        
    # --- MATRIZ DE INTERACCIÓN ---
    ws1["D3"] = f"Matriz de Interacción ({num_types}x{num_types})"
    ws1["D3"].font = subtitle_font
    
    for i in range(num_types):
        for j in range(num_types):
            cell = ws1.cell(row=4+i, column=4+j)
            cell.value = matrix[i][j]
            cell.font = data_font
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = border_thin
            if matrix[i][j] > 0:
                cell.fill = PatternFill(start_color="D1FAE5", end_color="D1FAE5", fill_type="solid") # Verde suave
            elif matrix[i][j] < 0:
                cell.fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid") # Rojo suave

    # --- HOJA 2: HISTORIAL DE SIMULACIÓN ---
    ws2 = wb.create_sheet(title="Historial y Gráficas")
    ws2.views.sheetView[0].showGridLines = True
    
    headers = ["Iteración", "Temperatura (°C)", "Cinética Media (J)", "Entropía Espacial", "Vínculos Activos"]
    for col_idx, header in enumerate(headers, start=1):
        cell = ws2.cell(row=1, column=col_idx, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
        
    if simulation_history:
        for row_idx, data in enumerate(simulation_history, start=2):
            for col_idx, val in enumerate(data, start=1):
                cell = ws2.cell(row=row_idx, column=col_idx, value=val)
                cell.font = data_font
                cell.border = border_thin
                cell.alignment = Alignment(horizontal="center")
                
        # Gráfica de Temperatura y Cinética
        chart = LineChart()
        chart.title = "Evolución Termodinámica del Sistema"
        chart.style = 13
        chart.y_axis.title = "Valor"
        chart.x_axis.title = "Iteración"
        
        data_ref = Reference(ws2, min_col=2, min_row=1, max_col=3, max_row=len(simulation_history)+1)
        cats_ref = Reference(ws2, min_col=1, min_row=2, max_row=len(simulation_history)+1)
        chart.add_data(data_ref, titles_from_data=True)
        chart.set_categories(cats_ref)
        
        ws2.add_chart(chart, "G2")
    else:
        ws2["A2"] = "No hay datos de historial registrados todavía."
        ws2["A2"].font = data_font

    # Autoajustar columnas
    for sheet in [ws1, ws2]:
        for col in sheet.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = openpyxl.utils.get_column_letter(col[0].column)
            sheet.column_dimensions[col_letter].width = max(max_len + 4, 12)

    # Guardar archivo
    filename = os.path.abspath("simulacion_termodinamica.xlsx")
    wb.save(filename)
    print(f"¡Exportado con éxito a {filename}! 📊✨")
