from textual.app import App, ComposeResult
from textual.containers import Horizontal, VerticalScroll, Container, Grid
from textual.widgets import Header, Footer, Button, Label, Static, TabbedContent, TabPane, Input, ListView, ListItem, Checkbox
from textual.reactive import reactive
from textual.message import Message
from textual.screen import Screen
import logic

# --- COMPONENTES VISUALES ---
MY_ASCII_ART = r"""
[][][]][][][]]{[]
[]
[]
[
][
][
]
[]
[]
[
]
[
]

[
]
[
]
[
]
[]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]
"""
SIDEBAR_ART = r"""
   .   .
    . .
  .  .  .
   .   .
  _______
 /_  _   \
|  \/  o  |
|         |
 \_______/ 
   ROSH
"""
class BtopBar(Static):
    """Barra de progreso reactiva."""
    progress = reactive(0.0)
    BARS = ["⠀", "⡀", "⣀", "⣄", "⣤", "⣦", "⣶", "⣷", "⣿"]
    def watch_progress(self, val):
        self.remove_class("p-low", "p-med", "p-high")
        if val < 50: self.add_class("p-low")
        elif val < 80: self.add_class("p-med")
        else: self.add_class("p-high")

    def render(self):
        width = self.content_size.width or 20
        if width <= 0: return ""
        p = min(max(self.progress / 100.0, 0), 1)
        total = width
        filled = int(total * p)
        remainder = (total * p) - filled
        bar = "⣿" * filled
        if filled < total:
            idx = int(remainder * (len(self.BARS) - 1))
            bar += self.BARS[idx]
        return bar.ljust(total, " ")

class Sidebar(Static):
    """Panel lateral de estadísticas."""
    def compose(self) -> ComposeResult:
        yield Label("::::::: DASHBOARD :::::::", classes="sidebar-title")
        yield Label("Meta Semanal:", classes="stat-label")
        self.lbl_meta = Label("0.0", classes="stat-value")
        yield self.lbl_meta       
        yield Label("Total Horas:", classes="stat-label")
        self.lbl_total = Label("0.0", classes="stat-value")
        yield self.lbl_total
        yield Label("Progreso Global:", classes="stat-label")
        self.bar_global = BtopBar(classes="btop-bar-global")
        yield self.bar_global
        
        #ASCII art
        with Container(classes="sidebar-footer"):
            yield Label(SIDEBAR_ART, classes="ascii-art") 
        # BOTONES DE CONTROL
        yield Button("Cambiar Vista ⧉", id="btn_view_toggle", variant="primary")
        yield Button("Reiniciar Semana", id="btn_reset", variant="error")

    def actualizar(self, stats):
        self.lbl_total.update(f"{stats['total_horas']:.1f} h")
        self.lbl_meta.update(f"{stats['total_meta']:.1f} h")
        self.bar_global.progress = stats['progreso_general']


class MateriaWidget(Static):
    horas = reactive(0.0)

    class EliminarSolicitud(Message):
        """Mensaje para pedir al padre que me borre."""
        def __init__(self, materia_obj):
            self.materia_obj = materia_obj
            super().__init__()

    class Cambio(Message): pass

    def __init__(self, materia_obj):
        super().__init__()
        self.materia = materia_obj
        self.horas = materia_obj.horas_acumuladas

    def compose(self) -> ComposeResult:
        # Layout: Nombre | Bar | - | Stats | + | Trash
        yield Label(f"{self.materia.nombre[:15]:<15}", classes="nombre-materia")
        
        self.progress_bar = BtopBar(classes="barra-materia")
        self.progress_bar.progress = self.materia.obtener_progreso()
        yield self.progress_bar
        
        # Botón Restar
        yield Button("-", id="btn_sub", classes="btn-minus")
        
        self.lbl_stats = Label(f"{self.horas:.1f}/{self.materia.meta_semanal}h", classes="stats-materia")
        yield self.lbl_stats
        
        # Botón Sumar
        yield Button("+", id="btn_add", classes="btn-small")
        
        # Botón Eliminar
        yield Button("X", id="btn_del", classes="btn-trash")

    def watch_horas(self, val):
        self.materia.horas_acumuladas = val
        if hasattr(self, 'progress_bar'):
            self.progress_bar.progress = self.materia.obtener_progreso()
            self.lbl_stats.update(f"{val:.1f}/{self.materia.meta_semanal}h")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_add":
            self.materia.registrar_sesion(1.0) 
            self.post_message(self.Cambio())
        elif event.button.id == "btn_sub":
            self.materia.restar_sesion(1.0) 
            self.horas = self.materia.horas_acumuladas
            self.post_message(self.Cambio())
        elif event.button.id == "btn_del":
            # Enviar mensaje al padre (TrackerPanel) para gestionar borrado
            self.post_message(self.EliminarSolicitud(self.materia))

