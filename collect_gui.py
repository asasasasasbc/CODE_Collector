import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import threading
import json

# --- Config Constants ---
CONFIG_FILE = 'collector_config.json'

def collect_files_content_gui(root_dir, output_file, extensions_str, log_callback, progress_callback):
    """
    Recursively collects content from files with specified extensions in root_dir
    and writes it to output_file. Updates GUI via callbacks.

    Args:
        root_dir (str): The directory to start searching from.
        output_file (str): The path to the file where results will be saved.
        extensions_str (str): A pipe-separated string of file extensions (e.g., "cs|txt|xml").
        log_callback (function): Callback to send log messages to the GUI.
        progress_callback (function): Callback to update progress (0-100).
    """
    if not os.path.isdir(root_dir):
        log_callback(f"Error: Directory '{root_dir}' not found.")
        progress_callback(-1) # Indicate error
        return

    # 1. Parse user input extensions
    try:
        # Clean user input, ensure each extension starts with '.', put into tuple for endswith
        extensions = [ext.strip() for ext in extensions_str.split('|') if ext.strip()]
        if not extensions:
            log_callback(f"Error: No valid file extensions provided.")
            progress_callback(-1)
            return
        target_extensions = tuple(f".{ext}" if not ext.startswith('.') else ext for ext in extensions)
    except Exception as e:
        log_callback(f"Error: Failed to parse file extensions - {e}")
        progress_callback(-1)
        return

    # 2. Pre-scan to get total file count
    files_to_process = []
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith(target_extensions):
                files_to_process.append(os.path.join(dirpath, filename))
    
    total_files = len(files_to_process)
    processed_files = 0

    if total_files == 0:
        log_callback(f"No files with extension(s) {extensions_str} found in '{root_dir}'.")
        progress_callback(100) # No files, so 100% done
        return

    # 3. Start processing files
    try:
        with open(output_file, 'w', encoding='utf-8') as outfile:
            for full_path in files_to_process:
                processed_files += 1
                progress_value = int((processed_files / total_files) * 100)
                progress_callback(progress_value)

                relative_path = os.path.relpath(full_path, root_dir).replace(os.sep, '/')

                header = f"{relative_path}-------------\n"
                outfile.write(header)
                log_callback(f"Processing: {relative_path}")

                try:
                    with open(full_path, 'r', encoding='utf-8-sig') as f:
                        content = f.read()
                        outfile.write(content)
                except UnicodeDecodeError:
                    try:
                        with open(full_path, 'r', encoding='latin-1') as f:
                            content = f.read()
                            outfile.write(content)
                        outfile.write("\n[Warning: File read with latin-1 encoding]\n")
                        log_callback(f"Warning: {relative_path} read with latin-1 due to UTF-8 decoding error.")
                    except Exception as e_fallback:
                        error_msg = f"\n[Error: Unable to read file {relative_path} - {e_fallback}]\n"
                        outfile.write(error_msg)
                        log_callback(f"Read error {relative_path}: {e_fallback}")
                except Exception as e:
                    error_msg = f"\n[Error: Unable to process file {relative_path} - {e}]\n"
                    outfile.write(error_msg)
                    log_callback(f"Processing error {relative_path}: {e}")

                outfile.write("\n\n")
        
        log_callback(f"\nSuccessfully collected content from {total_files} files to '{output_file}'")
        progress_callback(100) # Ensure it hits 100% at the end
    except Exception as e:
        log_callback(f"Error occurred while writing to output file: {e}")
        progress_callback(-1) # Indicate error

