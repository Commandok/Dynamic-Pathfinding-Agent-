import pygame
import heapq
import time
import math
import random
import sys
from pygame import gfxdraw

# Initialize Pygame
pygame.init()
pygame.font.init()

#ADJUSTED CONSTANTS FOR STANDARD SCREENS 
# Works perfectly on both 1366x768 and 1920x1080 screens
WIDTH, HEIGHT = 1200, 700  #  for standard screens
GRID_WIDTH = 850         #  grid width
TOOLBAR_WIDTH = 350      # Wide enough for all controls
DEFAULT_GRID_SIZE = 25   # Default grid size (adjustable)
FPS = 60

# Professional Color Palette 
BG = (248, 248, 248)
GRID_BG = (252, 252, 252)
TOOLBAR_BG = (45, 50, 60)
NODE_COLORS = {
    "empty": (255, 255, 255),
    "start": (255, 165, 0),
    "goal": (180, 100, 220),
    "barrier": (80, 80, 80),
    "open": (100, 200, 255),
    "closed": (255, 120, 120),
    "path": (120, 220, 120),
    "grid": (230, 230, 230)
}
BUTTON_COLORS = {
    "normal": (70, 120, 180),
    "active": (100, 160, 220),
    "hover": (120, 180, 240),
    "stop": (220, 80, 80),
    "text": (255, 255, 255)
}
SLIDER_COLORS = {
    "bg": (60, 65, 75),
    "knob": (100, 160, 220),
    "text": (240, 240, 240)
}
TEXT_COLOR = (240, 240, 240)
BORDER_COLOR = (200, 200, 200)
HIGHLIGHT_COLOR = (255, 255, 255, 50)

# State management
class State:
    def __init__(self):
        self.running = True
        self.searching = False
        self.dynamic_obstacles = False
        self.grid_size = DEFAULT_GRID_SIZE
        self.speed = 50
        self.algorithm = "A*"
        self.heuristic = "Manhattan"
        self.metrics = [0, 0, 0]
        self.grid = []
        self.start_node = None
        self.goal_node = None
        self.buttons = []
        self.sliders = []
        self.tooltip = None
        self.dragging_slider = None
        self.hovered_element = None
        self.show_tooltip = False
        self.tooltip_text = ""
        self.tooltip_pos = (0, 0)
        self.last_maze_time = 0
        self.maze_cooldown = 1

state = State()

# UTILITY FUNCTIONS 
def draw_tooltip(screen, text, pos):
    font = pygame.font.SysFont("arial", 16)
    text_surf = font.render(text, True, TEXT_COLOR)
    padding = 10
    rect = pygame.Rect(pos[0] + 10, pos[1] - 40, text_surf.get_width() + padding*2, text_surf.get_height() + padding*2)

    s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    s.fill((50, 55, 70, 200))
    screen.blit(s, (rect.x, rect.y))
    pygame.draw.rect(screen, BORDER_COLOR, rect, 1, border_radius=5)
    screen.blit(text_surf, (rect.x + padding, rect.y + padding))

def draw_rounded_rect(screen, color, rect, radius, border=0, border_color=None):
    if border > 0:
        pygame.draw.rect(screen, border_color, rect, border, border_radius=radius)
    s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(s, color, (0, 0, rect.width, rect.height), border_radius=radius)
    screen.blit(s, (rect.x, rect.y))

#CLASSES (UNCHANGED)
class Button:
    def __init__(self, x, y, w, h, text, action=None, color_key="normal"):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.action = action
        self.color_key = color_key
        self.hovered = False
        self.active = False
        self.tooltip = f"Click to {text.lower()}"

    def draw(self, screen):
        color = BUTTON_COLORS[self.color_key]
        if self.hovered and self.color_key != "stop":
            color = BUTTON_COLORS["hover"]
        if self.active:
            color = BUTTON_COLORS["active"]

        draw_rounded_rect(screen, color, self.rect, 10, 2, BORDER_COLOR)

        font = pygame.font.SysFont("arial", 18, bold=True)  #  font size
        text_surf = font.render(self.text, True, BUTTON_COLORS["text"])
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)

    def check_hover(self, pos):
        self.hovered = self.rect.collidepoint(pos)
        return self.hovered

    def click(self, pos):
        if self.rect.collidepoint(pos) and self.action:
            self.action()
            return True
        return False

