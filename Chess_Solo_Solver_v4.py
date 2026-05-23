import tkinter as tk
import copy

CELL = 70
BOARD_LIGHT = "#f0d9b5"
BOARD_DARK = "#b58863"
HIGHLIGHT_LIGHT = "#F5E79A"
HIGHLIGHT_DARK = "#C5A452"


# ---------------- PIECE ----------------

class Piece:
    def __init__(self, t, x, y):
        self.t = t
        self.x = x
        self.y = y
        self.captures = 0
        self.frozen = False


UNICODE = {
    "K": ("♔", "♚"),
    "Q": ("♕", "♛"),
    "R": ("♖", "♜"),
    "B": ("♗", "♝"),
    "N": ("♘", "♞"),
    "P": ("♙", "♟"),
}


# ---------------- BOARD ----------------

class Board:
    def __init__(self):
        self.pieces = []
        self.start_pieces = []
        self.start_has_king = False

    def add(self, p):
        # overwrite square
        self.pieces = [x for x in self.pieces if not (x.x == p.x and x.y == p.y)]

        # one king total: replace old king
        if p.t == "K":
            self.pieces = [x for x in self.pieces if x.t != "K"]

        self.pieces.append(p)

    def remove(self, x, y):
        self.pieces = [p for p in self.pieces if not (p.x == x and p.y == y)]


# ---------------- HELPERS ----------------

def find(b, x, y):
    for p in b.pieces:
        if p.x == x and p.y == y:
            return p
    return None


def sq(x, y):
    return chr(x + 97) + str(8 - y)


def san(p, t, nx, ny):
    if p.t == "P":
        return f"{chr(p.x + 97)}x{sq(nx, ny)}"
    return f"{p.t}x{sq(nx, ny)}"


def inb(x, y):
    return 0 <= x < 8 and 0 <= y < 8


def king_was_present(b):
    if getattr(b, "start_has_king", False):
        return True
    return any(p.t == "K" for p in getattr(b, "start_pieces", []))


# ---------------- MOVES ----------------

def moves(b, p):
    if p.frozen:
        return []

    res = []

    if p.t == "P":
        for dx, dy in [(-1, -1), (1, -1)]:
            t = find(b, p.x + dx, p.y + dy)
            if t:
                res.append((p, t, p.x + dx, p.y + dy))

    elif p.t == "N":
        for dx, dy in [
            (1, 2), (2, 1), (-1, 2), (-2, 1),
            (1, -2), (2, -1), (-1, -2), (-2, -1)
        ]:
            t = find(b, p.x + dx, p.y + dy)
            if t:
                res.append((p, t, p.x + dx, p.y + dy))

    elif p.t in "BRQ":
        dirs = []
        if p.t in "RQ":
            dirs += [(1, 0), (-1, 0), (0, 1), (0, -1)]
        if p.t in "BQ":
            dirs += [(1, 1), (1, -1), (-1, 1), (-1, -1)]

        for dx, dy in dirs:
            x, y = p.x, p.y
            while True:
                x += dx
                y += dy
                if not inb(x, y):
                    break
                t = find(b, x, y)
                if t:
                    res.append((p, t, x, y))
                    break

    elif p.t == "K":
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                t = find(b, p.x + dx, p.y + dy)
                if t:
                    res.append((p, t, p.x + dx, p.y + dy))

    return res


# ---------------- APPLY ----------------

def apply(b, p, t, nx, ny):
    nb = copy.deepcopy(b)

    pp = find(nb, p.x, p.y)
    tt = find(nb, t.x, t.y)
    if pp is None or tt is None:
        return None

    nb.pieces.remove(tt)

    pp.x = nx
    pp.y = ny

    pp.captures += 1
    if pp.captures >= 2:
        pp.frozen = True

    return nb


# ---------------- SOLVER ----------------

def solved(b):
    if len(b.pieces) != 1:
        return False

    if king_was_present(b):
        return b.pieces[0].t == "K"

    return True


