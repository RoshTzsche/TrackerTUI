# tui_app.py
from textual.app import App, ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Header, Footer, Button, Label, ProgressBar, Static
from textual.reactive import reactive
from textual.message import Message
import logic

# --- COMPONENTES ---
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
        self.bar_global = ProgressBar(total=100, show_eta=False)
        yield self.bar_global
        
        yield Button("Reiniciar", id="btn_reset")

    def actualizar(self, stats):
        self.lbl_total.update(f"{stats['total_horas']:.1f} h")
        self.lbl_meta.update(f"{stats['total_meta']:.1f} h")
        self.bar_global.progress = stats['progreso_general']

class ToDoList(Static): 

    """ Lista de cosas que hacer"""
    def compose(self):
        yield Label("To do list")
        yield Button()
        yield Button()
     

class MateriaWidget(Static):
    """Fila individual por materia."""
    horas = reactive(0.0)

    def __init__(self, materia_obj):
        super().__init__()
        self.materia = materia_obj
        self.horas = materia_obj.horas_acumuladas

    def compose(self) -> ComposeResult:
        yield Label(self.materia.nombre, classes="nombre-materia")
        
        self.progress_bar = ProgressBar(total=100, show_eta=False, id="barraindividual")
        self.progress_bar.progress = self.materia.obtener_progreso()
        yield self.progress_bar
        
        self.lbl_stats = Label(f"{self.horas}h", classes="stats-materia")
        yield self.lbl_stats
        
        yield Button("+1", id="btn_add")

    def watch_horas(self, val):
        self.materia.horas_acumuladas = val
        if hasattr(self, 'progress_bar'):
            self.progress_bar.progress = self.materia.obtener_progreso()
            self.lbl_stats.update(f"{val:.1f} / {self.materia.meta_semanal}h")

    class Cambio(Message): pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_add":
            self.horas += 1.0
            self.post_message(self.Cambio())

class StudyApp(App):
    CSS_PATH = "estilo.css"
    BINDINGS = [("q", "quit", "Salir")]

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main_layout"):
            yield Sidebar()
            with VerticalScroll(id="lista_container"):
                pass 
        yield Footer()

    def on_mount(self):
        self.materias = logic.cargar_datos()
        lista = self.query_one("#lista_container")
        for m in self.materias:
            lista.mount(MateriaWidget(m))
        self.actualizar_sidebar()

    def actualizar_sidebar(self):
        stats = logic.obtener_estadisticas_globales(self.materias)
        self.query_one(Sidebar).actualizar(stats)

    def on_materia_widget_cambio(self, msg):
        logic.guardar_datos(self.materias)
        self.actualizar_sidebar()

    def on_button_pressed(self, event):
        if event.button.id == "btn_reset":
            logic.reiniciar_semana(self.materias)
            logic.guardar_datos(self.materias)
            
            # Reiniciar UI
            for widget in self.query(MateriaWidget):
                widget.horas = 0.0
            self.actualizar_sidebar()
            self.notify("SEMANA REINICIADA")

if __name__ == "__main__":
    app = StudyApp()
    app.run()
