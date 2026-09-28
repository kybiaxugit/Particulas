import math
import random
import json
from pathlib import Path
import pygame
from exporter import export_to_excel
from genetics import ParticleDNA, DEFAULT_GENOME_CONFIG
from simulation import (
    TIPOS_CIENTIFICOS, MAX_TIPOS, WORLD_W, WORLD_H, Particle,
    rebuild_particles, resize_matrix, world_to_screen, evaluar_estado_sistema,
    SPECIES_GENOME_TEMPLATES
)

UI_WIDTH = 500
WIDTH, HEIGHT = 850 + UI_WIDTH, 900  
FPS = 60

LINK_REACH = 45.0
LINK_REACH_SQ = LINK_REACH * LINK_REACH
LINK_HYSTERESIS = 8.0
POLYGON_ALPHA = 40
LINE_ALPHA = 100
ui_mode = "main"
editor_species = 0
editor_gene_index = 0
genetic_input_value = ""
genetic_notice = ""

friction = 0.85
base_max_speed = 4.0
rMax = 75.0
paused = False
evolution_on = True

temperatura = 50.0
generacion = 0
simulation_history = [] 

zoom = 0.35  
pan_x = 0.0
pan_y = 0.0
dragging_map = False
last_mouse_pos = (0, 0)

global_id_counter = 0
nacimientos_totales = 0
muertes_totales = 0
selected_particle = None

PRESETS = {
    "Red Cristalina (Estable)": [[-0.2, 0.8, -0.5, 0.1], [-0.5, -0.2, 0.9, -0.4], [0.9, -0.6, -0.1, 0.3], [0.1, 0.2, -0.3, -0.2]],
    "Fluido Newtoniano": [[0.1, -0.3, 0.5, -0.2], [-0.4, 0.2, 0.6, -0.5], [-0.2, 0.1, 0.1, -0.6], [-0.3, -0.7, -0.1, -0.3]]
}

num_types = 4
particles_per_type = 300  
matrix = [[round(random.uniform(-1.0, 1.0), 2) for _ in range(num_types)] for _ in range(num_types)]
preset_name = "Matriz Estocástica"

def draw_button(screen, font, text, x, y, w, h, base_color, hover_color, mx, my):
    rect = pygame.Rect(x, y, w, h)
    color = hover_color if rect.collidepoint(mx, my) else base_color
    pygame.draw.rect(screen, color, rect, border_radius=4)
    text_surf = fit_text(font, text, w - 10)
    text_rect = text_surf.get_rect(center=rect.center)
    screen.blit(text_surf, text_rect)
    return rect

def fit_text(font, text, max_width):
    original, fitted = str(text), str(text)
    while fitted and font.size(fitted)[0] > max_width:
        fitted = fitted[:-1]
    if fitted != original and len(fitted) > 3:
        fitted = fitted[:-3] + "..."
    return font.render(fitted, True, (255, 255, 255))

def toroidal_distance_sq(a, b):
    dx, dy = abs(a.x - b.x), abs(a.y - b.y)
    dx, dy = min(dx, WORLD_W - dx), min(dy, WORLD_H - dy)
    return dx * dx + dy * dy

def genome_file_path():
    return Path(__file__).with_name("species_genetics.json")