class TrackerPanel(Static):
    """Panel para la lista de materias con creación dinámica."""
    
    def compose(self) -> ComposeResult:
        yield Label(":: TRACKER ::", classes="sidebar-title")
        
        with VerticalScroll():   
            yield Container(id="lista_container")
            with Container(id="panel_crear_materia"):
                yield Input(placeholder="Nueva Materia...", id="inp_nueva_materia")
                yield Input(placeholder="Meta(h)", id="inp_nueva_meta", type="number")
                yield Button("Añadir", id="btn_crear_materia")
       
    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn_crear_materia":
            self.crear_materia_ui()

    def on_input_submitted(self, event: Input.Submitted):
        # Permitir crear dando Enter en los inputs
        self.crear_materia_ui()
    def crear_materia_ui(self):
        nombre = self.query_one("#inp_nueva_materia", Input).value.strip()
        meta_str = self.query_one("#inp_nueva_meta", Input).value.strip()
    
        if nombre and meta_str:
            try:
                meta = float(meta_str)
            # 1. Llamada a la lógica persistente
                exito, resultado = logic.crear_materia(nombre, meta)
            
                if exito:
                # 2. Sincronizar TODA la app (Tabs y Dashboard)
                    self.app.cargar_datos_y_refrescar() 
                
                # 3. Limpiar inputs y notificar
                    self.query_one("#inp_nueva_materia", Input).value = ""
                    self.query_one("#inp_nueva_meta", Input).value = ""
                    self.app.notify(f"Materia '{nombre}' añadida")
                else:
                    self.app.notify(resultado, severity="error")
                
            except ValueError:
                self.app.notify("La meta debe ser un número", severity="error")

        # Manejar solicitud de borrado que viene de un hijo (MateriaWidget)
    def on_materia_widget_eliminar_solicitud(self, message: MateriaWidget.EliminarSolicitud):
        materia_a_borrar = message.materia_obj
        
        # Definir qué hacer si el usuario dice SI
        def check_borrado(confirmado: bool):
            if confirmado:
                self.app.materias.remove(materia_a_borrar)
                self.app.cargar_datos_y_refrescar() # Refresca todos los paneles
                self.app.guardar_todo()
                self.app.notify(f"Eliminada: {materia_a_borrar.nombre}")

        # Mostrar pantalla de confirmación
        self.app.push_screen(ConfirmScreen(), check_borrado)

    def recargar_materias(self, materias):
        container = self.query_one("#lista_container")
        container.remove_children() 
        for m in materias:
            container.mount(MateriaWidget(m))

class ToDoWidget(Static):
    def compose(self) -> ComposeResult:
        yield Label(":: TAREAS ::", classes="sidebar-title")
        yield ListView(id="list_tasks")
        yield Input(placeholder="Nueva tarea... (Enter)", id="inp_task")

    def on_input_submitted(self, event: Input.Submitted):
        if not event.value.strip(): return
        self.agregar_item(event.value, False)
        event.input.value = "" 
        self.post_message(self.Cambio())

    def agregar_item(self, texto, hecho):
        lv = self.query_one("#list_tasks", ListView)
        cb = Checkbox(texto, value=hecho, classes="task-cb")
        btn = Button("✖", variant="error", classes="btn-delete")
        lv.append(ListItem(Horizontal(cb, btn, classes="task-container")))

    def on_button_pressed(self, event: Button.Pressed):
        if "btn-delete" in event.button.classes:
            node = event.button
            while node.parent:
                node = node.parent
                if isinstance(node, ListItem):
                    node.remove()
                    self.post_message(self.Cambio())
                    break

    def on_checkbox_changed(self, event):
        self.post_message(self.Cambio())

    def recargar_todos(self, todos):
        # Limpiar y reconstruir
        try:
            lv = self.query_one("#list_tasks", ListView)
            lv.remove_children()
            for t in todos:
                if isinstance(t, dict):
                    self.agregar_item(t.get('text', ''), t.get('done', False))
        except: pass

    class Cambio(Message): pass

