# logic.py
import json
import os

FILE_NAME = "progress.json"

class Materia:
    def __init__(self, nombre, meta_semanal, horas_acumuladas=0.0):
        self.nombre = nombre
        self.meta_semanal = float(meta_semanal)
        self.horas_acumuladas = float(horas_acumuladas)

    def registrar_sesion(self, horas):
        self.horas_acumuladas += horas

    def obtener_progreso(self):
        if self.meta_semanal == 0: return 0
        return (self.horas_acumuladas / self.meta_semanal) * 100

    def to_dict(self):
        return {
            "nombre": self.nombre,
            "meta": self.meta_semanal,
            "horas_acumuladas": self.horas_acumuladas
        }

# --- FUNCIONES DE PERSISTENCIA UNIFICADA ---

def cargar_datos_globales():
    """Carga materias y tareas del archivo JSON de forma segura."""
    if not os.path.exists(FILE_NAME):
        return {"materias": _datos_por_defecto(), "todos": []}

    try:
        with open(FILE_NAME, 'r') as f:
            data = json.load(f)
            
            # Migración: Si el archivo viejo era una lista (solo materias)
            if isinstance(data, list):
                return {
                    "materias": [Materia(d['nombre'], d['meta'], d.get('horas_acumuladas', 0)) for d in data],
                    "todos": []
                }
            
            # Formato nuevo (Diccionario completo)
            raw_materias = data.get("materias", [])
            materias = [Materia(d['nombre'], d['meta'], d.get('horas_acumuladas', 0)) for d in raw_materias]
            todos = data.get("todos", [])
            return {"materias": materias, "todos": todos}
            
    except Exception:
        # Si falla, backup de emergencia con datos default
        return {"materias": _datos_por_defecto(), "todos": []}

def guardar_datos_globales(materias, todos):
    """Guarda el estado completo del sistema."""
    data = {
        "materias": [m.to_dict() for m in materias],
        "todos": todos 
    }
    with open(FILE_NAME, 'w') as f:
        json.dump(data, f, indent=4)

def obtener_estadisticas_globales(materias):
    total_horas = sum(m.horas_acumuladas for m in materias)
    total_meta = sum(m.meta_semanal for m in materias)
    progreso = (total_horas / total_meta * 100) if total_meta > 0 else 0
    return {
        "total_horas": total_horas,
        "total_meta": total_meta,
        "progreso_general": progreso
    }

def reiniciar_semana(materias):
    for m in materias:
        m.horas_acumuladas = 0.0

def _datos_por_defecto():
    raw = [
        ("Analisis matematico", 4), ("ML - SPV", 4), ("Termodinamica quimica", 4),
        ("EDO", 2), ("Python", 2), ("Electronica integrada", 2), 
        ("Probabilidad", 2), ("Lab. Termodinamica", 1), ("Pensamiento H.", 1)
    ]
    return [Materia(n, m) for n, m in raw]
