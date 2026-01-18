from textual.app import App, ComposeResult
from textual.containers import Horizontal, VerticalScroll, Container
from textual.widgets import Header, Footer, Button, Label, Static, TabbedContent, TabPane, Input, ListView, ListItem, Checkbox
from textual.reactive import reactive
from textual.message import Message
import logic
import math
from logic import GestorUltradiano 

# --- WIDGET PERSONALIZADO: BARRA ESTILO BTOP ---
class BtopBar(Static):
    """Barra de progreso renderizada con bloques Unicode."""
    progress = reactive(0.0)
    
    BARS = [" ", " ", "▂", "▃", "▄", "▅", "▆", "▇", "█"]

    def render(self):
        # 1. Calcular cuántos bloques llenos necesitamos
        width = self.content_size.width or 20
        total_chars = width
        
        # Porcentaje normalizado (0.0 a 1.0)
        p = min(max(self.progress / 100.0, 0), 1)
        
        filled_chars = int(total_chars * p)
        remainder = (total_chars * p) - filled_chars
        
        # Construir la barra
        bar_str = "█" * filled_chars
        
        # Añadir el carácter parcial (el detalle fino)
        if filled_chars < total_chars:
            idx = int(remainder * (len(self.BARS) - 1))
            bar_str += self.BARS[idx]
            
        # Rellenar con vacío el resto
        bar_str = bar_str.ljust(total_chars, " ")
        
        return bar_str 

class Sidebar(Static):
    """Panel lateral de estadísticas."""
    def compose(self) -> ComposeResult:
        yield Label(":: DASHBOARD ::", classes="sidebar-title")
        yield Label("Meta Semanal:", classes="stat-label")
        self.lbl_meta = Label("0.0", classes="stat-value")
        yield self.lbl_meta       
        yield Label("Total Horas:", classes="stat-label")
        self.lbl_total = Label("0.0", classes="stat-value")
        yield self.lbl_total
        yield Label("Progreso Global:", classes="stat-label")
        self.bar_global = BtopBar(classes="btop-bar-global") # Usamos nuestra barra
        yield self.bar_global
        yield Button("Reiniciar Semana", id="btn_reset", variant="error")

    def actualizar(self, stats):
        self.lbl_total.update(f"{stats['total_horas']:.1f} h")
        self.lbl_meta.update(f"{stats['total_meta']:.1f} h")
        self.bar_global.progress = stats['progreso_general']

class MateriaWidget(Static):
    """Fila individual por materia."""
    horas = reactive(0.0)

    def __init__(self, materia_obj):
        super().__init__()
        self.materia = materia_obj
        self.horas = materia_obj.horas_acumuladas

    def compose(self) -> ComposeResult:
        # Layout horizontal para nombre, barra y botón
        yield Label(f"{self.materia.nombre[:15]:<15}", classes="nombre-materia")
        
        # Barra Btop personalizada
        self.progress_bar = BtopBar(classes="barra-materia")
        self.progress_bar.progress = self.materia.obtener_progreso()
        yield self.progress_bar
        
        self.lbl_stats = Label(f"{self.horas:.1f}/{self.materia.meta_semanal}h", classes="stats-materia")
        yield self.lbl_stats
        
        yield Button("+", id="btn_add", classes="btn-small")

    def watch_horas(self, val):
        self.materia.horas_acumuladas = val
        if hasattr(self, 'progress_bar'):
            self.progress_bar.progress = self.materia.obtener_progreso()
            self.lbl_stats.update(f"{val:.1f}/{self.materia.meta_semanal}h")

    class Cambio(Message): pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_add":
            self.horas += 1.0
            self.post_message(self.Cambio())

class ToDoWidget(Static):
    """Gestor de tareas pendientes."""
    def compose(self) -> ComposeResult:
        yield Label(":: TAREAS PENDIENTES ::", classes="sidebar-title")
        yield ListView(id="list_tasks")
        yield Input(placeholder="Nueva tarea... (Enter)", id="inp_task")

    def on_input_submitted(self, event: Input.Submitted):
        if not event.value.strip(): return
        self.agregar_item(event.value, False)
        event.input.value = "" 
        self.post_message(self.Cambio())

    def agregar_item(self, texto, hecho):
        lv = self.query_one("#list_tasks", ListView)
        cb = Checkbox(texto, value=hecho)
        lv.append(ListItem(cb))

    def on_checkbox_changed(self, event):
        self.post_message(self.Cambio())

    class Cambio(Message): pass