class Slider:
    def __init__(self, x, y, w, h, min_val, max_val, initial_val, label):
        self.rect = pygame.Rect(x, y, w, h)
        self.knob_rect = pygame.Rect(x, y, 20, h)
        self.min_val = min_val
        self.max_val = max_val
        self.val = initial_val
        self.dragging = False
        self.label = label
        self.hovered = False
        self.tooltip = f"Drag to adjust {label.lower()}"

    def draw(self, screen):
        # Label
        font = pygame.font.SysFont("arial", 16)  #  font size
        label_surf = font.render(self.label, True, SLIDER_COLORS["text"])
        screen.blit(label_surf, (self.rect.x, self.rect.y - 25))  #  position

        # Value display
        val_font = pygame.font.SysFont("arial", 16)
        val_surf = val_font.render(str(self.val), True, SLIDER_COLORS["text"])
        screen.blit(val_surf, (self.rect.x + self.rect.w + 15, self.rect.y - 25))  #  position

        # Slider background
        draw_rounded_rect(screen, SLIDER_COLORS["bg"], self.rect, 7)
        # Slider knob
        draw_rounded_rect(screen, SLIDER_COLORS["knob"], self.knob_rect, 7)

    def check_hover(self, pos):
        self.hovered = self.rect.collidepoint(pos) or self.knob_rect.collidepoint(pos)
        return self.hovered

    def click(self, pos):
        if self.knob_rect.collidepoint(pos):
            self.dragging = True
            return True
        return False

    def update(self, pos):
        if self.dragging:
            self.knob_rect.x = max(self.rect.x, min(pos[0], self.rect.x + self.rect.w))
            self.val = int(self.min_val + (self.knob_rect.x - self.rect.x) / self.rect.w * (self.max_val - self.min_val))

