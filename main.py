# main.py

import eel
import threading
import tkinter as tk
from tkinter import filedialog
import os
import subprocess
import sys
from converter import process_cbz_file, combine_pdfs

eel.init('web')
active_threads = 0

def on_task_start():
    """Appelé au début de chaque thread."""
    global active_threads
    active_threads += 1

def on_task_end():
    """Appelé à la fin de chaque thread."""
    global active_threads
    active_threads -= 1
    if active_threads == 0:
        eel.sleep(0) 
        eel.all_tasks_complete()()

def run_in_thread(target_func, *args):
    """Lance une fonction dans un thread et gère le comptage."""
    def thread_wrapper():
        on_task_start()
        try:
            target_func(*args)
        finally:
            on_task_end()
    
    thread = threading.Thread(target=thread_wrapper)
    thread.start()

@eel.expose
def open_path(path):
    """Ouvre un fichier ou un dossier dans l'explorateur de fichiers natif."""
    try:
        # Assurer que le chemin existe pour éviter des erreurs
        if not os.path.exists(path):
            raise FileNotFoundError(f"Le chemin '{path}' n'existe pas.")
        
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin": # macOS
            subprocess.run(["open", path])
        else: # linux
            subprocess.run(["xdg-open", path])
    except Exception as e:
        print(f"Erreur en ouvrant le chemin {path}: {e}")
        eel.show_toast(f"Impossible d'ouvrir le chemin: {e}", "error")()

@eel.expose
def start_cbz_conversion(settings):
    """Sélectionne les fichiers CBZ et lance leur conversion avec les paramètres fournis."""
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    
    filepaths = filedialog.askopenfilenames(
        parent=root,
        title="Sélectionnez les fichiers .cbz à convertir",
        filetypes=[("Archives Comic Book", "*.cbz")]
    )
    
    if filepaths:
        eel.prepare_ui_for_tasks(list(filepaths), {})()
        for path in filepaths:
            run_in_thread(process_cbz_file, path, 
                          settings['suffix'], 
                          settings['quality'], 
                          settings['deleteOriginals'], 
                          eel.update_ui)
    else:
        # Si l'utilisateur annule la sélection, on déverrouille l'UI
        eel.all_tasks_complete()()

@eel.expose
def start_pdf_combination(settings):
    """Sélectionne les fichiers PDF et lance leur fusion avec les paramètres fournis."""
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    
    filepaths = filedialog.askopenfilenames(
        parent=root,
        title="Sélectionnez les PDF à fusionner (triés par nom)",
        filetypes=[("Fichiers PDF", "*.pdf")]
    )
    
    if filepaths:
        if len(filepaths) < 2:
            eel.show_toast("Veuillez sélectionner au moins deux fichiers PDF.", "warning")()
            eel.all_tasks_complete()()
            return

        job_id = f"job_combine_{len(filepaths)}_{os.path.basename(filepaths[0])}"
        task_list = [job_id]
        task_names = {job_id: f"Fusion de {len(filepaths)} chapitres"}
        
        eel.prepare_ui_for_tasks(task_list, task_names)()
        run_in_thread(combine_pdfs, list(filepaths),
                      settings['suffix'], 
                      settings['deleteOriginals'],
                      eel.update_ui)
    else:
        # Si l'utilisateur annule la sélection, on déverrouille l'UI
        eel.all_tasks_complete()()

if __name__ == '__main__':
    eel.start('index.html', size=(900, 850), mode='edge')