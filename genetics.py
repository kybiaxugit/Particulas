import math
import random
import json
from dataclasses import dataclass
from typing import Dict, Tuple, Optional, Any, List

@dataclass
class GeneSpec:
    """Especificación cuantitativa y científica de un gen dentro del genoma."""
    name: str
    symbol: str
    unit: str
    min_val: float
    max_val: float
    default_val: float
    mutation_rate: float        # Probabilidad de mutación específica del gen
    mutation_step: float        # Desviación estándar / paso relativo de la mutación
    description: str


class GenomeConfig:
    """
    Configuración global editable para las leyes genéticas, mutacionales 
    y ambientales del simulador.
    """
    
    def __init__(self):
        # --- Parámetros de Control Global Editable ---
        self.global_mutation_rate: float = 0.08      # Tasa base global de mutación (8%)
        self.mutation_strength: float = 0.12         # Escala de la variación gaussiana (12%)
        self.crossover_mode: str = "blend"            # 'blend' (BLX-alpha), 'uniform', 'single_point'
        self.enable_epigenetics: bool = True          # Expresión fenotípica adaptativa según entorno
        self.enable_telomeres: bool = True            # Senescencia celular y límite de Hayflick
        
        # --- Catálogo Científico de Genes ---
        self.gene_specs: Dict[str, GeneSpec] = {
            "metabolic_efficiency": GeneSpec(
                name="Eficiencia Metabólica", symbol="η_met", unit="adimensional",
                min_val=0.2, max_val=2.5, default_val=1.0,
                mutation_rate=0.05, mutation_step=0.1,
                description="Tasa de conversión energética e intercambio térmico con el medio."
            ),
            "thermal_min": GeneSpec(
                name="Tolerancia Térmica Mínima", symbol="T_min", unit="°C",
                min_val=-20.0, max_val=40.0, default_val=15.0,
                mutation_rate=0.06, mutation_step=2.0,
                description="Temperatura inferior crítica antes de la paralización o lisis."
            ),
            "thermal_max": GeneSpec(
                name="Tolerancia Térmica Máxima", symbol="T_max", unit="°C",
                min_val=40.0, max_val=120.0, default_val=80.0,
                mutation_rate=0.06, mutation_step=2.0,
                description="Temperatura superior límite antes de la desnaturalización celular."
            ),
            "telomere_length": GeneSpec(
                name="Longitud Telomérica Inicial", symbol="L_tel", unit="pb",
                min_val=100.0, max_val=5000.0, default_val=1500.0,
                mutation_rate=0.04, mutation_step=150.0,
                description="Reserva de divisiones celulares máximas (Esperanza de vida base)."
            ),
            "epigenetic_plasticity": GeneSpec(
                name="Plasticidad Fenotípica", symbol="ε_epi", unit="adimensional",
                min_val=0.0, max_val=1.0, default_val=0.25,
                mutation_rate=0.05, mutation_step=0.05,
                description="Capacidad de ajustar la expresión génica ante estrés ambiental."
            ),
            "drag_coefficient": GeneSpec(
                name="Coeficiente de Arrastre Hidrodinámico", symbol="C_d", unit="adimensional",
                min_val=0.1, max_val=2.0, default_val=0.85,
                mutation_rate=0.07, mutation_step=0.08,
                description="Resistencia viscosa al desplazamiento dinámico."
            ),
            "sensory_radius": GeneSpec(
                name="Alcance Sensorial / Quimiotaxis", symbol="R_sens", unit="μm",
                min_val=10.0, max_val=250.0, default_val=75.0,
                mutation_rate=0.08, mutation_step=5.0,
                description="Radio de detección y alcance de interacciones de campo."
            ),
            "affinity_modifier": GeneSpec(
                name="Modificador de Afinidad Electrostática", symbol="α_aff", unit="adimensional",
                min_val=-1.5, max_val=1.5, default_val=0.0,
                mutation_rate=0.10, mutation_step=0.15,
                description="Sesgo genético que escala los valores de la matriz de atracción/repulsión."
            ),
            "cellular_mass": GeneSpec(
                name="Masa y Inercia Celular", symbol="m_cell", unit="pg",
                min_val=0.5, max_val=10.0, default_val=1.0,
                mutation_rate=0.05, mutation_step=0.2,
                description="Inercia cinemática ante las fuerzas aplicadas por otras partículas."
            ),
            "fertility_threshold": GeneSpec(
                name="Umbral Energético Reproductivo", symbol="E_rep", unit="J",
                min_val=20.0, max_val=500.0, default_val=100.0,
                mutation_rate=0.05, mutation_step=10.0,
                description="Gasto energético mínimo necesario para activar la citocinesis o mitosis."
            ),
            "motility": GeneSpec(
                name="Motilidad", symbol="v_rel", unit="adimensional",
                min_val=0.25, max_val=2.0, default_val=1.0,
                mutation_rate=0.07, mutation_step=0.12,
                description="Modula la velocidad locomotora máxima de la célula."
            ),
            "stress_resistance": GeneSpec(
                name="Resistencia al estrés", symbol="R_est", unit="adimensional",
                min_val=0.1, max_val=2.0, default_val=1.0,
                mutation_rate=0.06, mutation_step=0.1,
                description="Reduce la probabilidad de muerte bajo estrés térmico."
            ),
            "fecundity": GeneSpec(
                name="Fecundidad", symbol="f_rep", unit="adimensional",
                min_val=0.1, max_val=2.0, default_val=1.0,
                mutation_rate=0.06, mutation_step=0.1,
                description="Modula la probabilidad de reproducción si se cumplen las condiciones."
            )
        }

    def update_gene_bounds(self, gene_key: str, min_val: float, max_val: float, default_val: float, mutation_rate: float):
        """Permite modificar dinámicamente los parámetros de un gen específico."""
        if gene_key in self.gene_specs:
            spec = self.gene_specs[gene_key]
            spec.min_val = min_val
            spec.max_val = max_val
            spec.default_val = max(min_val, min(max_val, default_val))
            spec.mutation_rate = max(0.0, min(1.0, mutation_rate))


