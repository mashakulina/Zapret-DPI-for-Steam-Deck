"""Keep dialog actions accessible when a scaled footer becomes narrow."""
import tkinter as tk


def pack_responsive_buttons(frame, buttons, gap=15, *, anchor=tk.CENTER):
    """Center compact actions, stacking them when their natural widths do not fit."""
    layout = None

    def arrange(event=None, *, width=None):
        nonlocal layout
        available = width if width is not None else (event.width if event is not None else frame.winfo_width())
        available -= 2 * frame.winfo_pixels(frame.cget('padx'))
        stacked = sum(button.winfo_reqwidth() for button in buttons) + gap * max(0, len(buttons) - 1) > available
        if layout == stacked:
            return
        layout = stacked
        for column in range(len(buttons) + 2):
            frame.columnconfigure(column, weight=0)
        frame.columnconfigure(0, weight=1 if anchor == tk.CENTER else 0)
        frame.columnconfigure(len(buttons) + 1, weight=1)
        for index, button in enumerate(buttons):
            button.pack_forget()
            button.grid_forget()
            button.grid(row=index if stacked else 0, column=1 if stacked else index + 1,
                        columnspan=len(buttons) if stacked else 1,
                        padx=(0, gap if not stacked and index < len(buttons) - 1 else 0),
                        pady=(0, gap if stacked and index < len(buttons) - 1 else 0))

    frame.bind('<Configure>', arrange, add='+')
    # Start compact; the first Configure event selects a row or a column.
    for index, button in enumerate(buttons):
        button.grid(row=0, column=index + 1,
                    padx=(0, gap if index < len(buttons) - 1 else 0))
    frame.after_idle(arrange)
    return arrange