class PomodoroWidget(Static):
    def compose(self) -> ComposeResult:
        self.engine = logic.motor_ultradiano_global
        self.timer_active = False 

        yield Label(":::::: FLUJO ULTRADIANO ::::::", classes="sidebar-title")
        
        # 1. Contenedor del Reloj "Digital"
        with Container(classes="clock-panel"):
            yield Label("IDLE", id="lbl_status")
            yield Label("90:00", id="lbl_time")
        
        self.progress_bar = BtopBar(classes="barra-materia")
        yield self.progress_bar
        
        # 2. Grid para los botones (Mejor que Horizontal para alineación)
        with Grid(classes="timer-grid"):
            yield Button("WORK (90m)", id="btn_start_90", variant="success", classes="btn-pomo")
            yield Button("PAUSE", id="btn_pause", variant="primary", classes="btn-pomo")
            yield Button("BREAK", id="btn_break", variant="warning", classes="btn-pomo")


    def on_mount(self):
        self.set_interval(1.0, self.update_timer)

    def update_timer(self):
        # Sincronizamos con el motor global
        terminado = False
        if self.timer_active:
            terminado = self.engine.tick()

        # Actualizar UI siempre (por si otro widget movió el motor)
        try:
            self.query_one("#lbl_time").update(self.engine.formatear_tiempo())
            self.query_one("#lbl_status").update(self.engine.state)
            self.progress_bar.progress = self.engine.obtener_progreso()
            
            lbl_time = self.query_one("#lbl_time")
            lbl_time.remove_class("time-work", "time-break")
            if self.engine.state == "WORK": lbl_time.add_class("time-work")
            elif self.engine.state == "BREAK": lbl_time.add_class("time-break")

            if terminado:
                self.timer_active = False
                self.notify("¡Ciclo Terminado!", severity="information")
        except: pass

    def on_button_pressed(self, event):
        btn_id = event.button.id
        if btn_id == "btn_start_90":
            self.engine.iniciar_trabajo(90)
            self.timer_active = True
        elif btn_id == "btn_pause":
            self.timer_active = not self.timer_active
        elif btn_id == "btn_break":
            self.engine.iniciar_descanso()
            self.timer_active = True
        elif btn_id == "btn_reset":
            self.timer_active = False
            self.engine.iniciar_trabajo(90)
            self.engine.state = "IDLE"

