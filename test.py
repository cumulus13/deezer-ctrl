import tkinter as tk
import win32gui
import win32con

# Function to set window style
def set_borderless(hwnd):
    # Get current window style
    style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)

    # Remove title bar, maximize button, minimize button, and thick frame
    style = style & ~(win32con.WS_CAPTION | win32con.WS_MAXIMIZEBOX | win32con.WS_MINIMIZEBOX | win32con.WS_THICKFRAME)

    # Apply the new style
    win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)

    # Update the window's non-client area to reflect the changes
    win32gui.SetWindowPos(hwnd, None, 0, 0, 0, 0,
                          win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOZORDER | win32con.SWP_FRAMECHANGED)

# Create the main application window
root = tk.Tk()

# Hide the window initially to prevent it from flashing on the screen
root.withdraw()
root.overrideredirect(True)
root.attributes("-topmost", True)  # Keep window on top initially
root.attributes("-alpha", 0.6)
#root.attributes("-toolwindow", False)  # Ensure the window appears in the taskbar
root.title("MPD Ticker")  # Set a title for the window            


# Call to ensure that the main window is visible
root.update_idletasks()

# Get the window handle
hwnd = int(root.wm_frame(), 16)

# Make the window borderless
set_borderless(hwnd)

# Show the window after setting it borderless
root.deiconify()

# Example: add some content to the window
label = tk.Label(root, text="Borderless Window", padx=10, pady=10)
label.pack()

# Run the application
root.mainloop()
