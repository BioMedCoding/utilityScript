import os
import shutil
import exifread
from tqdm import tqdm
import logging
from datetime import datetime

# Configurazione del logging
logging.basicConfig(filename="script.log", level=logging.INFO, format="%(asctime)s:%(levelname)s:%(message)s")

# Funzione per ottenere la data di creazione dai metadati EXIF
def get_creation_date(file_path):
    try:
        with open(file_path, 'rb') as f:
            tags = exifread.process_file(f)
            date_tag = 'EXIF DateTimeOriginal'
            if date_tag in tags:
                return datetime.strptime(str(tags[date_tag]), '%Y:%m:%d %H:%M:%S')
    except Exception as e:
        logging.error(f"Errore nella lettura dei metadati da {file_path}: {e}")
    return None

def get_user_input(prompt):
    value = input(prompt)
    confirmation = input(f"Hai inserito: '{value}'. Confermi? (s/n): ")
    while confirmation.lower() != 's':
        value = input(prompt)
        confirmation = input(f"Hai inserito: '{value}'. Confermi? (s/n): ")
    return value

def main():
    selected_jpg_folder = get_user_input("Inserisci il percorso della cartella contenente i file .jpg selezionati: ")
    sd_card_folders = get_user_input("Inserisci i percorsi delle cartelle delle schede SD (separati da uno spazio): ").split()
    output_folder = get_user_input("Inserisci il percorso della cartella di output per i file .arw: ")

    print("\nRiepilogo delle scelte:")
    print(f"Cartella contenente i file .jpg selezionati: {selected_jpg_folder}")
    print(f"Cartelle delle schede SD: {', '.join(sd_card_folders)}")
    print(f"Cartella di output per i file .arw: {output_folder}")

    final_confirmation = input("Confermi queste scelte? (s/n): ")
    if final_confirmation.lower() != 's':
        print("Operazione annullata.")
        return

    # Crea la cartella di output se non esiste
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Ottieni la lista dei file jpg selezionati
    selected_jpg_files = [f for f in os.listdir(selected_jpg_folder) if f.lower().endswith('.jpg')]

    # Dizionario per memorizzare i file .arw trovati
    arw_files = {}

    # Cerca i file .arw nelle cartelle delle schede SD
    for sd_folder in sd_card_folders:
        for root, _, files in os.walk(sd_folder):
            for file in files:
                if file.lower().endswith('.arw'):
                    arw_path = os.path.join(root, file)
                    creation_date = get_creation_date(arw_path)
                    if creation_date:
                        arw_files[creation_date] = arw_path

    # Crea un file di log per i file .arw non trovati
    log_file_path = os.path.join(output_folder, "log.txt")
    with open(log_file_path, "w") as log_file:
        # Copia i file .arw corrispondenti nella cartella di output
        for jpg_file in tqdm(selected_jpg_files, desc="Cercando file .arw corrispondenti"):
            jpg_path = os.path.join(selected_jpg_folder, jpg_file)
            jpg_creation_date = get_creation_date(jpg_path)
            
            if jpg_creation_date and jpg_creation_date in arw_files:
                arw_path = arw_files[jpg_creation_date]
                output_path = os.path.join(output_folder, os.path.basename(arw_path))
                try:
                    shutil.copy2(arw_path, output_path)
                    logging.info(f"Copiato {arw_path} in {output_path}")
                except Exception as e:
                    log_message = f"Errore nella copia di {arw_path} in {output_path}: {e}\n"
                    print(log_message)
                    log_file.write(log_message)
                    logging.error(log_message)
            else:
                log_message = f"File .arw non trovato per {jpg_file}\n"
                print(log_message)
                log_file.write(log_message)
                logging.warning(log_message)

    print("Script completato. Controlla il file di log per eventuali problemi.")

if __name__ == "__main__":
    main()
