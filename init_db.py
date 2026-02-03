import sqlite3

def init_database():
    # Création de la base de données persistante
    conn = sqlite3.connect('claimcheck_data.db')
    c = conn.cursor()

    # --- 1. TABLE DES RÉFÉRENTIELS (Lettres Clés) ---
    # Permet de gérer CNSS et CNOPS différemment
    c.execute('''CREATE TABLE IF NOT EXISTS lettres_cles (
        code TEXT,
        description TEXT,
        tarif_cnss REAL,
        tarif_cnops REAL,
        unite TEXT
    )''')

    # --- 2. TABLE DES ACTES (NGAP) ---
    # Stockera les milliers d'actes (Appendicite, Radio, etc.)
    c.execute('''CREATE TABLE IF NOT EXISTS actes_ngap (
        code_ngap TEXT PRIMARY KEY,
        description TEXT,
        lettre_cle TEXT,
        coefficient REAL
    )''')

    # --- 3. TABLE DES FORFAITS CLINIQUES (Spécifique Maroc) ---
    c.execute('''CREATE TABLE IF NOT EXISTS forfaits_cliniques (
        nom TEXT,
        tarif_cnss REAL,
        tarif_cnops REAL,
        details TEXT
    )''')

    # --- INJECTION DES DONNÉES QUE TU M'AS DONNÉES (Le "Seed") ---
    print("Injection des données de référence (Grilles 1-7 & Avenants)...")
    
    # Lettres Clés (Mise à jour avec tes infos précises)
    # Format: Code, Desc, Tarif CNSS, Tarif CNOPS (estimé ou identique), Unité
    data_lettres = [
        ('C', 'Consultation Généraliste', 80.00, 80.00, 'Actes'),
        ('CS', 'Consultation Spécialiste', 150.00, 150.00, 'Actes'),
        ('CNPSY', 'Consultation Psy', 190.00, 190.00, 'Actes'),
        ('CSC', 'Consultation Cardio + ECG', 190.00, 190.00, 'Actes'), # Avenant Cardio
        ('V', 'Visite Domicile', 120.00, 120.00, 'Actes'),
        ('K', 'Acte Chirurgie/Spécialité', 22.50, 20.00, 'Coefficient'), # K=22.50 (CNSS)
        ('KC', 'Acte Chirurgie', 22.50, 20.00, 'Coefficient'),
        ('Z', 'Radiologie', 10.00, 10.00, 'Coefficient'),
        ('B', 'Biologie', 1.10, 1.10, 'Coefficient'), # Confirmé
        ('D_SOIN', 'Soins Dentaires', 17.50, 17.50, 'Coefficient'), # Confirmé
        ('D_PROTH', 'Prothèse Dentaire', 12.50, 12.50, 'Coefficient'), # Confirmé
        ('AMM', 'Kiné', 50.00, 50.00, 'Séance'),
        ('AMO', 'Orthophonie', 50.00, 50.00, 'Séance')
    ]
    c.executemany('INSERT OR REPLACE INTO lettres_cles VALUES (?,?,?,?,?)', data_lettres)

    # Forfaits (Grilles 2, 3, etc.)
    data_forfaits = [
        ('CESARIENNE', 6000.00, 6000.00, 'Forfait global (Séjour inclus)'), # Revalorisé
        ('ACCOUCHEMENT_VOIE_BASSE', 3000.00, 3000.00, 'Forfait global'),
        ('CATARACTE', 4500.00, 4500.00, 'Forfait global'), # Revalorisé
        ('VESICULE_COELIO', 7500.00, 7500.00, 'Forfait global'),
        ('AMYGDALECTOMIE', 0, 0, 'Voir Avenant 2'), # A mettre à jour avec le doc précis
        ('LIT_MEDECINE', 550.00, 550.00, 'Par jour'),
        ('LIT_REANIMATION', 1500.00, 1500.00, 'Par jour'),
        ('LIT_SOINS_INTENSIFS', 1000.00, 1000.00, 'Par jour'),
        ('HEMODIALYSE', 850.00, 850.00, 'Par séance'),
        ('LITHOTRIPSIE', 5000.00, 5000.00, 'Forfait global'),
        ('CHIMIOTHERAPIE', 500.00, 500.00, 'Par séance (hors médicaments)')
    ]
    c.executemany('INSERT OR REPLACE INTO forfaits_cliniques VALUES (?,?,?,?)', data_forfaits)

    conn.commit()
    print("✅ Base de données 'claimcheck_data.db' créée et initialisée avec succès.")
    conn.close()

if __name__ == "__main__":
    init_database()