def load_species_genomes():
    try:
        saved = json.loads(genome_file_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    if not isinstance(saved, list):
        return
    for species_index, values in enumerate(saved[:len(SPECIES_GENOME_TEMPLATES)]):
        if not isinstance(values, dict):
            continue
        for key, value in values.items():
            spec = DEFAULT_GENOME_CONFIG.gene_specs.get(key)
            if spec is None:
                continue
            try:
                SPECIES_GENOME_TEMPLATES[species_index][key] = max(spec.min_val, min(spec.max_val, float(value)))
            except (TypeError, ValueError):
                continue

def save_species_genomes():
    genome_file_path().write_text(json.dumps(SPECIES_GENOME_TEMPLATES, ensure_ascii=False, indent=2), encoding="utf-8")

def draw_numeric_control(screen, font_small, label, x, y, val_str, input_id, active_input, input_text, mx, my):
    screen.blit(font_small.render(label, True, (226, 232, 240)), (x, y))
    btn_minus = draw_button(screen, font_small, "-", x, y+20, 24, 24, (71, 85, 105), (100, 116, 139), mx, my)
    box_rect = pygame.Rect(x+28, y+20, 60, 24)
    is_active = (active_input == input_id)
    color = (15, 23, 42) if not is_active else (30, 58, 138)
    pygame.draw.rect(screen, color, box_rect, border_radius=4)
    pygame.draw.rect(screen, (56, 189, 248) if is_active else (100, 116, 139), box_rect, width=1, border_radius=4)
    display_text = input_text if is_active else val_str
    screen.blit(fit_text(font_small, display_text, box_rect.width - 8), (box_rect.x + 4, box_rect.y + 5))
    btn_plus = draw_button(screen, font_small, "+", x+92, y+20, 24, 24, (71, 85, 105), (100, 116, 139), mx, my)
    return {'minus': btn_minus, 'plus': btn_plus, 'box': box_rect}

def draw_genetics_ui(screen, font, font_small, font_mini, mx, my, current_window_h, active_input, input_text):
    ui_start_x = max(400, WIDTH - UI_WIDTH)
    panel_w = WIDTH - ui_start_x
    pygame.draw.rect(screen, (15, 23, 42), (ui_start_x, 0, panel_w, current_window_h))
    pygame.draw.line(screen, (51, 65, 85), (ui_start_x, 0), (ui_start_x, current_window_h), 2)
    screen.blit(font.render("EDITOR DE ADN POR ESPECIE", True, (241, 245, 249)), (ui_start_x + 16, 18))
    screen.blit(font_small.render("El alelo editado se hereda; el fenotipo se expresa", True, (148, 163, 184)), (ui_start_x + 16, 48))

    widgets = {}
    species_name = TIPOS_CIENTIFICOS[editor_species]["nombre"]
    widgets['species_prev'] = draw_button(screen, font_small, "< Especie", ui_start_x + 16, 88, 105, 30, (51, 65, 85), (71, 85, 105), mx, my)
    widgets['species_next'] = draw_button(screen, font_small, "Especie >", ui_start_x + 132, 88, 105, 30, (51, 65, 85), (71, 85, 105), mx, my)
    screen.blit(font.render(f"{species_name}  |  {editor_species + 1}/{num_types}", True, TIPOS_CIENTIFICOS[editor_species]["color"]), (ui_start_x + 250, 94))

    keys = list(DEFAULT_GENOME_CONFIG.gene_specs)
    gene_key = keys[editor_gene_index % len(keys)]
    spec = DEFAULT_GENOME_CONFIG.gene_specs[gene_key]
    template = SPECIES_GENOME_TEMPLATES[editor_species]
    current_value = template.get(gene_key, spec.default_val)
    try:
        pending_value = float(genetic_input_value.replace(',', '.')) if genetic_input_value else current_value
    except ValueError:
        pending_value = current_value
    widgets['gene_prev'] = draw_button(screen, font_small, "< Rasgo", ui_start_x + 16, 140, 105, 30, (51, 65, 85), (71, 85, 105), mx, my)
    widgets['gene_next'] = draw_button(screen, font_small, "Rasgo >", ui_start_x + 132, 140, 105, 30, (51, 65, 85), (71, 85, 105), mx, my)
    screen.blit(font.render(f"{spec.name} ({spec.symbol})", True, (226, 232, 240)), (ui_start_x + 16, 184))
    screen.blit(font_small.render(f"Intervalo permitido: {spec.min_val:g}–{spec.max_val:g} {spec.unit}", True, (148, 163, 184)), (ui_start_x + 16, 214))
    screen.blit(font_small.render(f"Valor heredable de {species_name}: {current_value:.3f} {spec.unit}", True, (16, 185, 129)), (ui_start_x + 16, 238))
    widgets['value'] = draw_numeric_control(screen, font_small, "Editar alelo", ui_start_x + 16, 270, f"{pending_value:.3f}", 'gene_value', active_input, input_text, mx, my)
    widgets['apply'] = draw_button(screen, font_small, "Aplicar", ui_start_x + 16, 330, 125, 32, (5, 120, 95), (16, 150, 115), mx, my)
    widgets['save'] = draw_button(screen, font_small, "Guardar ADN", ui_start_x + 150, 330, 125, 32, (30, 64, 75), (14, 116, 144), mx, my)
    widgets['tutorial'] = draw_button(screen, font_small, "Tutorial", ui_start_x + 284, 330, 85, 32, (51, 65, 85), (71, 85, 105), mx, my)
    widgets['back'] = draw_button(screen, font_small, "Volver", ui_start_x + 378, 330, 85, 32, (51, 65, 85), (71, 85, 105), mx, my)
    desc = spec.description
    words, line, y = desc.split(), "", 390
    for word in words:
        candidate = f"{line} {word}".strip()
        if font_small.size(candidate)[0] > panel_w - 32:
            screen.blit(font_small.render(line, True, (200, 210, 220)), (ui_start_x + 16, y)); y += 22; line = word
        else:
            line = candidate
    if line:
        screen.blit(font_small.render(line, True, (200, 210, 220)), (ui_start_x + 16, y))
    screen.blit(fit_text(font_mini, genetic_notice or "Se aplica a individuos vivos y a futuros nacimientos de esta especie.", panel_w - 32), (ui_start_x + 16, current_window_h - 36))
    return widgets


def draw_tutorial_ui(screen, font, font_small, mx, my, current_window_h):
    ui_start_x = max(400, WIDTH - UI_WIDTH)
    panel_w = WIDTH - ui_start_x
    pygame.draw.rect(screen, (15, 23, 42), (ui_start_x, 0, panel_w, current_window_h))
    pygame.draw.line(screen, (51, 65, 85), (ui_start_x, 0), (ui_start_x, current_window_h), 2)
    screen.blit(font.render("GUÍA RÁPIDA | GENÉTICA Y AFINIDAD", True, (241, 245, 249)), (ui_start_x + 16, 18))
    paragraphs = [
        ("1. Editar el ADN", "Pulsa «Editar ADN especie». Elige especie y rasgo con los botones. Modifica el alelo y pulsa «Aplicar a especie». El cambio afecta a los individuos vivos de esa especie y a sus descendientes."),
        ("2. Atracción y repulsión", "En la matriz, cada fila es la especie que ejerce la interacción y cada columna la especie receptora. Clic izquierdo aumenta el valor (+0,1); clic derecho lo reduce (−0,1). Verde indica atracción, rojo repulsión; el rango es −1 a +1."),
        ("3. ADN frente a matriz", "La matriz define la interacción base entre especies. El gen «Modificador de afinidad» la escala según f efectiva = f matriz × (1 + alelo ADN). La repulsión de contacto cercano sigue activa como protección."),
        ("4. Explorar", "Haz clic en una partícula para ver sus fenotipos expresados. Rueda del ratón: zoom. Arrastra: desplazar el mapa. Espacio: pausa. E: activar o desactivar evolución."),
    ]
    y = 72
    for heading, body in paragraphs:
        screen.blit(font.render(heading, True, (56, 189, 248)), (ui_start_x + 16, y)); y += 30
        line = ""
        for word in body.split():
            candidate = f"{line} {word}".strip()
            if font_small.size(candidate)[0] > panel_w - 32:
                screen.blit(font_small.render(line, True, (220, 226, 232)), (ui_start_x + 16, y)); y += 23; line = word
            else:
                line = candidate
        if line:
            screen.blit(font_small.render(line, True, (220, 226, 232)), (ui_start_x + 16, y)); y += 23
        y += 18
    return {'back': draw_button(screen, font_small, "Volver", ui_start_x + 16, current_window_h - 52, 110, 32, (51, 65, 85), (71, 85, 105), mx, my)}


def draw_ui(screen, font, font_small, font_mini, font_hud, mx, my, avg_kinetic, spatial_entropy, active_links, total_pressure, sim_screen_w, current_window_h, active_input, input_text, population=None):
    if ui_mode == "genetics":
        return draw_genetics_ui(screen, font, font_small, font_mini, mx, my, current_window_h, active_input, input_text)
    if ui_mode == "tutorial":
        return draw_tutorial_ui(screen, font, font_small, mx, my, current_window_h)
    ui_start_x = sim_screen_w
    ui_current_width = WIDTH - sim_screen_w
    ui = {}
    
    # Fondo UI
    pygame.draw.rect(screen, (15, 23, 42), (ui_start_x, 0, ui_current_width, current_window_h))
    pygame.draw.line(screen, (51, 65, 85), (ui_start_x, 0), (ui_start_x, current_window_h), 2)
    
    # Panel de Estado
    screen.blit(font.render("LABORATORIO | EVOLUCIÓN", True, (241, 245, 249)), (ui_start_x + 15, 15))
    eval_text, eval_color = evaluar_estado_sistema(avg_kinetic, spatial_entropy, active_links, temperatura, total_pressure)
    
    pygame.draw.rect(screen, (30, 41, 59), (ui_start_x + 15, 45, ui_current_width - 30, 105), border_radius=6)
    screen.blit(font_small.render(f"Estado Actual: {eval_text}", True, eval_color), (ui_start_x + 25, 55))
    screen.blit(font_small.render(f"Temp. Global: {temperatura:.1f} °C | Entropía: {spatial_entropy:.1f}", True, (226, 232, 240)), (ui_start_x + 25, 75))
    population = population if population is not None else particles_per_type * num_types
    screen.blit(font_small.render(f"Fotograma: {generacion} | Población viva: {population}", True, (148, 163, 184)), (ui_start_x + 25, 95))
    screen.blit(font_small.render(f"Genotipo Habilitado: {'SÍ (Mutación Activa)' if evolution_on else 'NO'}", True, (16, 185, 129) if evolution_on else (239, 68, 68)), (ui_start_x + 25, 115))

    y_offset = 165
    ui['temp'] = draw_numeric_control(screen, font_small, "Temp. (°C)", ui_start_x + 15, y_offset, f"{temperatura:.1f}", 'temp', active_input, input_text, mx, my)
    ui['types'] = draw_numeric_control(screen, font_small, "Especies", ui_start_x + 150, y_offset, f"{num_types}", 'types', active_input, input_text, mx, my)
    ui['part'] = draw_numeric_control(screen, font_small, "Densidad/E", ui_start_x + 285, y_offset, f"{particles_per_type}", 'part', active_input, input_text, mx, my)
    
    y_offset += 60
    ui['fric'] = draw_numeric_control(screen, font_small, "Fricción (Base)", ui_start_x + 15, y_offset, f"{friction:.2f}", 'fric', active_input, input_text, mx, my)
    ui['rmax'] = draw_numeric_control(screen, font_small, "Radio Interacción", ui_start_x + 150, y_offset, f"{rMax:.0f}", 'rmax', active_input, input_text, mx, my)
    ui['vel'] = draw_numeric_control(screen, font_small, "Velocidad Máx", ui_start_x + 285, y_offset, f"{base_max_speed:.1f}", 'vel', active_input, input_text, mx, my)

    y_offset += 65
    ui['btn_pause'] = draw_button(screen, font_small, "Pausa" if not paused else "Reanudar", ui_start_x + 15, y_offset, 90, 28, (124, 58, 237), (139, 92, 246), mx, my)
    ui['btn_evo'] = draw_button(screen, font_small, "ADN / Mutar", ui_start_x + 115, y_offset, 90, 28, (16, 185, 129) if evolution_on else (71, 85, 105), (52, 211, 153), mx, my)
    ui['btn_reset'] = draw_button(screen, font_small, "Reiniciar", ui_start_x + 215, y_offset, 90, 28, (217, 119, 6), (245, 158, 11), mx, my)
    ui['btn_csv'] = draw_button(screen, font_small, "Excel", ui_start_x + 315, y_offset, 90, 28, (5, 150, 105), (16, 185, 129), mx, my)

    y_offset += 50
    ui['mutation'] = draw_numeric_control(screen, font_small, "Tasa mutación", ui_start_x + 15, y_offset, f"{DEFAULT_GENOME_CONFIG.global_mutation_rate:.3f}", 'mutation', active_input, input_text, mx, my)
    ui['mut_strength'] = draw_numeric_control(screen, font_small, "Magnitud mutación", ui_start_x + 150, y_offset, f"{DEFAULT_GENOME_CONFIG.mutation_strength:.2f}", 'mut_strength', active_input, input_text, mx, my)
    ui['epigenetics'] = draw_button(screen, font_small, "Epigenética: Sí" if DEFAULT_GENOME_CONFIG.enable_epigenetics else "Epigenética: No", ui_start_x + 285, y_offset + 20, 125, 24, (30, 64, 75), (14, 116, 144), mx, my)

    ui['btn_genetic_editor'] = draw_button(screen, font_small, "Editar ADN especie", ui_start_x + 15, y_offset + 50, 175, 28, (14, 116, 144), (8, 145, 178), mx, my)
    ui['btn_tutorial'] = draw_button(screen, font_small, "Guía: ADN y matriz", ui_start_x + 202, y_offset + 50, 190, 28, (51, 65, 85), (71, 85, 105), mx, my)

    y_offset += 92
    screen.blit(font_small.render("MATRIZ DE AFINIDAD (ATRACCIÓN / REPULSIÓN)", True, (241, 245, 249)), (ui_start_x + 15, y_offset))
    y_offset += 25
    
    start_x, start_y = ui_start_x + 20, y_offset
    cell_size = min(40, 310 // num_types)
    visible_types = min(num_types, max(0, (current_window_h - start_y - (230 if selected_particle else 12)) // cell_size))
    f_matrix = font_mini if num_types > 5 else font_small
    ui['matrix'] = []

    for i in range(visible_types):
        c_name = TIPOS_CIENTIFICOS[i]["nombre"][:3]
        c_color = TIPOS_CIENTIFICOS[i]["color"]
        screen.blit(f_matrix.render(c_name, True, c_color), (start_x + 40 + i * cell_size, start_y - 18))
        screen.blit(f_matrix.render(c_name, True, c_color), (start_x, start_y + (cell_size//4) + i * cell_size))

        for j in range(visible_types):
            val = matrix[i][j]
            base_color = (16, 185, 129) if val > 0 else (239, 68, 68) if val < 0 else (51, 65, 85)
            intensity = min(255, abs(int(val * 200)) + 55)
            r, g, b = [max(0, min(255, int(base_color[k] * (intensity/255) + [30,41,59][k] * (1-intensity/255)))) for k in range(3)]
            rect_x, rect_y = start_x + 40 + j * cell_size, start_y + i * cell_size
            cell_rect = pygame.Rect(rect_x, rect_y, cell_size-2, cell_size-2)
            
            if cell_rect.collidepoint(mx, my): pygame.draw.rect(screen, (255, 255, 255), (rect_x-1, rect_y-1, cell_size, cell_size), border_radius=3, width=2)
            pygame.draw.rect(screen, (r, g, b), (rect_x, rect_y, cell_size-3, cell_size-3), border_radius=3)
            screen.blit(f_matrix.render(f"{val:.1f}", True, (255, 255, 255)), (rect_x + 2, rect_y + cell_size//4))
            ui['matrix'].append({'rect': cell_rect, 'row': i, 'col': j})
    if visible_types < num_types:
        screen.blit(font_mini.render(f"Matriz parcial: {visible_types}/{num_types}; deselecciona la partícula para ver todo", True, (148, 163, 184)), (start_x, start_y + visible_types * cell_size + 2))

    # Información HUD Genética de la Partícula Seleccionada
    if selected_particle:
        y_hud = current_window_h - 220
        pygame.draw.rect(screen, (15, 23, 42), (ui_start_x, y_hud, ui_current_width, 220))
        pygame.draw.line(screen, selected_particle.dna.color_rgb, (ui_start_x, y_hud), (WIDTH, y_hud), 3)
        
        screen.blit(font.render("ANÁLISIS DE SECUENCIA GENÉTICA", True, (241, 245, 249)), (ui_start_x + 15, y_hud + 15))
        
        estado_vida = "Viva" if selected_particle.alive else "Senescente / Muerta"
        screen.blit(font_hud.render(f"Especie: {TIPOS_CIENTIFICOS[selected_particle.type]['nombre']} | ID: {selected_particle.id} | {estado_vida}", True, selected_particle.dna.color_rgb), (ui_start_x + 15, y_hud + 45))
        
        # Extracción de fenotipos vivos
        telomeros = selected_particle.dna.current_telomeres
        t_min = selected_particle.dna.get_phenotype("thermal_min", temperatura)
        t_max = selected_particle.dna.get_phenotype("thermal_max", temperatura)
        m_cell = selected_particle.dna.get_phenotype("cellular_mass", temperatura)
        eficiencia = selected_particle.dna.get_phenotype("metabolic_efficiency", temperatura)
        motilidad = selected_particle.dna.get_phenotype("motility", temperatura)
        resistencia = selected_particle.dna.get_phenotype("stress_resistance", temperatura)
        fecundidad = selected_particle.dna.get_phenotype("fecundity", temperatura)
        
        col1, col2 = ui_start_x + 15, ui_start_x + 220
        screen.blit(font_hud.render(f"Longevidad (Telómeros): {telomeros:.0f} pb", True, (200, 200, 200)), (col1, y_hud + 75))
        screen.blit(font_hud.render(f"Tolerancia Térmica: {t_min:.1f}°C a {t_max:.1f}°C", True, (200, 200, 200)), (col1, y_hud + 95))
        screen.blit(font_hud.render(f"Masa Inercial: {m_cell:.2f} pg", True, (200, 200, 200)), (col1, y_hud + 115))
        screen.blit(font_hud.render(f"Eficiencia Metabólica: {eficiencia:.2f} η", True, (200, 200, 200)), (col1, y_hud + 135))
        
        screen.blit(font_hud.render(f"Generación / Edad: {selected_particle.age} c", True, (200, 200, 200)), (col2, y_hud + 75))
        screen.blit(font_hud.render(f"Reproducciones (Mitosis/Meiosis): {selected_particle.children}", True, (200, 200, 200)), (col2, y_hud + 95))
        screen.blit(font_hud.render(f"Velocidad: {math.hypot(selected_particle.vx, selected_particle.vy):.2f} v", True, (200, 200, 200)), (col2, y_hud + 115))
        screen.blit(font_hud.render(f"Motilidad: {motilidad:.2f}× | Resistencia: {resistencia:.2f}×", True, (200, 200, 200)), (col2, y_hud + 135))
        screen.blit(font_hud.render(f"Fecundidad: {fecundidad:.2f}×", True, (200, 200, 200)), (col2, y_hud + 155))

    return ui

def main():
    global particles_per_type, num_types, matrix, preset_name, friction, base_max_speed, rMax, paused, evolution_on, zoom, pan_x, pan_y, dragging_map, last_mouse_pos, temperatura, generacion, WIDTH, HEIGHT
    global global_id_counter, nacimientos_totales, muertes_totales, selected_particle
    global ui_mode, editor_species, editor_gene_index, genetic_input_value, genetic_notice
    
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("Simulador Bio-Termodinámico Genético")
    
    # Pre-crear superficie para optimizar rendimiento (Anti-Lag)
    shapes_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 24)
    font_small = pygame.font.Font(None, 20)
    font_mini = pygame.font.Font(None, 16)
    font_hud = pygame.font.Font(None, 18)

    load_species_genomes()
    particles, global_id_counter, nacimientos_totales, muertes_totales, generacion = rebuild_particles([], num_types, particles_per_type, simulation_history)
    running = True
    active_input, input_text = None, ""
    cached_lines = []
    link_state = set()

    while running:
        current_window_w, current_window_h = screen.get_size()
        sim_screen_w = max(400, current_window_w - UI_WIDTH)
        sim_screen_h = current_window_h
        mx, my = pygame.mouse.get_pos()
        
        if not paused: generacion += 1

        grid_cols = max(1, int(math.ceil(WORLD_W / rMax)))
        grid_rows = max(1, int(math.ceil(WORLD_H / rMax)))
        num_cells = grid_cols * grid_rows
        grid_signature = (grid_cols, grid_rows)
        if locals().get("neighbor_signature") != grid_signature:
            neighbor_indices = []
            for cy in range(grid_rows):
                for cx in range(grid_cols):
                    neighbor_indices.append(sorted({((cy + dy) % grid_rows) * grid_cols + ((cx + dx) % grid_cols)
                                                    for dy in (-1, 0, 1) for dx in (-1, 0, 1)}))
            neighbor_signature = grid_signature

        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE): running = False
            elif event.type == pygame.VIDEORESIZE:
                WIDTH, HEIGHT = max(900, event.w), max(700, event.h)
                screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
                shapes_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            
            elif event.type == pygame.KEYDOWN:
                if active_input:
                    if event.key == pygame.K_RETURN:
                        try:
                            input_text = input_text.replace(',', '.')
                            if active_input == 'temp': temperatura = max(0.0, min(150.0, float(input_text)))
                            elif active_input == 'types':
                                num_types, matrix = resize_matrix(int(input_text), num_types, matrix)
                                particles, global_id_counter, nacimientos_totales, muertes_totales, generacion = rebuild_particles(particles, num_types, particles_per_type, simulation_history)
                            elif active_input == 'part':
                                particles_per_type = max(10, min(2000, int(input_text)))
                                particles, global_id_counter, nacimientos_totales, muertes_totales, generacion = rebuild_particles(particles, num_types, particles_per_type, simulation_history)
                            elif active_input == 'fric': friction = max(0.01, min(0.99, float(input_text)))
                            elif active_input == 'rmax': rMax = max(10.0, min(250.0, float(input_text)))
                            elif active_input == 'vel': base_max_speed = max(0.5, min(15.0, float(input_text)))
                            elif active_input == 'mutation': DEFAULT_GENOME_CONFIG.global_mutation_rate = max(0.0, min(1.0, float(input_text)))
                            elif active_input == 'mut_strength': DEFAULT_GENOME_CONFIG.mutation_strength = max(0.0, min(2.0, float(input_text)))
                            elif active_input == 'gene_value': genetic_input_value = input_text
                        except: pass
                        active_input = None
                    elif event.key == pygame.K_BACKSPACE: input_text = input_text[:-1]
                    else:
                        if event.unicode in '0123456789.-,': input_text += event.unicode
                else:
                    if event.key in (pygame.K_SPACE, pygame.K_p): paused = not paused
                    elif event.key == pygame.K_e: evolution_on = not evolution_on
            
            elif event.type == pygame.MOUSEWHEEL and mx < sim_screen_w:
                old_zoom = zoom
                zoom = min(8.0, zoom * 1.15) if event.y > 0 else max(0.05, zoom / 1.15)
                pan_x -= (mx - (sim_screen_w / 2 + pan_x)) * (zoom / old_zoom - 1)
                pan_y -= (my - (sim_screen_h / 2 + pan_y)) * (zoom / old_zoom - 1)

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if mx < sim_screen_w and event.button == 1:
                    dragging_map, last_mouse_pos = True, event.pos
                    active_input = None 
                    
                    click_wx = (mx - sim_screen_w/2 - pan_x) / zoom + WORLD_W/2
                    click_wy = (my - sim_screen_h/2 - pan_y) / zoom + WORLD_H/2
                    min_dist = 60 / zoom
                    selected_particle = None
                    for p in particles:
                        dist = math.hypot(p.x - click_wx, p.y - click_wy)
                        if dist < min_dist:
                            selected_particle = p
                            min_dist = dist

                elif mx >= sim_screen_w:
                    ui = draw_ui(screen, font, font_small, font_mini, font_hud, mx, my, 0, 0, 0, 0, sim_screen_w, current_window_h, active_input, input_text, len(particles))
                    if ui_mode == 'tutorial':
                        if ui['back'].collidepoint(mx, my): ui_mode = 'main'
                    elif ui_mode == 'genetics':
                        gene_keys = list(DEFAULT_GENOME_CONFIG.gene_specs)
                        gene_key = gene_keys[editor_gene_index % len(gene_keys)]
                        gene_spec = DEFAULT_GENOME_CONFIG.gene_specs[gene_key]
                        gene_value = SPECIES_GENOME_TEMPLATES[editor_species].get(gene_key, gene_spec.default_val)
                        if ui['back'].collidepoint(mx, my): ui_mode = 'main'; active_input = None
                        elif ui['tutorial'].collidepoint(mx, my): ui_mode = 'tutorial'; active_input = None
                        elif ui['species_prev'].collidepoint(mx, my):
                            editor_species = (editor_species - 1) % num_types
                            genetic_input_value = str(SPECIES_GENOME_TEMPLATES[editor_species].get(gene_key, gene_spec.default_val))
                        elif ui['species_next'].collidepoint(mx, my):
                            editor_species = (editor_species + 1) % num_types
                            genetic_input_value = str(SPECIES_GENOME_TEMPLATES[editor_species].get(gene_key, gene_spec.default_val))
                        elif ui['gene_prev'].collidepoint(mx, my):
                            editor_gene_index = (editor_gene_index - 1) % len(gene_keys)
                            next_key = gene_keys[editor_gene_index]
                            genetic_input_value = str(SPECIES_GENOME_TEMPLATES[editor_species].get(next_key, DEFAULT_GENOME_CONFIG.gene_specs[next_key].default_val))
                        elif ui['gene_next'].collidepoint(mx, my):
                            editor_gene_index = (editor_gene_index + 1) % len(gene_keys)
                            next_key = gene_keys[editor_gene_index]
                            genetic_input_value = str(SPECIES_GENOME_TEMPLATES[editor_species].get(next_key, DEFAULT_GENOME_CONFIG.gene_specs[next_key].default_val))
                        elif ui['value']['box'].collidepoint(mx, my): active_input = 'gene_value'; input_text = f"{gene_value:.3f}"
                        elif ui['value']['minus'].collidepoint(mx, my):
                            try: base_value = float(genetic_input_value.replace(',', '.')) if genetic_input_value else gene_value
                            except ValueError: base_value = gene_value
                            genetic_input_value = str(max(gene_spec.min_val, base_value - gene_spec.mutation_step))
                        elif ui['value']['plus'].collidepoint(mx, my):
                            try: base_value = float(genetic_input_value.replace(',', '.')) if genetic_input_value else gene_value
                            except ValueError: base_value = gene_value
                            genetic_input_value = str(min(gene_spec.max_val, base_value + gene_spec.mutation_step))
                        elif ui['apply'].collidepoint(mx, my):
                            try:
                                candidate = input_text if active_input == 'gene_value' else genetic_input_value
                                new_value = max(gene_spec.min_val, min(gene_spec.max_val, float(candidate.replace(',', '.'))))
                                SPECIES_GENOME_TEMPLATES[editor_species][gene_key] = new_value
                                for particle in particles:
                                    if particle.alive and particle.type == editor_species:
                                        particle.dna.alleles[gene_key] = new_value
                                        if gene_key == 'telomere_length': particle.dna.current_telomeres = new_value
                                genetic_input_value = str(new_value)
                                active_input = None
                            except (TypeError, ValueError):
                                pass
                        elif ui['save'].collidepoint(mx, my):
                            try:
                                save_species_genomes()
                                genetic_notice = "ADN guardado en species_genetics.json"
                            except OSError as error:
                                genetic_notice = f"No se pudo guardar: {error}"
                    elif ui['btn_genetic_editor'].collidepoint(mx, my):
                        editor_species = min(editor_species, num_types - 1)
                        ui_mode = 'genetics'
                        active_input = None
                        gene_keys = list(DEFAULT_GENOME_CONFIG.gene_specs)
                        gene_key = gene_keys[editor_gene_index % len(gene_keys)]
                        genetic_input_value = str(SPECIES_GENOME_TEMPLATES[editor_species].get(gene_key, DEFAULT_GENOME_CONFIG.gene_specs[gene_key].default_val))
                    elif ui['btn_tutorial'].collidepoint(mx, my): ui_mode = 'tutorial'; active_input = None
                    elif ui['temp']['box'].collidepoint(mx, my): active_input = 'temp'; input_text = str(round(temperatura,1))
                    elif ui['temp']['minus'].collidepoint(mx, my): temperatura = max(0.0, temperatura - 10.0)
                    elif ui['temp']['plus'].collidepoint(mx, my): temperatura = min(150.0, temperatura + 10.0)
                    elif ui['types']['box'].collidepoint(mx, my): active_input = 'types'; input_text = str(num_types)
                    elif ui['types']['minus'].collidepoint(mx, my):
                        num_types, matrix = resize_matrix(num_types - 1, num_types, matrix)
                        particles, global_id_counter, nacimientos_totales, muertes_totales, generacion = rebuild_particles(particles, num_types, particles_per_type, simulation_history)
                    elif ui['types']['plus'].collidepoint(mx, my):
                        num_types, matrix = resize_matrix(num_types + 1, num_types, matrix)
                        particles, global_id_counter, nacimientos_totales, muertes_totales, generacion = rebuild_particles(particles, num_types, particles_per_type, simulation_history)
                    elif ui['part']['box'].collidepoint(mx, my): active_input = 'part'; input_text = str(particles_per_type)
                    elif ui['part']['minus'].collidepoint(mx, my):
                        particles_per_type = max(30, particles_per_type - 50)
                        particles, global_id_counter, nacimientos_totales, muertes_totales, generacion = rebuild_particles(particles, num_types, particles_per_type, simulation_history)
                    elif ui['part']['plus'].collidepoint(mx, my):
                        particles_per_type = min(2000, particles_per_type + 50)
                        particles, global_id_counter, nacimientos_totales, muertes_totales, generacion = rebuild_particles(particles, num_types, particles_per_type, simulation_history)
                    
                    elif ui['btn_pause'].collidepoint(mx, my): paused = not paused
                    elif ui['btn_reset'].collidepoint(mx, my):
                        particles, global_id_counter, nacimientos_totales, muertes_totales, generacion = rebuild_particles(particles, num_types, particles_per_type, simulation_history)
                    elif ui['btn_evo'].collidepoint(mx, my): evolution_on = not evolution_on
                    elif ui['epigenetics'].collidepoint(mx, my): DEFAULT_GENOME_CONFIG.enable_epigenetics = not DEFAULT_GENOME_CONFIG.enable_epigenetics
                    elif ui['mutation']['box'].collidepoint(mx, my): active_input = 'mutation'; input_text = f"{DEFAULT_GENOME_CONFIG.global_mutation_rate:.3f}"
                    elif ui['mut_strength']['box'].collidepoint(mx, my): active_input = 'mut_strength'; input_text = f"{DEFAULT_GENOME_CONFIG.mutation_strength:.2f}"
                    elif ui['mutation']['minus'].collidepoint(mx, my): DEFAULT_GENOME_CONFIG.global_mutation_rate = max(0.0, DEFAULT_GENOME_CONFIG.global_mutation_rate - 0.01)
                    elif ui['mutation']['plus'].collidepoint(mx, my): DEFAULT_GENOME_CONFIG.global_mutation_rate = min(1.0, DEFAULT_GENOME_CONFIG.global_mutation_rate + 0.01)
                    elif ui['mut_strength']['minus'].collidepoint(mx, my): DEFAULT_GENOME_CONFIG.mutation_strength = max(0.0, DEFAULT_GENOME_CONFIG.mutation_strength - 0.02)
                    elif ui['mut_strength']['plus'].collidepoint(mx, my): DEFAULT_GENOME_CONFIG.mutation_strength = min(2.0, DEFAULT_GENOME_CONFIG.mutation_strength + 0.02)
                    elif ui['btn_csv'].collidepoint(mx, my): export_to_excel(matrix, simulation_history, preset_name, num_types, particles_per_type, len(particles), generacion)
                    
                    else:
                        for cell in ui['matrix']:
                            if cell['rect'].collidepoint(mx, my):
                                if event.button == 1: matrix[cell['row']][cell['col']] = min(1.0, round(matrix[cell['row']][cell['col']] + 0.1, 2))
                                elif event.button == 3: matrix[cell['row']][cell['col']] = max(-1.0, round(matrix[cell['row']][cell['col']] - 0.1, 2))
                                break

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1: dragging_map = False
            elif event.type == pygame.MOUSEMOTION and dragging_map:
                pan_x += event.pos[0] - last_mouse_pos[0]
                pan_y += event.pos[1] - last_mouse_pos[1]
                last_mouse_pos = event.pos

        lines_to_draw, tris_to_draw = [], []
        total_kinetic_energy, total_pressure = 0.0, 0.0

        if not paused:
            grid = [[] for _ in range(num_cells)]
            current_link_state = set()
            for p in particles:
                if p.alive:
                    grid[min(grid_rows - 1, max(0, int(p.y / rMax))) * grid_cols + min(grid_cols - 1, max(0, int(p.x / rMax)))].append(p)

            nuevas_particulas = []
            
            for p1 in particles:
                if not p1.alive: continue
                p1.age += 1
                
                # --- Integración Genética: Senescencia y Tolerancia Térmica ---
                if evolution_on:
                    p1.dna.adapt_epigenetics(abs(temperatura - 50.0) / 30.0)
                    if p1.dna.degrade_telomeres(rate=0.015): 
                        p1.alive = False; muertes_totales += 1; continue
                
                t_max = p1.dna.get_phenotype("thermal_max", temperatura)
                t_min = p1.dna.get_phenotype("thermal_min", temperatura)
                
                resistencia = p1.dna.get_phenotype("stress_resistance", temperatura)
                if temperatura > t_max and random.random() < 0.05 / max(0.1, resistencia): p1.alive = False; muertes_totales += 1; continue
                elif temperatura < t_min and random.random() < 0.05 / max(0.1, resistencia): p1.alive = False; muertes_totales += 1; continue
                
                # Reproducción Genética (Cruce Asexual/Sexual)
                e_rep = p1.dna.get_phenotype("fertility_threshold", temperatura)
                fecundidad = p1.dna.get_phenotype("fecundity", temperatura)
                max_population = num_types * particles_per_type * 2
                if evolution_on and len(particles) + len(nuevas_particulas) < max_population and p1.age > 80 and (p1.vx**2 + p1.vy**2) > (e_rep / 10.0) and random.random() < min(0.01, 0.0005 * fecundidad):
                    p1.children += 1
                    local_cell = min(grid_rows - 1, max(0, int(p1.y / rMax))) * grid_cols + min(grid_cols - 1, max(0, int(p1.x / rMax)))
                    mates = [p2 for n_idx in neighbor_indices[local_cell] for p2 in grid[n_idx]
                             if p2 is not p1 and p2.alive and p2.type == p1.type
                             and p2.id < p1.id
                             and toroidal_distance_sq(p1, p2) < LINK_REACH_SQ]
                    child_dna = (ParticleDNA.crossover(p1.dna, random.choice(mates).dna, mutation_multiplier=1.2)
                                 if mates and random.random() < 0.35
                                 else p1.dna.reproduce_asexual(mutation_multiplier=1.2))
                    nuevas_particulas.append(Particle(global_id_counter, (p1.x + random.uniform(-40, 40)) % WORLD_W, (p1.y + random.uniform(-40, 40)) % WORLD_H, p1.type, child_dna))
                    global_id_counter += 1
                    nacimientos_totales += 1

                fx, fy, local_density = 0.0, 0.0, 0
                cell_idx = min(grid_rows - 1, max(0, int(p1.y / rMax))) * grid_cols + min(grid_cols - 1, max(0, int(p1.x / rMax)))
                
                p1_mass = p1.dna.get_phenotype("cellular_mass", temperatura)
                p1_affinity = p1.dna.get_phenotype("affinity_modifier", temperatura)

                for n_idx in neighbor_indices[cell_idx]:
                    for p2 in grid[n_idx]:
                        if not p2.alive or p1 is p2: continue

                        dx, dy = p2.x - p1.x, p2.y - p1.y
                        if dx > WORLD_W / 2: dx -= WORLD_W
                        elif dx < -WORLD_W / 2: dx += WORLD_W
                        if dy > WORLD_H / 2: dy -= WORLD_H
                        elif dy < -WORLD_H / 2: dy += WORLD_H
                        
                        dist_sq = dx * dx + dy * dy

                        if 0.0001 < dist_sq < rMax**2:
                            dist = math.sqrt(dist_sq)
                            local_density += 1
                            if dist < rMax*0.3: p1.vx, p1.vy = p1.vx * 0.98, p1.vy * 0.98

                            pair_key = (p1.id, p2.id)
                            link_reach = LINK_REACH + (LINK_HYSTERESIS if pair_key in link_state else 0.0)
                            if p1.type == p2.type and p1.id < p2.id and dist_sq < link_reach * link_reach:
                                if abs(p1.x - p2.x) < WORLD_W / 2 and abs(p1.y - p2.y) < WORLD_H / 2:
                                    lines_to_draw.append((p1.dna.color_rgb, (p1.x, p1.y), (p2.x, p2.y)))
                                    current_link_state.add(pair_key)

                            f = matrix[p1.type][p2.type] * (1.0 + p1_affinity)
                            force = (dist / (rMax*0.3) - 1.0) if dist < (rMax*0.3) else (f * (1.0 - abs(2.0 * ((dist - rMax*0.3) / (rMax * 0.7)) - 1.0)))
                            
                            # Física: F = m*a  => a = F/m
                            total_pressure += abs(force)
                            accel = force / p1_mass
                            fx += dx * (1.0 / dist) * accel
                            fy += dy * (1.0 / dist) * accel

                # Fricción Genética / Viscosidad Epigenética
                drag_base = p1.dna.get_phenotype("drag_coefficient", temperatura)
                viscosity = max(0.1, (friction * drag_base) - (local_density * 0.003))
                
                p1.vx, p1.vy = (p1.vx + fx * 0.4) * viscosity, (p1.vy + fy * 0.4) * viscosity

                speed_sq = p1.vx**2 + p1.vy**2
                current_max_speed = base_max_speed * (temperatura / 50.0) * (2.0 / p1_mass) * p1.dna.get_phenotype("motility", temperatura)
                if speed_sq > current_max_speed**2:
                    speed = math.sqrt(speed_sq)
                    p1.vx, p1.vy = (p1.vx / speed) * current_max_speed, (p1.vy / speed) * current_max_speed
                total_kinetic_energy += 0.5 * speed_sq * p1_mass

            particles = [p for p in particles if p.alive] + nuevas_particulas
            for p in particles: p.x, p.y = (p.x + p.vx) % WORLD_W, (p.y + p.vy) % WORLD_H
            cached_lines = lines_to_draw
            link_state = current_link_state

        avg_kinetic = total_kinetic_energy / len(particles) if particles else 0
        mean_x = sum(p.x for p in particles) / len(particles) if particles else 0
        mean_y = sum(p.y for p in particles) / len(particles) if particles else 0
        spatial_entropy = math.sqrt(sum((p.x - mean_x)**2 + (p.y - mean_y)**2 for p in particles) / len(particles)) if particles else 0

        # Renderizado (Limpiar en lugar de recrear)
        screen.fill((10, 15, 30), rect=(0, 0, sim_screen_w, sim_screen_h))
        shapes_surface.fill((0, 0, 0, 0))
        
        # El filtrado por FPS hacía que los enlaces aparecieran y desaparecieran
        # al cruzar el umbral de 30 FPS. Se dibuja el último estado estable.
        for color_rgb, pos1, pos2 in cached_lines:
            screen_pos1 = world_to_screen(*pos1, sim_screen_w, sim_screen_h, zoom, pan_x, pan_y)
            screen_pos2 = world_to_screen(*pos2, sim_screen_w, sim_screen_h, zoom, pan_x, pan_y)
            pygame.draw.line(shapes_surface, (*color_rgb, LINE_ALPHA), screen_pos1, screen_pos2, max(1, int(1 * zoom)))
        
        screen.blit(shapes_surface, (0, 0))

        for p in particles:
            sx, sy = world_to_screen(p.x, p.y, sim_screen_w, sim_screen_h, zoom, pan_x, pan_y)
            if -10 < sx < sim_screen_w + 10 and -10 < sy < sim_screen_h + 10:
                pygame.draw.circle(screen, p.dna.color_rgb, (int(sx), int(sy)), max(1, int(3 * zoom)))

        draw_ui(screen, font, font_small, font_mini, font_hud, mx, my, avg_kinetic, spatial_entropy, len(lines_to_draw), total_pressure, sim_screen_w, current_window_h, active_input, input_text, len(particles))
        
        if selected_particle:
            if not selected_particle.alive: selected_particle = None
            else:
                sx, sy = world_to_screen(selected_particle.x, selected_particle.y, sim_screen_w, sim_screen_h, zoom, pan_x, pan_y)
                pygame.draw.circle(screen, (255, 255, 255), (int(sx), int(sy)), max(5, int(8*zoom)), 2)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()

if __name__ == "__main__":
    main()