class FileCollectorApp:
    def __init__(self, master):
        self.master = master
        master.title("CODE Collector")
        master.geometry("700x300")

        # --- Styling ---
        style = ttk.Style()
        style.configure("TButton", padding=5, font=('Helvetica', 10))
        style.configure("TLabel", padding=5, font=('Helvetica', 10))
        style.configure("TEntry", padding=5, font=('Helvetica', 10))

        # --- Frames ---
        input_frame = ttk.Frame(master, padding="10 10 10 10")
        input_frame.pack(fill=tk.X)

        action_frame = ttk.Frame(master, padding="10 0 10 10")
        action_frame.pack(fill=tk.X)
        
        log_frame = ttk.Frame(master, padding="10 0 10 10")
        log_frame.pack(fill=tk.BOTH, expand=True)

        # --- StringVars for GUI elements ---
        self.dir_entry_var = tk.StringVar()
        self.output_file_var = tk.StringVar()
        self.extensions_var = tk.StringVar(value="cs") # Default value

        # --- Input Directory ---
        ttk.Label(input_frame, text="Source Directory:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.dir_entry = ttk.Entry(input_frame, textvariable=self.dir_entry_var, width=60)
        self.dir_entry.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=5)
        self.browse_dir_button = ttk.Button(input_frame, text="Browse...", command=self.browse_directory)
        self.browse_dir_button.grid(row=0, column=2, padx=5, pady=5)

        # --- Output File ---
        ttk.Label(input_frame, text="Output File:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.output_file_entry = ttk.Entry(input_frame, textvariable=self.output_file_var, width=60)
        self.output_file_entry.grid(row=1, column=1, sticky=tk.EW, padx=5, pady=5)
        self.browse_output_button = ttk.Button(input_frame, text="Browse...", command=self.browse_output_file)
        self.browse_output_button.grid(row=1, column=2, padx=5, pady=5)

        # --- File Extensions ---
        ttk.Label(input_frame, text="File Extensions:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.extensions_entry = ttk.Entry(input_frame, textvariable=self.extensions_var)
        self.extensions_entry.grid(row=2, column=1, sticky=tk.EW, padx=5, pady=5)
        ttk.Label(input_frame, text="e.g. py|js").grid(row=2, column=2, sticky=tk.W, padx=5)
        
        input_frame.columnconfigure(1, weight=1)

        # --- Action Button & Progress Bar ---
        self.start_button = ttk.Button(action_frame, text="Start Collecting", command=self.start_collection_thread)
        self.start_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.progress_bar = ttk.Progressbar(action_frame, orient=tk.HORIZONTAL, length=300, mode='determinate')
        self.progress_bar.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=True)

        # --- Log Text Area ---
        ttk.Label(log_frame, text="Log:").pack(anchor=tk.W)
        self.log_text = tk.Text(log_frame, height=15, wrap=tk.WORD, font=('Courier New', 9))
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=(0,5))
        
        log_scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=(0,5))
        self.log_text.config(yscrollcommand=log_scrollbar.set)

        self.load_config() # Load last used configuration

    def load_config(self):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                
            # Validate path existence, fallback to default if not found
            source_dir = config.get("source_dir", "")
            if os.path.isdir(source_dir):
                self.dir_entry_var.set(source_dir)
            else:
                self.dir_entry_var.set(os.getcwd()) # Fallback to current dir

            # For output file, trust saved path unless empty
            output_file = config.get("output_file", "")
            if output_file:
                 self.output_file_var.set(output_file)
            else:
                 self.output_file_var.set(os.path.join(os.getcwd(), "result.txt"))

            self.extensions_var.set(config.get("extensions", "cs"))

        except (FileNotFoundError, json.JSONDecodeError):
            # If file not found or format error, use default values
            self.dir_entry_var.set(os.getcwd())
            self.output_file_var.set(os.path.join(os.getcwd(), "result.txt"))
            self.extensions_var.set("cs")

    def save_config(self):
        config = {
            "source_dir": self.dir_entry_var.get(),
            "output_file": self.output_file_var.get(),
            "extensions": self.extensions_var.get()
        }
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=4)
        except IOError as e:
            self.log_message(f"Warning: Unable to save configuration: {e}")

    def browse_directory(self):
        directory = filedialog.askdirectory(initialdir=self.dir_entry_var.get())
        if directory:
            self.dir_entry_var.set(directory)
            base_output_name = os.path.basename(self.output_file_var.get())
            if not base_output_name or base_output_name == ".txt":
                base_output_name = "result.txt"
            self.output_file_var.set(os.path.join(directory, base_output_name))

    def browse_output_file(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile=os.path.basename(self.output_file_var.get() or "result.txt"),
            initialdir=os.path.dirname(self.output_file_var.get() or os.getcwd())
        )
        if filepath:
            self.output_file_var.set(filepath)

    def log_message(self, message):
        if self.master.winfo_exists():
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)
            self.master.update_idletasks()

    def update_progress(self, value):
        if self.master.winfo_exists():
            if value == -1:
                self.progress_bar['value'] = 0
            else:
                self.progress_bar['value'] = value
            self.master.update_idletasks()

    def start_collection_thread(self):
        root_dir = self.dir_entry_var.get()
        output_file = self.output_file_var.get()
        extensions = self.extensions_var.get()

        if not root_dir or not os.path.isdir(root_dir):
            messagebox.showerror("Error", f"Source directory '{root_dir}' is invalid or does not exist.")
            return
        if not output_file:
            messagebox.showerror("Error", "Please enter output file name.")
            return
        if not extensions.strip():
            messagebox.showerror("Error", "Please enter at least one file extension.")
            return
        
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            if messagebox.askyesno("Create Directory?", f"Output directory '{output_dir}' does not exist. Create it?"):
                try:
                    os.makedirs(output_dir, exist_ok=True)
                except OSError as e:
                    messagebox.showerror("Error", f"Unable to create directory '{output_dir}': {e}")
                    return
            else:
                return

        self.save_config() # Save current configuration
        self.log_text.delete(1.0, tk.END)
        self.log_message("Starting collection process...")
        self.start_button.config(state=tk.DISABLED)
        self.browse_dir_button.config(state=tk.DISABLED)
        self.browse_output_button.config(state=tk.DISABLED)
        self.progress_bar['value'] = 0

        thread = threading.Thread(
            target=self._run_collection_task,
            args=(root_dir, output_file, extensions)
        )
        thread.daemon = True
        thread.start()

    def _run_collection_task(self, root_dir, output_file, extensions):
        try:
            collect_files_content_gui(root_dir, output_file, extensions, self.log_message, self.update_progress)
        except Exception as e:
            self.log_message(f"An unexpected error occurred: {e}")
            self.update_progress(-1)
        finally:
            if self.master.winfo_exists():
                self.master.after(0, self._enable_controls)

    def _enable_controls(self):
        if self.master.winfo_exists():
            self.start_button.config(state=tk.NORMAL)
            self.browse_dir_button.config(state=tk.NORMAL)
            self.browse_output_button.config(state=tk.NORMAL)
            if self.progress_bar['value'] == 100:
                 messagebox.showinfo("Done", "File collection completed!")
            elif self.progress_bar['value'] != 100 and "Error" in self.log_text.get(1.0, tk.END):
                 messagebox.showerror("Error", "Error occurred during file collection. Please check the log.")

def main():
    root = tk.Tk()
    app = FileCollectorApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
