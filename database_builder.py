import sqlite3
import os

def build_complete_database():
    print("🏗️ Construction de la Base de Données Unifiée (Public & Privé)...")
    
    # On nettoie pour être sûr de repartir à zéro
    if os.path.exists("claimcheck.db"):
        os.remove("claimcheck.db")
        print("🗑️ Ancienne base supprimée.")
        
    conn = sqlite3.connect('claimcheck.db')
    c = conn.cursor()

    # --- CRÉATION DES TABLES ---
    c.execute('''CREATE TABLE lettres_cles (
        code TEXT PRIMARY KEY,
        description TEXT,
        tarif_prive REAL,
        tarif_public REAL,
        unite TEXT
    )''')

    c.execute('''CREATE TABLE forfaits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom_acte TEXT,
        tarif_prive REAL,
        tarif_public REAL,
        details TEXT,
        mots_cles TEXT
    )''')

    # --- INJECTION DES DONNÉES (Tes PDF Publics + Privés) ---
    
    # 1. LETTRES CLÉS (La base du calcul)
    data_lettres = [
        ('C', 'Consultation Généraliste', 80.00, 50.00, 'Acte'),
        ('CS', 'Consultation Spécialiste', 150.00, 75.00, 'Acte'),
        ('CNPSY', 'Consultation Psy', 190.00, 100.00, 'Acte'),
        ('CP', 'Consultation Professeur', 150.00, 120.00, 'Acte'), 
        ('CSC', 'Consultation Cardio + ECG', 250.00, 190.00, 'Acte'),
        ('V', 'Visite Domicile', 120.00, 120.00, 'Acte'),
        ('K', 'Acte Chirurgie (K)', 22.50, 13.00, 'Coefficient'), # L'écart critique !
        ('KC', 'Acte Chirurgie (KC)', 22.50, 13.00, 'Coefficient'),
        ('Z', 'Radiologie', 10.00, 9.00, 'Coefficient'),
        ('B', 'Biologie', 1.10, 0.90, 'Coefficient'),
        ('D', 'Soins Dentaires', 17.50, 10.00, 'Coefficient'),
        ('AMM', 'Kiné', 50.00, 40.00, 'Séance'),
        ('AMI', 'Soins Infirmiers', 7.50, 7.50, 'Acte')
    ]
    c.executemany('INSERT INTO lettres_cles VALUES (?,?,?,?,?)', data_lettres)

    # 2. LES FORFAITS (Le "Gros Argent")
    data_forfaits = [
        # Maternité
        ('CESARIENNE', 8000.00, 3000.00, 'Séjour inclus', 'cesarienne, césarienne'),
        ('ACCOUCHEMENT', 3000.00, 1000.00, 'Voie basse', 'accouchement, accouchement normal'),
        
        # Chirurgie Ophtalmo & ORL
        ('CATARACTE', 6500.00, 2500.00, 'Classique', 'cataracte'),
        ('CATARACTE_PHACO', 8500.00, 3500.00, 'Phaco-émulsification', 'cataracte phaco'),
        ('AMYGDALECTOMIE', 3000.00, 800.00, 'Amygdales', 'amygdalectomie, amygdales'),
        ('VEGETATIONS', 2400.00, 240.00, 'Adénoïdectomie', 'vegetations, adenoidectomie'),

        # Cardio (Grilles 8 & 9)
        ('CORONAROGRAPHIE', 6000.00, 4500.00, 'Exploration', 'coronarographie'),
        ('ANGIOPLASTIE_1STENT', 49000.00, 46500.00, '1 Stent Actif', 'angioplastie, stent'),
        ('PACEMAKER', 35000.00, 24000.00, 'Double chambre', 'pacemaker, stimulateur'),
        ('REMPLACEMENT_VALVULAIRE', 110000.00, 80000.00, 'Cœur ouvert', 'remplacement valvulaire, valve'),

        # Oncologie (Grilles 13-18)
        ('CHIMIOTHERAPIE', 1000.00, 300.00, 'Par séance', 'chimiotherapie, chimio'),
        ('RADIOTHERAPIE_SEIN', 25200.00, 600.00, 'Forfait global vs Séance', 'radiotherapie sein'),
        ('GREFFE_MOELLE', 280000.00, 0, 'Forfait 30 jours', 'greffe moelle'),
        
        # Hospitalisation (Grille 3)
        ('LIT_MEDECINE', 550.00, 550.00, 'Par jour', 'sejour medecine, hospitalisation'),
        ('LIT_REANIMATION', 1500.00, 1800.00, 'Par jour (Public + cher!)', 'reanimation, rea'),
        
        # Imagerie (Grille 4)
        ('SCANNER', 1000.00, 840.00, 'TDM', 'scanner, tdm'),
        ('IRM', 2200.00, 2000.00, 'IRM', 'irm, resonance')
    ]
    c.executemany('INSERT INTO forfaits (nom_acte, tarif_prive, tarif_public, details, mots_cles) VALUES (?,?,?,?,?)', data_forfaits)

    conn.commit()
    print("✅ SUCCÈS : Base de données 'claimcheck.db' générée avec les tarifs Publics et Privés.")
    conn.close()

if __name__ == "__main__":
    build_complete_database()
