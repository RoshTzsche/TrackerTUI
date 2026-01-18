from textual.app import App, ComposeResult
from textual.containers import Horizontal, VerticalScroll, Container
from textual.widgets import Header, Footer, Button, Label, Static, TabbedContent, TabPane, Input, ListView, ListItem, Checkbox
from textual.reactive import reactive
from textual.message import Message
import logic
import math

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
        
        return f"[{'#00ff00' if p > 0.8 else '#00afff'}]{bar_str}[/]"

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