# --- WIDGET POMODORO/ULTRADIANO ---
class PomodoroWidget(Static):
    """Interfaz gráfica del timer."""
    
    def compose(self) -> ComposeResult:
        # Instanciamos el motor lógico
        self.engine = GestorUltradiano()
        self.timer_active = False # Controla si el tick corre en la UI

        yield Label(":: FLUJO ULTRADIANO ::", classes="sidebar-title")
        
        # Display del tiempo
        yield Container(
            Label("IDLE", id="lbl_status"),
            Label("90:00", id="lbl_time"),
            classes="timer-container"
        )

        # Barra de progreso (Reusamos tu BtopBar)
        self.progress_bar = BtopBar(classes="barra-materia")
        yield self.progress_bar

        # Controles
        with Horizontal(classes="timer-controls"):
            yield Button("Iniciar (90m)", id="btn_start_90", variant="success")
            yield Button("Pausar/Reanudar", id="btn_pause", variant="primary")
            yield Button("Break Dinámico", id="btn_break", variant="warning")
            yield Button("Reset", id="btn_reset", variant="error")

    def on_mount(self):
        # Creamos un intervalo que se ejecuta cada 1 segundo
        self.set_interval(1.0, self.update_timer)

    def update_timer(self):
        """El corazón del loop."""
        if self.timer_active:
            terminado = self.engine.tick()
            
            # Actualizar UI
            self.query_one("#lbl_time").update(self.engine.formatear_tiempo())
            self.query_one("#lbl_status").update(self.engine.state)
            
            # Actualizar barra
            self.progress_bar.progress = self.engine.obtener_progreso()
            
            # Gestionar cambio de color según estado
            lbl_time = self.query_one("#lbl_time")
            if self.engine.state == "WORK":
                lbl_time.remove_class("time-break")
                lbl_time.add_class("time-work")
            elif self.engine.state == "BREAK":
                lbl_time.remove_class("time-work")
                lbl_time.add_class("time-break")

            if terminado:
                self.timer_active = False
                self.notify("¡Ciclo Terminado!", severity="information")
                if self.engine.state == "WORK":
                    # Auto-iniciar break o esperar? Mejor esperar usuario
                    self.query_one("#lbl_status").update("DONE - TAKE BREAK")

    def on_button_pressed(self, event):
        btn_id = event.button.id
        
        if btn_id == "btn_start_90":
            self.engine.iniciar_trabajo(90)
            self.timer_active = True
            self.query_one("#lbl_status").update("DEEP WORK")
            
        elif btn_id == "btn_pause":
            # Toggle simple
            self.timer_active = not self.timer_active
            status = "PAUSED" if not self.timer_active else self.engine.state
            self.query_one("#lbl_status").update(status)
            
        elif btn_id == "btn_break":
            # Forzar el descanso dinámico basado en lo que hayas trabajado
            self.engine.iniciar_descanso()
            self.timer_active = True
            descanso_min = self.engine.target_seconds // 60
            self.notify(f"Descanso calculado: {descanso_min} min")
            
        elif btn_id == "btn_reset":
            self.timer_active = False
            self.engine.iniciar_trabajo(90) # Reset a estado base
            self.engine.state = "IDLE"
            self.query_one("#lbl_time").update("90:00")
            self.query_one("#lbl_status").update("READY")
            self.progress_bar.progress = 0

class StudyApp(App):
    CSS_PATH = [
        "/home/ateniense/.cache/wal/textual.tcss", 
        "estilo.css"
    ]
    BINDINGS = [("q", "quit", "Salir")]

    def compose(self) -> ComposeResult:
        with Horizontal(id="main_layout"):
            yield Sidebar()
            
            # --- PESTAÑAS PARA ORGANIZACIÓN ---
            with TabbedContent(initial="tab_materias"):
                with TabPane("Tracker", id="tab_materias"):
                    with VerticalScroll(id="lista_container"):
                        pass 
                with TabPane("To-Do List", id="tab_todo"):
                    yield ToDoWidget()

                with TabPane("Ultradian Timer", id="tab_pomodoro"):
                    yield PomodoroWidget()
    def on_mount(self):
        datos = logic.cargar_datos_globales()
        self.materias = datos["materias"]
        self.todos = datos["todos"]

        lista = self.query_one("#lista_container")
        for m in self.materias:
            lista.mount(MateriaWidget(m))

        todo_widget = self.query_one(ToDoWidget)
        for t in self.todos:
            if isinstance(t, dict):
                todo_widget.agregar_item(t.get('text', ''), t.get('done', False))

        self.actualizar_sidebar()

    def actualizar_sidebar(self):
        stats = logic.obtener_estadisticas_globales(self.materias)
        self.query_one(Sidebar).actualizar(stats)

    def guardar_todo(self):
        """Centraliza el guardado."""
        tasks_ui = []
        try:
            list_view = self.query_one("#list_tasks", ListView)
            for item in list_view.children:
                cb = item.query_one(Checkbox)
                tasks_ui.append({"text": str(cb.label), "done": cb.value})
            self.todos = tasks_ui
        except:
            pass # Si el widget no está cargado (pestaña oculta), usamos self.todos de memoria

        logic.guardar_datos_globales(self.materias, self.todos)

    def on_materia_widget_cambio(self, msg):
        self.guardar_todo()
        self.actualizar_sidebar()

    def on_to_do_widget_cambio(self, msg):
        self.guardar_todo()

    def on_button_pressed(self, event):
        if event.button.id == "btn_reset":
            logic.reiniciar_semana(self.materias)
            for widget in self.query(MateriaWidget):
                widget.horas = 0.0
            self.guardar_todo()
            self.actualizar_sidebar()

if __name__ == "__main__":
    app = StudyApp()
    app.run()
