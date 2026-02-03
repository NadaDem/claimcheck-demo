import sqlite3

def build_database():
    print("🚧 Construction de la Base de Données ClaimCheck (Architecture Hybride)...")
    conn = sqlite3.connect('claimcheck.db')
    c = conn.cursor()

    # --- 1. TABLE DES TARIFS DE BASE (Lettres Clés) ---
    # Cette table gère la différence fondamentale entre K=22.50 (Privé) et K=13 (Public)
    c.execute('''CREATE TABLE IF NOT EXISTS lettres_cles (
        code TEXT PRIMARY KEY,
        description TEXT,
        tarif_prive REAL,
        tarif_public REAL,
        unite TEXT
    )''')

    # --- 2. TABLE DES FORFAITS (Actes packagés) ---
    # C'est ici qu'on stocke les Césariennes, Cataractes, etc.
    c.execute('''CREATE TABLE IF NOT EXISTS forfaits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom_acte TEXT,
        tarif_prive REAL,
        tarif_public REAL,
        details TEXT,
        mots_cles TEXT
    )''')

    # --- INJECTION DES DONNÉES (Source: Tes Documents ANAM) ---
    
    # A. LETTRES CLÉS
    # [cite_start]Sources: Grille 1 Privé [cite: 1648, 1716] [cite_start]& Grille 1 Public [cite: 1996]
    data_lettres = [
        ('C', 'Consultation Généraliste', 80.00, 50.00, 'Acte'),
        ('CS', 'Consultation Spécialiste', 150.00, 75.00, 'Acte'),
        ('CNPSY', 'Consultation Psy', 190.00, 100.00, 'Acte'),
        ('CSC', 'Consultation Cardio + ECG', 250.00, 190.00, 'Acte')[cite_start], # Privé revalorisé [cite: 1716]
        ('V', 'Visite Domicile', 120.00, 120.00, 'Acte'), # Public non précisé, on garde base
        ('K', 'Acte Chirurgie', 22.50, 13.00, 'Coefficient'), # La grosse différence !
        ('KC', 'Acte Chirurgie (Ancien)', 22.50, 13.00, 'Coefficient'),
        ('Z', 'Radiologie', 10.00, 9.00, 'Coefficient')[cite_start], # Z=9 en public [cite: 1996]
        ('B', 'Biologie', 1.10, 0.90, 'Coefficient')[cite_start], # B=0.90 en public [cite: 1996]
        ('KE', 'Echographie (Coeff)', 10.00, 10.00, 'Coefficient'),
        ('D', 'Soins Dentaires', 17.50, 10.00, 'Coefficient')[cite_start], # D=10 en public [cite: 1996]
        ('AMM', 'Kiné', 50.00, 40.00, 'Séance')[cite_start], # AMM=40 en public [cite: 1996]
        ('AMI', 'Soins Infirmiers', 7.50, 7.50, 'Acte')
    ]
    c.executemany('INSERT OR REPLACE INTO lettres_cles VALUES (?,?,?,?,?)', data_lettres)

    # B. FORFAITS CLINIQUES & HOPITAUX
    # Sources: Grilles 2, 3, 4, 5... Privé vs Public
    data_forfaits = [
        # ACC & GYNECO
        ('CESARIENNE', 8000.00, 3000.00, 'Forfait séjour inclus', 'cesarienne, césarienne')[cite_start], # Privé [cite: 1695][cite_start], Public [cite: 2014]
        ('ACCOUCHEMENT', 3000.00, 1000.00, 'Voie basse simple', 'accouchement, acc')[cite_start], # Public [cite: 2045]
        
        # CHIRURGIE COURANTE
        ('CATARACTE', 6500.00, 2500.00, 'Extra capsulaire', 'cataracte')[cite_start], # Privé [cite: 1685][cite_start], Public [cite: 2102]
        ('AMYGDALECTOMIE', 3000.00, 800.00, 'Adulte', 'amygdalectomie, amygdales')[cite_start], # Privé [cite: 1704][cite_start], Public [cite: 2094]
        ('VESICULE', 7500.00, 4000.00, 'Cholécystectomie', 'vesicule, cholecystectomie'), # Estimé public selon K
        
        # CARDIO (Le High Ticket)
        ('CORONAROGRAPHIE', 6000.00, 4500.00, 'Exploration', 'coronarographie')[cite_start], # Privé [cite: 1740][cite_start], Public [cite: 2140]
        ('ANGIOPLASTIE_1STENT', 49000.00, 46500.00, '1 Stent Actif', 'angioplastie, stent')[cite_start], # Privé [cite: 1779][cite_start], Public [cite: 2179]
        ('REMPLACEMENT_VALVULAIRE', 110000.00, 80000.00, 'Cœur ouvert', 'remplacement valvulaire, valve')[cite_start], # Privé [cite: 1812][cite_start], Public [cite: 2221]
        
        # CANCEROLOGIE
        ('CHIMIOTHERAPIE', 1000.00, 300.00, 'Par séance', 'chimiotherapie, chimio')[cite_start], # Privé [cite: 1870][cite_start], Public [cite: 2102]
        ('RADIOTHERAPIE_SEIN', 25200.00, 600.00, 'Forfait global vs Séance Public', 'radiotherapie sein')[cite_start], # Privé [cite: 1914][cite_start], Public [cite: 2109]
        ('GREFFE_MOELLE', 280000.00, 0, 'Forfait 30 jours', 'greffe moelle')[cite_start], # [cite: 1966]
        
        # SEJOURS (Par jour)
        ('LIT_MEDECINE', 550.00, 550.00, 'Par jour', 'sejour medecine, lit')[cite_start], # [cite: 1606, 2019]
        ('LIT_REANIMATION', 1500.00, 1800.00, 'Par jour', 'reanimation, rea')[cite_start], # Public plus cher ici ! [cite: 1611, 2028]
        ('LIT_SOINS_INTENSIFS', 1000.00, 1000.00, 'Par jour', 'soins intensifs, usic')[cite_start], # [cite: 1615, 2037]
        
        # IMAGERIE
        ('SCANNER_TDM', 1000.00, 840.00, 'TDM avec contraste', 'scanner, tdm')[cite_start], # [cite: 1626, 2057]
        ('IRM', 2200.00, 2000.00, 'Avec contraste', 'irm, resonance') [cite_start]# [cite: 1626, 2057]
    ]
    c.executemany('INSERT INTO forfaits (nom_acte, tarif_prive, tarif_public, details, mots_cles) VALUES (?,?,?,?,?)', data_forfaits)

    conn.commit()
    print("✅ Base de données CONSOLIDÉE (Privé ANAM + Public 2007) créée.")
    conn.close()

if __name__ == "__main__":
    build_database()
