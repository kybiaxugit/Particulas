import math
import random
from genetics import ParticleDNA

TIPOS_CIENTIFICOS = [
    {"nombre": "Alfa",    "color": (239, 68, 68)},
    {"nombre": "Beta",    "color": (16, 185, 129)},
    {"nombre": "Gamma",   "color": (59, 130, 246)},
    {"nombre": "Delta",   "color": (234, 179, 8)},
    {"nombre": "Épsilon", "color": (168, 85, 247)},
    {"nombre": "Zeta",    "color": (249, 115, 22)},
    {"nombre": "Eta",     "color": (14, 165, 233)},  
    {"nombre": "Theta",   "color": (236, 72, 153)},  
    {"nombre": "Iota",    "color": (139, 92, 246)},  
    {"nombre": "Kappa",   "color": (20, 184, 166)},  
    {"nombre": "Lambda",  "color": (245, 158, 11)},  
    {"nombre": "Mu",      "color": (244, 63, 94)},   
    {"nombre": "Nu",      "color": (99, 102, 241)},  
    {"nombre": "Xi",      "color": (132, 204, 22)},  
    {"nombre": "Ómicron", "color": (130, 115, 62)}
]
MAX_TIPOS = len(TIPOS_CIENTIFICOS)

WORLD_W = 4000
WORLD_H = 4000
SPECIES_GENOME_TEMPLATES = [{} for _ in range(MAX_TIPOS)]

class Particle:
    __slots__ = ['id', 'x', 'y', 'vx', 'vy', 'type', 'age', 'hardness', 'children', 'alive', 'dna']
    def __init__(self, pid, x, y, p_type, dna=None):
        self.id = pid
        self.x = x
        self.y = y
        self.vx = 0.0
        self.vy = 0.0
        self.type = p_type
        self.age = 0
        self.hardness = random.uniform(20.0, 100.0)
        self.children = 0
        self.alive = True
        # Asignar ADN, si no se pasa uno, se genera con el color base de la familia
        self.dna = dna if dna is not None else ParticleDNA(color_rgb=TIPOS_CIENTIFICOS[p_type]["color"])
        if dna is None and 0 <= p_type < len(SPECIES_GENOME_TEMPLATES):
            for gene, value in SPECIES_GENOME_TEMPLATES[p_type].items():
                if gene in self.dna.alleles:
                    self.dna.alleles[gene] = value

def rebuild_particles(particles, num_types, particles_per_type, simulation_history):
    simulation_history.clear()
    new_particles = []
    global_id_counter = 0
    nacimientos_totales = 0
    muertes_totales = 0
    generacion = 0
    
    for t in range(num_types):
        existing = [p for p in particles if p.type == t and p.alive]
        base_x, base_y = random.uniform(0, WORLD_W), random.uniform(0, WORLD_H)
        
        while len(existing) < particles_per_type:
            if len(existing) > 0:
                ref = random.choice(existing)
                nx, ny = (ref.x + random.uniform(-100, 100)) % WORLD_W, (ref.y + random.uniform(-100, 100)) % WORLD_H
            else:
                nx, ny = (base_x + random.uniform(-100, 100)) % WORLD_W, (base_y + random.uniform(-100, 100)) % WORLD_H
                
            np = Particle(global_id_counter, nx, ny, t)
            global_id_counter += 1
            existing.append(np)
            
        for p in existing[:particles_per_type]:
            # IDs únicos incluso al conservar individuos tras cambiar configuración.
            p.id = global_id_counter
            global_id_counter += 1
            new_particles.append(p)
            
    return new_particles, global_id_counter, nacimientos_totales, muertes_totales, generacion

def resize_matrix(new_size, num_types, matrix):
    new_size = max(2, min(MAX_TIPOS, new_size))
    new_matrix = [[0.0 for _ in range(new_size)] for _ in range(new_size)]
    for i in range(new_size):
        for j in range(new_size):
            if i < num_types and j < num_types and i < len(matrix) and j < len(matrix[i]): new_matrix[i][j] = matrix[i][j]
            else: new_matrix[i][j] = round(random.uniform(-1.0, 1.0), 2)
    return new_size, new_matrix

def world_to_screen(wx, wy, sim_screen_w, sim_screen_h, zoom, pan_x, pan_y):
    sx = (wx - WORLD_W / 2) * zoom + sim_screen_w / 2 + pan_x
    sy = (wy - WORLD_H / 2) * zoom + sim_screen_h / 2 + pan_y
    return sx, sy

def evaluar_estado_sistema(kinetic, entropy, links, temp, pressure):
    if temp > 80 or pressure > 20000: return "COLAPSO TÉRMICO", (239, 68, 68)
    elif temp < 20: return "ESTASIS MOLECULAR", (59, 130, 246)
    elif links > 300 and kinetic < 2.0: return "RED CRISTALINA", (16, 185, 129)
    return "HOMEOSTASIS FLUIDA", (234, 179, 8)
