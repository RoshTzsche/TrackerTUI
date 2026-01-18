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

# --- NUEVA CLASE: GESTOR ULTRADIANO (Aquí estaba el error) ---
class GestorUltradiano:
    """
    Motor lógico para ciclos de trabajo basados en Ritmos Ultradianos.
    Ratio de descanso: ~16.6% del tiempo trabajado (90m -> 15m).
    """
    WORK_MIN = 90
    WORK_MAX = 112
    
    def __init__(self):
        self.state = "IDLE" # IDLE, WORK, BREAK
        self.target_seconds = 90 * 60 # Default 90 min
        self.current_seconds = self.target_seconds
        self.elapsed_work = 0 # Tiempo real trabajado (para calcular break dinámico)
    
    def iniciar_trabajo(self, minutos=90):
        self.state = "WORK"
        self.target_seconds = minutos * 60
        self.current_seconds = self.target_seconds
        self.elapsed_work = 0
        
    def tick(self):
        """Avanza el reloj un segundo. Retorna True si el ciclo terminó."""
        if self.state == "IDLE": return False
        
        if self.current_seconds > 0:
            self.current_seconds -= 1
            if self.state == "WORK":
                self.elapsed_work += 1
            return False
        else:
            return True # Tiempo agotado

    def calcular_descanso_dinamico(self):
        """
        Calcula el descanso basado en el esfuerzo real.
        Regla: 1 minuto de descanso por cada 6 minutos de trabajo.
        Ej: 90m -> 15m | 45m -> 7.5m
        """
        segundos_descanso = int(self.elapsed_work / 6)
        # Mínimo 2 minutos para que valga la pena
        return max(segundos_descanso, 120)

    def iniciar_descanso(self):
        self.state = "BREAK"
        self.target_seconds = self.calcular_descanso_dinamico()
        self.current_seconds = self.target_seconds

    def formatear_tiempo(self):
        mins, secs = divmod(self.current_seconds, 60)
        return f"{mins:02d}:{secs:02d}"
    
    def obtener_progreso(self):
        if self.target_seconds == 0: return 0
        # Invertimos para que la barra se llene o vacíe según prefieras
        total = self.target_seconds
        restante = self.current_seconds
        return ((total - restante) / total) * 100

# --- FUNCIONES DE PERSISTENCIA ---

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