class ConfirmScreen(Screen):
    """Modal para confirmar borrado."""
    def compose(self) -> ComposeResult:
        yield Grid(
            Label("¿Estás seguro de ELIMINAR esta materia?\nEsta acción no se puede deshacer.", id="question"),
            Button("Cancelar", variant="primary", id="btn_cancel_delete"),
            Button("ELIMINAR", variant="error", id="btn_confirm_delete"),
            id="dialog"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_confirm_delete":
            self.dismiss(True) # Retorna True si confirmó
        else:
            self.dismiss(False)

# --- VISTA DASHBOARD (REJILLA) ---
class DashboardView(Container):
    """Vista 'God Mode' con todo visible a la vez."""
    def compose(self) -> ComposeResult:
        # Columna Izquierda: Tracker
        yield TrackerPanel(id="dash_tracker")
        
        # Columna Derecha: Pomodoro (Arriba) y ToDo (Abajo)
        with VerticalScroll(id="dash_right_col"):
            yield PomodoroWidget(id="dash_pomodoro")
            yield ToDoWidget(id="dash_todo")
            with Container(classes="ascii-dashboard-box"):
                yield Label(MY_ASCII_ART, classes="ascii-art-text")
""" 
  yield ToDoWidget(id="dash_todo")
        # Columna Derecha: Pomodoro (Arriba) y ToDo (Abajo)
        with VerticalScroll(id="dash_right_col"):
            yield PomodoroWidget(id="dash_pomodoro")
            yield TrackerPanel(id="dash_tracker")
            yield Label(MY_ASCII_ART, classes="ascii-art-text")
"""
# --- APP PRINCIPAL ---
class StudyApp(App):
    CSS_PATH = ["/home/ateniense/.cache/wal/textual.tcss", "estilo.css"]
    BINDINGS = [("q", "quit", "Salir")]

    # Variable reactiva para controlar qué vista se muestra
    show_dashboard = reactive(True)

    def compose(self) -> ComposeResult:
        with Horizontal(id="main_layout"):
            yield Sidebar()
            
            # --- VISTA 1: TABS CLÁSICAS ---
            with TabbedContent(initial="tab_materias", id="view_tabs"):
                with TabPane("Tracker", id="tab_materias"):
                    yield TrackerPanel(id="tab_tracker_panel")
                with TabPane("To-Do List", id="tab_todo"):
                    yield ToDoWidget(id="tab_todo_widget")
                with TabPane("Ultradian Timer", id="tab_pomodoro"):
                    yield PomodoroWidget(id="tab_pomodoro_widget")
            
            # --- VISTA 2: DASHBOARD (Oculto por defecto) ---
            yield DashboardView(id="view_dashboard")
                    

    def on_mount(self):
        self.cargar_datos_y_refrescar()

    def watch_show_dashboard(self, show: bool):
        """Alternar visibilidad CSS basado en la variable reactiva."""
        tabs = self.query_one("#view_tabs")
        dash = self.query_one("#view_dashboard")
        
        if show:
            tabs.display = False
            dash.display = True
            # Forzar refresco al mostrar dashboard para sincronizar datos
            self.cargar_datos_y_refrescar()
        else:
            tabs.display = True
            dash.display = False
            self.cargar_datos_y_refrescar()

    def cargar_datos_y_refrescar(self):
        """Carga datos de disco y los inyecta en TODOS los widgets."""
        datos = logic.cargar_datos_globales()
        self.materias = datos["materias"]
        self.todos = datos["todos"]

        # Refrescar Paneles de Materias (hay dos: uno en tabs, uno en dash)
        for panel in self.query(TrackerPanel):
            panel.recargar_materias(self.materias)

        # Refrescar ToDos (hay dos)
        for widget in self.query(ToDoWidget):
            widget.recargar_todos(self.todos)

        # Actualizar Sidebar
        self.actualizar_sidebar()

    def actualizar_sidebar(self):
        stats = logic.obtener_estadisticas_globales(self.materias)
        self.query_one(Sidebar).actualizar(stats)

    def guardar_todo(self):
        # Recolectar ToDos del widget visible actual
        visible_todo_widget = None
        if self.show_dashboard:
            visible_todo_widget = self.query_one("#dash_todo", ToDoWidget)
        else:
            visible_todo_widget = self.query_one("#tab_todo_widget", ToDoWidget)
            
        if visible_todo_widget:
            tasks_ui = []
            try:
                # Extraemos datos manualmente del widget visible
                list_view = visible_todo_widget.query_one("ListView")
                for item in list_view.children:
                    # Buscamos el checkbox dentro del Horizontal
                    cb = item.query_one(Checkbox)
                    tasks_ui.append({"text": str(cb.label), "done": cb.value})
                self.todos = tasks_ui
            except: pass

        logic.guardar_datos_globales(self.materias, self.todos)
        
        # IMPORTANTE: Sincronizar el otro widget que no se ve
        self.cargar_datos_y_refrescar()

    # --- MANEJO DE EVENTOS ---
    def on_materia_widget_cambio(self, msg):
        self.guardar_todo()

    def on_to_do_widget_cambio(self, msg):
        self.guardar_todo()

    def on_button_pressed(self, event):
        bid = event.button.id
        if bid == "btn_reset":
            logic.reiniciar_semana(self.materias)
            self.guardar_todo()
            self.notify("Semana Reiniciada")
        elif bid == "btn_view_toggle":
            # Alternar vista
            self.show_dashboard = not self.show_dashboard

if __name__ == "__main__":
    app = StudyApp()
    app.run()