class Node:
    def __init__(self, row, col, size, total_rows):
        self.row = row
        self.col = col
        self.x = col * size
        self.y = row * size
        self.size = size
        self.total_rows = total_rows
        self.color = NODE_COLORS["empty"]
        self.neighbors = []
        self.state = "empty"

    def get_pos(self):
        return self.row, self.col

    def is_barrier(self):
        return self.state == "barrier"

    def reset(self):
        self.state = "empty"
        self.color = NODE_COLORS["empty"]

    def make_start(self):
        self.state = "start"
        self.color = NODE_COLORS["start"]

    def make_goal(self):
        self.state = "goal"
        self.color = NODE_COLORS["goal"]

    def make_barrier(self):
        self.state = "barrier"
        self.color = NODE_COLORS["barrier"]

    def make_open(self):
        self.state = "open"
        self.color = NODE_COLORS["open"]

    def make_closed(self):
        self.state = "closed"
        self.color = NODE_COLORS["closed"]

    def make_path(self):
        self.state = "path"
        self.color = NODE_COLORS["path"]

    def draw(self, screen):
        pygame.draw.rect(screen, self.color, (self.x, self.y, self.size, self.size))
        if self.state == "start":
            gfxdraw.filled_circle(screen, self.x + self.size//2, self.y + self.size//2, self.size//3, NODE_COLORS["start"])
        elif self.state == "goal":
            gfxdraw.filled_polygon(screen, [
                (self.x + self.size//2, self.y + 5),
                (self.x + self.size - 5, self.y + self.size//2),
                (self.x + self.size//2, self.y + self.size - 5),
                (self.x + 5, self.y + self.size//2)
            ], NODE_COLORS["goal"])

    def update_neighbors(self, grid):
        self.neighbors = []
        directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        for dr, dc in directions:
            r, c = self.row + dr, self.col + dc
            if 0 <= r < self.total_rows and 0 <= c < self.total_rows:
                if not grid[r][c].is_barrier():
                    self.neighbors.append(grid[r][c])

#  PATHFINDING ALGORITHMS 
def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def euclidean(a, b):
    return math.sqrt((a[0] - b[0])**2 + (a[1] - b[1])**2)

def reconstruct_path(came_from, current, draw):
    path = []
    while current in came_from:
        current = came_from[current]
        current.make_path()
        path.append(current)
        draw()
    return path[::-1]

def pathfind(draw, grid, start, goal, algo, heuristic):
    count = 0
    open_set = []
    heapq.heappush(open_set, (0, count, start))
    came_from = {}
    g_score = {node: float("inf") for row in grid for node in row}
    g_score[start] = 0
    visited = 0
    start_time = time.time()

    while open_set and state.searching:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        current = heapq.heappop(open_set)[2]
        visited += 1

        if current == goal:
            path = reconstruct_path(came_from, goal, draw)
            exec_time = (time.time() - start_time) * 1000
            state.searching = False
            return visited, len(path), exec_time

        for neighbor in current.neighbors:
            temp_g = g_score[current] + 1
            h = manhattan(neighbor.get_pos(), goal.get_pos()) if heuristic == "Manhattan" else euclidean(neighbor.get_pos(), goal.get_pos())
            f = temp_g + h if algo == "A*" else h

            if temp_g < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = temp_g
                count += 1
                heapq.heappush(open_set, (f, count, neighbor))
                neighbor.make_open()

        draw()
        pygame.time.delay(max(0, 100 - state.speed))

        if current != start:
            current.make_closed()

    state.searching = False
    return visited, 0, 0

# GRID UTILITIES 
def make_grid(rows, width):
    gap = width // rows
    grid = []
    for i in range(rows):
        grid.append([])
        for j in range(rows):
            node = Node(i, j, gap, rows)
            grid[i].append(node)
    return grid

def draw_grid(screen, rows, width):
    gap = width // rows
    for i in range(rows):
        pygame.draw.line(screen, NODE_COLORS["grid"], (0, i * gap), (width, i * gap))
        pygame.draw.line(screen, NODE_COLORS["grid"], (i * gap, 0), (i * gap, width))

def generate_maze(grid):
    current_time = time.time()
    if current_time - state.last_maze_time < state.maze_cooldown:
        return

    state.last_maze_time = current_time
    for row in grid:
        for node in row:
            if random.random() < 0.25 and node != state.start_node and node != state.goal_node:
                node.make_barrier()
    for row in grid:
        for node in row:
            node.update_neighbors(grid)

def add_dynamic_obstacles(grid):
    for _ in range(2):
        r, c = random.randint(0, state.grid_size-1), random.randint(0, state.grid_size-1)
        if grid[r][c] != state.start_node and grid[r][c] != state.goal_node and not grid[r][c].is_barrier():
            grid[r][c].make_barrier()
            for row in grid:
                for node in row:
                    node.update_neighbors(grid)

#ADJUSTED DRAWING FUNCTIONS 
def draw_toolbar(screen):
    # Toolbar background
    draw_rounded_rect(screen, TOOLBAR_BG, pygame.Rect(GRID_WIDTH, 0, TOOLBAR_WIDTH, HEIGHT), 0)

    # Title section with highlight
    title_font = pygame.font.SysFont("arial", 28, True)  #  font size
    title = title_font.render("Pathfinding Pro", True, TEXT_COLOR)
    title_rect = title.get_rect(topleft=(GRID_WIDTH + 20, 15))  #  position
    pygame.draw.rect(screen, HIGHLIGHT_COLOR, (title_rect.x - 5, title_rect.y - 5, title_rect.width + 10, title_rect.height + 10), border_radius=5)
    screen.blit(title, title_rect)

    # Algorithm info section ( positions)
    info_font = pygame.font.SysFont("arial", 18)  #  font size
    algo_text = info_font.render(f"Algorithm: {state.algorithm}", True, TEXT_COLOR)
    heuristic_text = info_font.render(f"Heuristic: {state.heuristic}", True, TEXT_COLOR)
    screen.blit(algo_text, (GRID_WIDTH + 20, 70))  #  position
    screen.blit(heuristic_text, (GRID_WIDTH + 20, 95))  #  position

    # Section headers ( positions and font sizes)
    section_font = pygame.font.SysFont("arial", 20, True)  #  font size
    controls_title = section_font.render("Algorithm Controls", True, TEXT_COLOR)
    actions_title = section_font.render("Simulation Controls", True, TEXT_COLOR)
    utils_title = section_font.render("Utility Functions", True, TEXT_COLOR)
    settings_title = section_font.render("Simulation Settings", True, TEXT_COLOR)
    metrics_title = section_font.render("Performance Metrics", True, TEXT_COLOR)

    screen.blit(controls_title, (GRID_WIDTH + 20, 130))  #  position
    screen.blit(actions_title, (GRID_WIDTH + 20, 280))   #  position
    screen.blit(utils_title, (GRID_WIDTH + 20, 390))     #  position
    screen.blit(settings_title, (GRID_WIDTH + 20, 500))  #  position
    screen.blit(metrics_title, (GRID_WIDTH + 20, 610))   #  position

    # Draw buttons with  positions
    for button in state.buttons:
        button.draw(screen)

    # Draw sliders with  positions
    for slider in state.sliders:
        slider.draw(screen)

    # Metrics display ( position and size)
    draw_rounded_rect(screen, (50, 55, 70), pygame.Rect(GRID_WIDTH + 20, 640, 310, 90), 10)  #  position and height
    info_font = pygame.font.SysFont("arial", 18)  
    y = 660  #  starting position
    info = [
        f"Nodes Visited: {state.metrics[0]}",
        f"Path Length: {state.metrics[1]}",
        f"Time: {int(state.metrics[2])} ms"
    ]
    for t in info:
        text = info_font.render(t, True, TEXT_COLOR)
        screen.blit(text, (GRID_WIDTH + 30, y))
        y += 25  #  spacing

    # Tooltip
    if state.show_tooltip:
        draw_tooltip(screen, state.tooltip_text, state.tooltip_pos)

def draw(screen, grid):
    screen.fill(GRID_BG)
    for row in grid:
        for node in row:
            node.draw(screen)
    draw_grid(screen, state.grid_size, GRID_WIDTH)
    draw_toolbar(screen)
    pygame.display.flip()


def main():
    global state

    # Initialize screen 
    screen = pygame.display.set_mode((WIDTH, HEIGHT))

    # Initialize grid  default size
    state.grid = make_grid(state.grid_size, GRID_WIDTH)
    state.start_node = state.grid[3][3]  #starting position
    state.goal_node = state.grid[state.grid_size-4][state.grid_size-4]  #  goal position
    state.start_node.make_start()
    state.goal_node.make_goal()

    # Button actions 
    def set_algorithm(algo):
        state.algorithm = algo
        state.buttons[0].active = (algo == "A*")
        state.buttons[1].active = (algo == "GBFS")

    def set_heuristic(heuristic):
        state.heuristic = heuristic
        state.buttons[2].active = (heuristic == "Manhattan")
        state.buttons[3].active = (heuristic == "Euclidean")

    def start_search():
        if not state.searching:
            state.searching = True
            state.metrics = list(pathfind(
                lambda: draw(screen, state.grid),
                state.grid,
                state.start_node,
                state.goal_node,
                state.algorithm,
                state.heuristic
            ))

    def stop_search():
        state.searching = False

    def generate_new_maze():
        generate_maze(state.grid)

    def toggle_dynamic():
        state.dynamic_obstacles = not state.dynamic_obstacles
        state.buttons[7].text = "DYNAMIC ON" if state.dynamic_obstacles else "DYNAMIC OFF"

    # Create buttons 
    state.buttons = [
        # Algorithm selection buttons 
        Button(GRID_WIDTH + 20, 160, 150, 45, "A*", lambda: set_algorithm("A*"), "normal"),
        Button(GRID_WIDTH + 190, 160, 150, 45, "GBFS", lambda: set_algorithm("GBFS"), "normal"),
        Button(GRID_WIDTH + 20, 210, 150, 45, "Manhattan", lambda: set_heuristic("Manhattan"), "normal"),
        Button(GRID_WIDTH + 190, 210, 150, 45, "Euclidean", lambda: set_heuristic("Euclidean"), "normal"),

        # Action buttons
        Button(GRID_WIDTH + 20, 300, 150, 50, "START", start_search, "normal"),
        Button(GRID_WIDTH + 190, 300, 150, 50, "STOP", stop_search, "stop"),

        # Utility buttons
        Button(GRID_WIDTH + 20, 370, 150, 45, "GENERATE MAZE", generate_new_maze, "normal"),
        Button(GRID_WIDTH + 190, 370, 150, 45, "DYNAMIC OFF", toggle_dynamic, "normal")
    ]
    state.buttons[0].active = True
    state.buttons[2].active = True

    # Create sliders 
    state.sliders = [
        Slider(GRID_WIDTH + 20, 480, 310, 15, 10, 50, state.grid_size, "Grid Size:"),
        Slider(GRID_WIDTH + 20, 540, 310, 15, 1, 100, state.speed, "Simulation Speed:")
    ]

    # Main loop 
    clock = pygame.time.Clock()
    while state.running:
        clock.tick(FPS)
        mouse_pos = pygame.mouse.get_pos()
        mouse_pressed = pygame.mouse.get_pressed()

        # Handle events 
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                state.running = False

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    for button in state.buttons:
                        if button.click(event.pos):
                            break
                    for slider in state.sliders:
                        if slider.click(event.pos):
                            state.dragging_slider = slider
                            break
                    if event.pos[0] < GRID_WIDTH:
                        gap = GRID_WIDTH // state.grid_size
                        r, c = event.pos[1] // gap, event.pos[0] // gap
                        if 0 <= r < state.grid_size and 0 <= c < state.grid_size:
                            node = state.grid[r][c]
                            if node != state.start_node and node != state.goal_node:
                                node.make_barrier()
                                for row in state.grid:
                                    for n in row:
                                        n.update_neighbors(state.grid)

                elif event.button == 3:  # Right click
                    if event.pos[0] < GRID_WIDTH:
                        gap = GRID_WIDTH // state.grid_size
                        r, c = event.pos[1] // gap, event.pos[0] // gap
                        if 0 <= r < state.grid_size and 0 <= c < state.grid_size:
                            state.grid[r][c].reset()
                            for row in state.grid:
                                for node in row:
                                    node.update_neighbors(state.grid)

            if event.type == pygame.MOUSEMOTION:
                state.show_tooltip = False
                state.hovered_element = None

                for button in state.buttons:
                    if button.check_hover(mouse_pos):
                        state.show_tooltip = True
                        state.tooltip_text = button.tooltip
                        state.tooltip_pos = mouse_pos
                        state.hovered_element = button

                for slider in state.sliders:
                    if slider.check_hover(mouse_pos):
                        state.show_tooltip = True
                        state.tooltip_text = slider.tooltip
                        state.tooltip_pos = mouse_pos
                        state.hovered_element = slider

        if state.dragging_slider and mouse_pressed[0]:
            state.dragging_slider.update(mouse_pos)
            if state.dragging_slider == state.sliders[0]:
                new_size = state.sliders[0].val
                if new_size != state.grid_size:
                    state.grid_size = new_size
                    state.grid = make_grid(state.grid_size, GRID_WIDTH)
                    state.start_node = state.grid[min(3, state.grid_size-1)][min(3, state.grid_size-1)]
                    state.goal_node = state.grid[max(1, state.grid_size-4)][max(1, state.grid_size-4)]
                    state.start_node.make_start()
                    state.goal_node.make_goal()
            elif state.dragging_slider == state.sliders[1]:
                state.speed = state.sliders[1].val
        else:
            state.dragging_slider = None

        if state.dynamic_obstacles and not state.searching and random.random() < 0.01:
            add_dynamic_obstacles(state.grid)
            if state.searching:
                state.searching = False
                state.metrics = list(pathfind(
                    lambda: draw(screen, state.grid),
                    state.grid,
                    state.start_node,
                    state.goal_node,
                    state.algorithm,
                    state.heuristic
                ))

        draw(screen, state.grid)

    pygame.quit()

if __name__ == "__main__":
    main()