def solve(b, path=None):
    if path is None:
        path = []

    # If a king existed at the start, and it is already gone now, this branch is dead.
    if king_was_present(b) and not any(p.t == "K" for p in b.pieces):
        return None

    if solved(b):
        return path

    # Try the most constrained pieces first.
    pieces = sorted(b.pieces, key=lambda p: len(moves(b, p)))

    for p in pieces:
        if p.frozen:
            continue

        for m in moves(b, p):
            nb = apply(b, *m)
            if nb is None:
                continue

            step = san(*m)
            last_move = (p.x, p.y, m[2], m[3])

            res = solve(nb, path + [(step, nb, last_move)])
            if res:
                return res

    return None


# ---------------- APP ----------------

class App:
    def __init__(self, root):
        self.root = root
        self.board = Board()
        self.last_move = None

        self.solution = []
        self.index = 0
        self.mode = "editor"

        self.delay = 1.0
        self.from_current = False
        self.settings_open = False
        self.reset_settings_open = False

        self.playing = False
        self.play_job = None
        self.anim_job = None

        self.clear_on_reset = tk.BooleanVar(value=True)
        self.var = tk.BooleanVar(value=False)

        self.selected = "Q"
        self.start_board = None

        # ---------------- UI ----------------

        main = tk.Frame(root)
        main.pack()

        self.canvas = tk.Canvas(main, width=8 * CELL, height=8 * CELL)
        self.canvas.grid(row=0, column=0)
        self.canvas.bind("<Button-1>", self.left)
        self.canvas.bind("<Button-3>", self.right)

        side = tk.Frame(main)
        side.grid(row=0, column=1, sticky="n")

        self.listbox = tk.Listbox(side, width=25, height=18)
        self.listbox.pack()
        self.listbox.bind("<<ListboxSelect>>", self.jump)

        # Piece palette
        self.pf = tk.Frame(side)
        self.pf.pack(fill="x")

        self.pbtns = {}
        for i, p in enumerate(["K", "Q", "R", "B", "N", "P"]):
            b = tk.Button(
                self.pf,
                text=UNICODE[p][0],
                font=("Segoe UI Symbol", 18),
                width=4,
                command=lambda x=p: self.pick(x)
            )
            b.grid(row=i // 3, column=i % 3, sticky="nsew")
            self.pbtns[p] = b

        for c in range(3):
            self.pf.columnconfigure(c, weight=1)

        self.pick("Q")

        # Editor controls
        self.editor_frame = tk.Frame(side)
        self.editor_frame.pack(fill="x")

        self.clear_btn = tk.Button(self.editor_frame, text="Clear", command=self.clear)
        self.solve_btn = tk.Button(self.editor_frame, text="Solve", command=self.to_solver)
        self.readme_btn = tk.Button(self.editor_frame, text="README", command=self.open_readme)

        self.clear_btn.pack(fill="x")
        self.solve_btn.pack(fill="x")
        self.readme_btn.pack(fill="x")

        # Solver controls
        self.playback_frame = tk.Frame(side)
        self.play_btn = tk.Button(self.playback_frame, text="Playback", command=self.playback)
        self.play_btn.pack(fill="x")
        self.play_btn.bind("<Button-3>", self.toggle_settings)

        self.settings = tk.Frame(self.playback_frame)
        tk.Label(self.settings, text="Delay").pack()

        self.slider = tk.Scale(
            self.settings,
            from_=0.2,
            to=5.0,
            resolution=0.1,
            orient="horizontal",
            command=self.set_delay
        )
        self.slider.set(1.0)
        self.slider.pack()

        self.entry = tk.Entry(self.settings)
        self.entry.pack()
        self.entry.bind("<Return>", self.set_delay_entry)

        self.cb = tk.Checkbutton(
            self.settings,
            text="Start from current move",
            variable=self.var,
            command=self.toggle_from_current
        )
        self.cb.pack()

        self.reset_frame = tk.Frame(side)
        self.reset_btn = tk.Button(self.reset_frame, text="Reset", command=self.to_editor)
        self.reset_btn.pack(fill="x")
        self.reset_btn.bind("<Button-3>", self.toggle_reset_settings)

        self.reset_settings = tk.Frame(self.reset_frame)
        self.reset_checkbox = tk.Checkbutton(
            self.reset_settings,
            text="Clear board",
            variable=self.clear_on_reset
        )
        self.reset_checkbox.pack()

        root.bind("<Left>", self.prev)
        root.bind("<Right>", self.next)

        self.draw()

    # ---------------- PIECE PICK ----------------

    def pick(self, p):
        self.selected = p
        for name, btn in self.pbtns.items():
            btn.config(relief="raised", width=4)
        self.pbtns[p].config(relief="sunken", width=3)

    # ---------------- MODE SWITCH ----------------

    def to_solver(self):
        self.stop_playback()

        # Save the current puzzle position as the solution base.
        self.start_board = copy.deepcopy(self.board)
        self.start_board.start_pieces = copy.deepcopy(self.start_board.pieces)
        self.start_board.start_has_king = any(p.t == "K" for p in self.start_board.pieces)

        res = solve(self.start_board)
        if not res:
            print("No solution")
            self.solution = []
            self.index = 0
            self.last_move = None
            self.listbox.delete(0, tk.END)
            self.draw()
            return

        self.solution = [("START", copy.deepcopy(self.start_board), None)] + res
        self.index = 0
        self.last_move = None

        self.mode = "solver"

        self.settings.pack_forget()
        self.reset_settings.pack_forget()
        self.settings_open = False
        self.reset_settings_open = False

        self.pf.pack_forget()
        self.editor_frame.pack_forget()

        self.playback_frame.pack(fill="x")
        self.reset_frame.pack(fill="x")

        self.play_btn.config(text="Playback")

        self.listbox.delete(0, tk.END)
        for i, (m, _, _) in enumerate(self.solution):
            self.listbox.insert(tk.END, f"{i}. {m}")

        self.show_state(0)

    def to_editor(self):
        self.stop_playback()
        self.mode = "editor"

        self.playback_frame.pack_forget()
        self.reset_frame.pack_forget()

        self.settings.pack_forget()
        self.reset_settings.pack_forget()
        self.settings_open = False
        self.reset_settings_open = False

        self.pf.pack(fill="x")
        self.editor_frame.pack(fill="x")

        # Always clear notation/history when returning to editor
        self.solution = []
        self.index = 0
        self.listbox.delete(0, tk.END)
        self.last_move = None

        # If checked, clear board. If unchecked, restore the original puzzle.
        if self.clear_on_reset.get():
            self.board = Board()
        elif self.start_board is not None:
            self.board = copy.deepcopy(self.start_board)

        self.draw()

    # ---------------- INPUT ----------------

    def left(self, e):
        if self.mode != "editor":
            return
        x, y = e.x // CELL, e.y // CELL
        self.board.add(Piece(self.selected, x, y))
        self.last_move = None
        self.draw()

    def right(self, e):
        if self.mode != "editor":
            return
        x, y = e.x // CELL, e.y // CELL
        self.board.remove(x, y)
        self.last_move = None
        self.draw()

    def clear(self):
        if self.mode != "editor":
            return
        self.board = Board()
        self.last_move = None
        self.draw()

    # ---------------- README ----------------

    def open_readme(self):
        win = tk.Toplevel(self.root)
        win.title("📘 README — Solo Chess Solver v4")
        win.geometry("520x560")
        win.transient(self.root)

        frame = tk.Frame(win)
        frame.pack(expand=True, fill="both")

        scroll = tk.Scrollbar(frame)

        text = tk.Text(
            frame,
            wrap="word",
            padx=10,
            pady=10,
            yscrollcommand=scroll.set
        )

        scroll.config(command=text.yview)
        scroll.pack(side="right", fill="y")
        text.pack(side="left", expand=True, fill="both")

        content = """🧩 What this is

A small interactive Solo Chess puzzle solver + visualizer built in Python with Tkinter.

You place pieces on a board and the program attempts to solve the puzzle by finding a sequence of capture moves that reduces the board to a final state.

It also includes playback with a little animation so solutions can be watched step-by-step and more enjoyably.

I initially programmed this for chess.com Solo puzzles, so if you're into that kind of stuff (me too duh), you're welcome :)

Below are the requirements and some explanation and features, if you were tempted to click the button written in ALL CAPS:

------------------------------------------------------------

⚙️ Requirements

You only need:

• Python 3.10+
• Tkinter
(usually included with Python)

No external libraries required.

To run:

python your_file_name.py

------------------------------------------------------------

🎮 Editor Mode

This is where you build puzzles.

Controls:

Left click
→ Place selected piece

Right click
→ Remove piece

Piece buttons
→ Choose piece type

Clear
→ Remove all pieces

Solve
→ Send puzzle to solver

README
→ Open this window

------------------------------------------------------------

♟️ Solver Mode

Appears after pressing Solve.

Controls:

Playback
→ Start / stop replay

Right click Playback
→ Open playback settings

Reset
→ Return to editor

Left arrow
→ Previous move

Right arrow
→ Next move

Move list
→ Jump directly to move

------------------------------------------------------------

▶️ Playback

Features:

• Animated movement
• Last move highlighting
• Pause/resume support
• Adjustable speed
• Start from current move

------------------------------------------------------------

🤖 Solver rules

• Every move must capture
• If a king exists initially,
  it must be the last remaining piece
• Pieces that capture twice freeze
• Frozen pieces become black pieces
• Solver prioritizes constrained moves

(Basically chess.com, ya.)

------------------------------------------------------------

⚠️ Notes

• Some positions may naturally
  have no solution

• Extremely complex positions
  can take longer

• This is a puzzle solver,
  not a full chess engine

------------------------------------------------------------

💬 Final note

I would genuinely appreciate if people tested it
and gave feedback.

Especially:

• Bugs
• Strange positions
• Solver failures
• Unexpected solutions
• General opinions
• Ideas or improvements
• Things I forgot to mention
• Typos

Have fun using (and breaking) it :)
"""

        text.insert("1.0", content)
        text.config(state="disabled")

        tk.Button(win, text=" X ", command=win.destroy).pack(pady=5)

    # ---------------- SETTINGS ----------------

    def toggle_settings(self, e=None):
        self.settings_open = not self.settings_open
        if self.settings_open:
            self.settings.pack(fill="x")
        else:
            self.settings.pack_forget()

    def toggle_reset_settings(self, e=None):
        self.reset_settings_open = not self.reset_settings_open
        if self.reset_settings_open:
            self.reset_settings.pack(fill="x")
        else:
            self.reset_settings.pack_forget()

    def set_delay(self, v):
        try:
            val = float(v)
            if 0.2 <= val <= 5.0:
                self.delay = val
        except ValueError:
            pass

    def set_delay_entry(self, e=None):
        try:
            val = float(self.entry.get())
            if 0.2 <= val <= 5.0:
                self.delay = val
                self.slider.set(val)
        except ValueError:
            pass

    def toggle_from_current(self):
        self.from_current = self.var.get()

    # ---------------- PLAYBACK ----------------

    def stop_playback(self):
        self.playing = False

        if self.play_job is not None:
            try:
                self.root.after_cancel(self.play_job)
            except tk.TclError:
                pass
            self.play_job = None

        if self.anim_job is not None:
            try:
                self.root.after_cancel(self.anim_job)
            except tk.TclError:
                pass
            self.anim_job = None

        self.play_btn.config(text="Playback")

    def playback(self):
        if self.mode != "solver":
            return

        if self.playing:
            self.stop_playback()
            return

        if not self.solution:
            print("No solution loaded")
            return

        start_index = self.index if self.from_current else 0
        self.playing = True
        self.play_btn.config(text="Stop")

        self.show_state(start_index)

        if start_index >= len(self.solution) - 1:
            self.stop_playback()
            return

        self.play_job = self.root.after(
            int(self.delay * 1000),
            lambda: self.play_advance(start_index)
        )

    def play_advance(self, from_index):
        if not self.playing:
            return

        to_index = from_index + 1
        if to_index >= len(self.solution):
            self.stop_playback()
            return

        self.animate_transition(from_index, to_index)

    def animate_transition(self, from_index, to_index):
        if not self.playing:
            return

        from_board = self.solution[from_index][1]
        to_board = self.solution[to_index][1]
        move = self.solution[to_index][2]
        fx, fy, tx, ty = move

        mover = find(from_board, fx, fy)
        if mover is None:
            self.board = copy.deepcopy(to_board)
            self.last_move = move
            self.index = to_index
            self.draw()
            self.schedule_next(to_index)
            return

        symbol = UNICODE[mover.t][1] if mover.frozen else UNICODE[mover.t][0]

        steps = 12
        frame_ms = 18

        def frame(step):
            if not self.playing:
                return

            t = step / steps
            x = fx + (tx - fx) * t
            y = fy + (ty - fy) * t

            self.draw(
                board=from_board,
                anim_symbol=symbol,
                anim_pos=(x, y),
                anim_from=(fx, fy),
                last_move=None
            )

            if step < steps:
                self.anim_job = self.root.after(frame_ms, lambda: frame(step + 1))
            else:
                self.board = copy.deepcopy(to_board)
                self.last_move = move
                self.index = to_index
                self.draw()
                self.anim_job = None
                self.schedule_next(to_index)

        frame(0)

    def schedule_next(self, current_index):
        if not self.playing:
            return

        if current_index >= len(self.solution) - 1:
            self.stop_playback()
            return

        self.play_job = self.root.after(
            int(self.delay * 1000),
            lambda: self.play_advance(current_index)
        )

    # ---------------- LIST / NAV ----------------

    def show_state(self, i):
        if not self.solution or i < 0 or i >= len(self.solution):
            return

        _, board_state, last_move = self.solution[i]
        self.board = copy.deepcopy(board_state)
        self.last_move = last_move
        self.index = i
        self.draw()

        self.listbox.selection_clear(0, tk.END)
        self.listbox.selection_set(i)
        self.listbox.activate(i)
        self.listbox.see(i)

    def jump(self, e=None):
        if self.mode != "solver" or not self.solution:
            return

        sel = self.listbox.curselection()
        if not sel:
            return

        self.stop_playback()
        self.show_state(sel[0])

    def next(self, e=None):
        if self.mode != "solver" or not self.solution:
            return
        if self.index < len(self.solution) - 1:
            self.stop_playback()
            self.show_state(self.index + 1)

    def prev(self, e=None):
        if self.mode != "solver" or not self.solution:
            return
        if self.index > 0:
            self.stop_playback()
            self.show_state(self.index - 1)

# ---------------- DRAW ----------------

    def draw(self, board=None, anim_symbol=None, anim_pos=None, anim_from=None, last_move=None):
        board = self.board if board is None else board
        last_move = self.last_move if last_move is None else last_move

        self.canvas.delete("all")

        for r in range(8):
            for c in range(8):
                col = BOARD_LIGHT if (r + c) % 2 == 0 else BOARD_DARK
                self.canvas.create_rectangle(
                    c * CELL, r * CELL, (c + 1) * CELL, (r + 1) * CELL,
                    fill=col, outline=""
                )

        if last_move:
            x1, y1, x2, y2 = last_move

            from_color = HIGHLIGHT_LIGHT if (x1 + y1) % 2 == 0 else HIGHLIGHT_DARK
            to_color = HIGHLIGHT_LIGHT if (x2 + y2) % 2 == 0 else HIGHLIGHT_DARK

            self.canvas.create_rectangle(
                x1 * CELL, y1 * CELL, (x1 + 1) * CELL, (y1 + 1) * CELL,
                fill=from_color, outline=""
            )
            self.canvas.create_rectangle(
                x2 * CELL, y2 * CELL, (x2 + 1) * CELL, (y2 + 1) * CELL,
                fill=to_color, outline=""
            )

        for p in board.pieces:
            if anim_from and (p.x, p.y) == anim_from:
                continue

            symbol = UNICODE[p.t][1] if p.frozen else UNICODE[p.t][0]
            self.canvas.create_text(
                p.x * CELL + CELL // 2,
                p.y * CELL + CELL // 2,
                text=symbol,
                font=("Segoe UI Symbol", 50)
            )

        if anim_symbol and anim_pos:
            x, y = anim_pos
            self.canvas.create_text(
                x * CELL + CELL // 2,
                y * CELL + CELL // 2,
                text=anim_symbol,
                font=("Segoe UI Symbol", 50)
            )


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Solo Chess Solver v4")
    App(root)
    root.mainloop()