# Configuración global singleton por defecto
DEFAULT_GENOME_CONFIG = GenomeConfig()


class ParticleDNA:
    """
    Representa el genoma de una partícula con herencia, expresión fenotípica,
    modificación epigenética, senescencia y croma RGB.
    """

    def __init__(
        self,
        color_rgb: Optional[Tuple[int, int, int]] = None,
        alleles: Optional[Dict[str, float]] = None,
        config: Optional[GenomeConfig] = None
    ):
        self.config = config or DEFAULT_GENOME_CONFIG
        
        # 1. Cromóforo (Pigmentación hereditable en espectro RGB)
        self.color_rgb: List[int] = list(color_rgb) if color_rgb else [200, 200, 200]
        
        # 2. Genotipo (Alelos continuos para rasgos cuantificables)
        self.alleles: Dict[str, float] = {}
        if alleles:
            for key, val in alleles.items():
                if key in self.config.gene_specs:
                    spec = self.config.gene_specs[key]
                    self.alleles[key] = max(spec.min_val, min(spec.max_val, float(val)))
        else:
            # Inicialización aleatoria gaussiana sobre los valores por defecto
            for key, spec in self.config.gene_specs.items():
                delta = random.gauss(0, spec.mutation_step * 0.5)
                val = spec.default_val + delta
                self.alleles[key] = max(spec.min_val, min(spec.max_val, val))

        # 3. Marcadores Epigenéticos (Factores ambientales de regulación)
        self.epigenetic_tags: Dict[str, float] = {key: 0.0 for key in self.config.gene_specs}
        
        # 4. Contador de senescencia telomérica
        self.current_telomeres: float = self.alleles.get("telomere_length", 1500.0)

    # -------------------------------------------------------------------------
    # EXPRESIÓN FENOTÍPICA
    # -------------------------------------------------------------------------
    def get_phenotype(self, key: str, env_temp: float = 50.0) -> float:
        """
        Calcula el valor expresado del gen considerando:
        Genotipo base + Regulación Epigenética + Estrés Térmico Ambiental.
        """
        if key not in self.alleles:
            return 1.0
        
        base_val = self.alleles[key]
        
        if not self.config.enable_epigenetics:
            return base_val

        plasticity = self.alleles.get("epigenetic_plasticity", 0.25)
        epi_tag = self.epigenetic_tags.get(key, 0.0)
        
        # Evaluación de estrés térmico
        t_min = self.alleles.get("thermal_min", 15.0)
        t_max = self.alleles.get("thermal_max", 80.0)
        
        thermal_stress = 0.0
        if env_temp < t_min:
            thermal_stress = (t_min - env_temp) / 20.0
        elif env_temp > t_max:
            thermal_stress = (env_temp - t_max) / 20.0
            
        expressed_val = base_val * (1.0 + (epi_tag + thermal_stress * 0.05) * plasticity)
        
        spec = self.config.gene_specs.get(key)
        if spec:
            expressed_val = max(spec.min_val, min(spec.max_val, expressed_val))
            
        return expressed_val

    # -------------------------------------------------------------------------
    # SENESCENCIA Y ADAPTACIÓN
    # -------------------------------------------------------------------------
    def degrade_telomeres(self, rate: float = 1.0) -> bool:
        """Aplica la acortación telomérica. Devuelve True si alcanza la senescencia crítica."""
        if not self.config.enable_telomeres:
            return False
            
        metabolic_factor = self.get_phenotype("metabolic_efficiency")
        decay = rate * (1.2 - (metabolic_factor * 0.2))
        self.current_telomeres -= max(0.05, decay)
        return self.current_telomeres <= 0.0

    def adapt_epigenetics(self, env_stress: float):
        """Ajusta paulatinamente los marcadores epigenéticos ante condiciones extremas."""
        if not self.config.enable_epigenetics:
            return
            
        plasticity = self.alleles.get("epigenetic_plasticity", 0.25)
        for key in self.epigenetic_tags:
            target = math.tanh(env_stress) * plasticity
            self.epigenetic_tags[key] += (target - self.epigenetic_tags[key]) * 0.02

    # -------------------------------------------------------------------------
    # REPRODUCCIÓN (ASEXUAL Y SEXUAL)
    # -------------------------------------------------------------------------
    def reproduce_asexual(self, mutation_multiplier: float = 1.0) -> 'ParticleDNA':
        """Mitosis / Replicación asexual con tasa de error en copia de ADN."""
        child_dna = ParticleDNA(
            color_rgb=tuple(self.color_rgb),
            alleles=dict(self.alleles),
            config=self.config
        )
        child_dna.mutate(mutation_multiplier=mutation_multiplier)
        return child_dna

    @classmethod
    def crossover(
        cls,
        parent1: 'ParticleDNA',
        parent2: 'ParticleDNA',
        config: Optional[GenomeConfig] = None,
        mutation_multiplier: float = 1.0
    ) -> 'ParticleDNA':
        """Meiosis sexual con entrecruzamiento de alelos cromosómicos y mezcla de pigmentos."""
        cfg = config or parent1.config or DEFAULT_GENOME_CONFIG
        mode = cfg.crossover_mode
        
        # 1. Mezcla de Pigmentación
        child_rgb = [0, 0, 0]
        for c in range(3):
            p1_c, p2_c = parent1.color_rgb[c], parent2.color_rgb[c]
            if mode == "blend":
                alpha = random.uniform(-0.1, 1.1)
                val = p1_c + alpha * (p2_c - p1_c)
            else:
                val = p1_c if random.random() < 0.5 else p2_c
            child_rgb[c] = int(max(0, min(255, val)))

        # 2. Recombinación de Alelos
        child_alleles: Dict[str, float] = {}
        for key, spec in cfg.gene_specs.items():
            v1 = parent1.alleles.get(key, spec.default_val)
            v2 = parent2.alleles.get(key, spec.default_val)
            
            if mode == "blend":
                alpha = random.uniform(-0.15, 1.15)
                child_val = v1 + alpha * (v2 - v1)
            elif mode == "single_point":
                child_val = v1 if random.random() < 0.5 else v2
            else:
                w = random.uniform(0.0, 1.0)
                child_val = v1 * w + v2 * (1.0 - w)
                
            child_alleles[key] = max(spec.min_val, min(spec.max_val, child_val))

        child = cls(color_rgb=tuple(child_rgb), alleles=child_alleles, config=cfg)
        child.mutate(mutation_multiplier=mutation_multiplier)
        return child

    # -------------------------------------------------------------------------
    # OPERADOR DE MUTACIÓN CIENTÍFICA
    # -------------------------------------------------------------------------
    def mutate(self, mutation_multiplier: float = 1.0):
        """Aplica mutaciones estocásticas gaussianas en alelos y pigmentación."""
        rate = min(1.0, max(0.0, self.config.global_mutation_rate * mutation_multiplier))
        strength = self.config.mutation_strength
        
        # La tasa global representa la probabilidad base; cada locus la pondera
        # respecto al valor de referencia (5 %).
        for key, spec in self.config.gene_specs.items():
            locus_rate = min(1.0, rate * (spec.mutation_rate / 0.05))
            if random.random() < locus_rate:
                sigma = spec.mutation_step * max(0.0, strength)
                delta = random.gauss(0, sigma)
                self.alleles[key] = max(spec.min_val, min(spec.max_val, self.alleles[key] + delta))

        # Mutación de color
        if random.random() < (rate * 0.7):
            for i in range(3):
                if random.random() < 0.5:
                    shift = int(random.gauss(0, 12 * strength))
                    self.color_rgb[i] = max(0, min(255, self.color_rgb[i] + shift))

    # -------------------------------------------------------------------------
    # SERIALIZACIÓN Y EDICIÓN
    # -------------------------------------------------------------------------
    def get_hex_color(self) -> str:
        """Devuelve el color cromático en formato hexadecimal (#RRGGBB)."""
        return f"#{self.color_rgb[0]:02x}{self.color_rgb[1]:02x}{self.color_rgb[2]:02x}"

    def to_dict(self) -> Dict[str, Any]:
        """Exporta el ADN a un diccionario editable."""
        return {
            "color_rgb": self.color_rgb,
            "alleles": self.alleles,
            "epigenetic_tags": self.epigenetic_tags,
            "telomeres": self.current_telomeres
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], config: Optional[GenomeConfig] = None) -> 'ParticleDNA':
        """Importa el ADN desde un diccionario estructurado."""
        dna = cls(
            color_rgb=tuple(data.get("color_rgb", [200, 200, 200])),
            alleles=data.get("alleles", {}),
            config=config
        )
        if "epigenetic_tags" in data:
            dna.epigenetic_tags = data["epigenetic_tags"]
        if "telomeres" in data:
            dna.current_telomeres = data["telomeres"]
        return dna

    def to_json(self) -> str:
        """Serializa la información genética a JSON."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str, config: Optional[GenomeConfig] = None) -> 'ParticleDNA':
        """Deserializa y reconstruye un ADN desde una cadena JSON."""
        return cls.from_dict(json.loads(json_str), config=config)
