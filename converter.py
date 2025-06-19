# converter.py

import os
import re
import zipfile
import tempfile
from pathlib import Path
from PIL import Image
from pypdf import PdfWriter, PdfReader

def safe_filename(name):
    """Nettoie une chaîne pour l'utiliser comme nom de fichier."""
    return re.sub(r'[\\/*?:"<>|]', "", name)

def get_output_path(source_path, new_name, suffix):
    """Construit le chemin de sortie final dans le dossier d'origine."""
    base_name = Path(new_name).stem
    final_name = f"{base_name}{suffix}.pdf"
    return Path(source_path).parent / final_name

def process_cbz_file(cbz_filepath, suffix, quality, delete_originals, update_callback):
    """
    Traite un seul fichier CBZ.
    Prend en charge la qualité d'image et la suppression optionnelle.
    """
    try:
        p = Path(cbz_filepath)
        parent_dir_name = p.parent.name
        
        match = re.search(r'(?:chapter|capitulo)?[\s_-]*(\d+)', p.name, re.IGNORECASE)
        if not match:
            raise ValueError("Aucun numéro de chapitre trouvé dans le nom du fichier.")
            
        chapter_number = int(match.group(1))
        
        new_pdf_name = f"{safe_filename(parent_dir_name)} - {chapter_number}.pdf"
        output_pdf_path = get_output_path(cbz_filepath, new_pdf_name, suffix)
        
        update_callback(cbz_filepath, {"status": "processing", "details": "Extraction des images...", "progress": 10})

        with tempfile.TemporaryDirectory() as temp_dir:
            with zipfile.ZipFile(cbz_filepath, 'r') as archive:
                image_files = sorted([name for name in archive.namelist() if name.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))])
                if not image_files:
                    raise FileNotFoundError("Aucune image trouvée dans l'archive.")
                
                archive.extractall(temp_dir, members=image_files)
                update_callback(cbz_filepath, {"status": "processing", "details": f"Compilation du PDF (qualité: {quality}%)...", "progress": 60})
                
                images_pil = [Image.open(Path(temp_dir) / f).convert("RGB") for f in image_files]
                if images_pil:
                    images_pil[0].save(
                        output_pdf_path, 
                        "PDF", 
                        resolution=100.0, 
                        save_all=True, 
                        append_images=images_pil[1:],
                        quality=quality # Utilisation du paramètre de qualité
                    )
        
        if delete_originals:
            os.remove(cbz_filepath)
            details_msg = f"Remplacé par : {output_pdf_path.name}"
        else:
            details_msg = f"Créé : {output_pdf_path.name}"

        # On retourne le chemin complet du fichier de sortie pour les actions rapides
        update_callback(cbz_filepath, {"status": "success", "details": details_msg, "progress": 100, "outputPath": str(output_pdf_path)})

    except Exception as e:
        update_callback(cbz_filepath, {"status": "error", "details": f"Erreur : {e}", "progress": 100})

def combine_pdfs(pdf_filepaths, suffix, delete_originals, update_callback):
    """
    Fusionne plusieurs fichiers PDF.
    Gère la suppression optionnelle et les noms de fichiers avec des suffixes.
    """
    job_id = f"job_combine_{len(pdf_filepaths)}_{os.path.basename(pdf_filepaths[0])}"
    
    try:
        if len(pdf_filepaths) < 2:
            raise ValueError("Sélectionnez au moins deux PDF à fusionner.")

        update_callback(job_id, {"status": "processing", "details": "Analyse et tri des fichiers...", "progress": 5})

        parsed_files = []
        pattern = re.compile(r'(\d+)(?=[@#\[\.]|$)')

        for path in pdf_filepaths:
            try:
                with open(path, "rb") as f:
                    PdfReader(f)
            except Exception:
                update_callback(job_id, {"status": "error", "details": f"Erreur: Fichier {Path(path).name} corrompu ou illisible.", "progress": 100})
                return

            matches = pattern.findall(Path(path).stem)
            if matches:
                parsed_files.append({'path': path, 'num': int(matches[-1])})
            else:
                update_callback(job_id, {"status": "error", "details": f"Erreur: Impossible de trouver un numéro dans '{Path(path).name}'.", "progress": 100})
                return
        
        if not parsed_files:
             raise ValueError("Aucun fichier valide avec un numéro de chapitre n'a pu être traité.")

        parsed_files.sort(key=lambda x: x['num'])
        
        parent_dir_name = Path(parsed_files[0]['path']).parent.name
        start_chap, end_chap = parsed_files[0]['num'], parsed_files[-1]['num']
        
        new_pdf_name = f"{safe_filename(parent_dir_name)} {start_chap}-{end_chap}.pdf"
        output_pdf_path = get_output_path(parsed_files[0]['path'], new_pdf_name, suffix)
        
        merger = PdfWriter()
        total_files = len(parsed_files)
        for i, file_info in enumerate(parsed_files):
            progress = 10 + int(((i + 1) / total_files) * 80)
            details = f"Ajout de '{Path(file_info['path']).name}' ({i+1}/{total_files})"
            update_callback(job_id, {"status": "processing", "details": details, "progress": progress})
            merger.append(file_info['path'])
        
        update_callback(job_id, {"status": "processing", "details": "Écriture du fichier final...", "progress": 95})
        merger.write(output_pdf_path)
        merger.close()

        if delete_originals:
            for file_info in parsed_files:
                os.remove(file_info['path'])
            details_msg = f"Créé et originaux supprimés : {output_pdf_path.name}"
        else:
            details_msg = f"Créé : {output_pdf_path.name}"

        # On retourne le chemin complet du fichier de sortie pour les actions rapides
        update_callback(job_id, {"status": "success", "details": details_msg, "progress": 100, "outputPath": str(output_pdf_path)})

    except Exception as e:
        update_callback(job_id, {"status": "error", "details": f"Erreur : {e}", "progress": 100})