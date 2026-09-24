"""Realism tables for the Clínica Arenal seed (scripts/seed_clinic.py).

Numbers come from INE (names, surnames, population), ICEA 2025 (insurer market), the Comunidad de
Madrid / Madrid city / Getafe labour calendars, the 2026 congress calendars (EADV, SECOT, SEMERGEN)
and RESA 2025 waiting times. Every person the seed invents is synthetic. See README.md next to this file.
"""
from datetime import date
from typing import Any

# ── Age (years on the anchor day) by sex. share of generated records, share female ─────────────
AGE_BRACKETS = [  # (min_age, max_age_inclusive, share, female_share)
    (0, 1, 0.025, 0.49),
    (2, 5, 0.055, 0.49),
    (6, 13, 0.100, 0.49),    # under-14 total 18% (paediatrics is 16.6% of provider hours, 30-min slots)
    (14, 17, 0.035, 0.50),
    (18, 29, 0.100, 0.55),
    (30, 44, 0.210, 0.57),
    (45, 64, 0.250, 0.55),
    (65, 79, 0.145, 0.55),
    (80, 94, 0.075, 0.64),
    (95, 101, 0.005, 0.75),
]
assert abs(sum(b[2] for b in AGE_BRACKETS) - 1) < 1e-9

# ── Home site (drives phone prefix, insurer, where they book) ─────────────────────────────────
HOME_SITE = {"centro": 0.45, "norte": 0.26, "sur": 0.29}   # = share of provider hours per site

GIVEN_NAMES_M = {  # INE Padrón 01/01/2022; top-28 per birth cohort; weight = thousands of people
    "<=1949": [("José", 178), ("Antonio", 151), ("Manuel", 132), ("Francisco", 119), ("Juan", 86), ("Pedro", 46), ("José Luis", 44), ("Ángel", 42), ("Jesús", 41), ("Miguel", 40), ("Luis", 40), ("José María", 37), ("Rafael", 36), ("José Antonio", 32), ("Vicente", 30), ("Ramón", 29), ("Fernando", 27), ("Joaquín", 22), ("Enrique", 21), ("Carlos", 18), ("José Manuel", 18), ("Andrés", 18), ("Emilio", 17), ("Juan José", 16), ("Julián", 16), ("Santiago", 15), ("Salvador", 15), ("Julio", 14)],
    "1950-1969": [("Antonio", 261), ("José", 221), ("Manuel", 221), ("Francisco", 198), ("José Luis", 135), ("José Antonio", 133), ("Juan", 119), ("Francisco Javier", 109), ("José Manuel", 99), ("Jesús", 92), ("Rafael", 87), ("José María", 86), ("Pedro", 82), ("Miguel Ángel", 81), ("Juan Carlos", 74), ("Fernando", 74), ("Ángel", 73), ("Miguel", 70), ("Carlos", 65), ("Luis", 62), ("Juan José", 61), ("Juan Antonio", 54), ("Ramón", 48), ("Vicente", 46), ("Javier", 45), ("Enrique", 43), ("Joaquín", 42), ("Juan Manuel", 42)],
    "1970-1989": [("David", 201), ("Antonio", 137), ("Javier", 136), ("Francisco Javier", 129), ("Manuel", 110), ("Daniel", 109), ("Miguel Ángel", 101), ("José Antonio", 101), ("Carlos", 99), ("Sergio", 94), ("José Manuel", 88), ("Francisco", 87), ("Alberto", 82), ("Jorge", 80), ("José Luis", 79), ("José", 77), ("Jesús", 76), ("Raúl", 75), ("Óscar", 75), ("Juan Carlos", 66), ("Rafael", 64), ("Rubén", 63), ("Fernando", 62), ("Alejandro", 62), ("Iván", 57), ("Juan", 57), ("Miguel", 57), ("José María", 54)],
    "1990-2009": [("Alejandro", 132), ("Daniel", 121), ("David", 115), ("Pablo", 96), ("Javier", 94), ("Adrián", 93), ("Sergio", 83), ("Álvaro", 82), ("Carlos", 73), ("Iván", 60), ("Jorge", 57), ("Manuel", 55), ("Antonio", 54), ("Diego", 52), ("Miguel", 50), ("Rubén", 49), ("Alberto", 47), ("Víctor", 44), ("Jesús", 43), ("Raúl", 43), ("Mario", 42), ("Francisco", 37), ("Marcos", 36), ("Juan", 36), ("Marc", 36), ("José", 33), ("Francisco Javier", 32), ("Ángel", 32)],
    "2010-2026": [("Hugo", 54), ("Daniel", 51), ("Alejandro", 47), ("Pablo", 46), ("Álvaro", 39), ("Adrián", 38), ("Martín", 36), ("Lucas", 35), ("David", 34), ("Mario", 30), ("Diego", 30), ("Mateo", 30), ("Manuel", 30), ("Javier", 27), ("Leo", 26), ("Marcos", 24), ("Sergio", 22), ("Izan", 21), ("Nicolás", 20), ("Alex", 20), ("Miguel", 20), ("Carlos", 20), ("Jorge", 19), ("Marc", 19), ("Iker", 19), ("Antonio", 19), ("Gonzalo", 18), ("Ángel", 17)],
}
GIVEN_NAMES_TAIL_M = {  # the rest of the same INE top-50 lists; sample uniformly
    "<=1949": ["Félix", "Juan Antonio", "Tomás", "Agustín", "Alfonso", "Domingo", "Mariano", "Jaime", "Eduardo", "Ricardo", "Diego", "Pablo", "Josep", "Gregorio", "Felipe", "Francisco Javier", "Alberto", "Miguel Ángel", "Alejandro", "Juan Manuel", "José Ramón", "Joan", "Eugenio", "Ignacio", "Sebastián", "Lorenzo", "Daniel"],
    "1950-1969": ["Santiago", "Andrés", "Jorge", "Alfonso", "Salvador", "Alberto", "Eduardo", "Emilio", "José Ramón", "Ricardo", "Francisco José", "Julián", "Agustín", "Julio", "José Miguel", "Diego", "Jaime", "Pablo", "Roberto", "Jordi", "David", "Ignacio", "Tomás", "Félix", "Domingo", "Mariano", "Josep"],
    "1970-1989": ["Roberto", "Juan José", "Pablo", "Ángel", "Juan Antonio", "Pedro", "Francisco José", "Juan Manuel", "Luis", "Diego", "Eduardo", "Jordi", "Enrique", "Ignacio", "Andrés", "Álvaro", "Adrián", "Víctor", "Santiago", "Ricardo", "Joaquín", "Ramón", "José Miguel", "Vicente", "Víctor Manuel", "Cristian", "Mohamed", "Marcos", "Mario"],
    "1990-2009": ["Miguel Ángel", "Hugo", "Óscar", "Samuel", "Rafael", "Luis", "Guillermo", "Jaime", "Pedro", "Ignacio", "Aitor", "Cristian", "Iker", "José Antonio", "Alex", "José Manuel", "Nicolás", "Fernando", "Ismael", "Pau", "Gonzalo", "Lucas", "Héctor", "Gabriel", "José Luis", "Rodrigo", "Andrés", "Aarón", "Borja", "Eduardo", "Juan José", "Juan Carlos", "Mohamed", "Francisco José"],
    "2010-2026": ["Juan", "Enzo", "Iván", "Samuel", "Bruno", "Marco", "Héctor", "Gabriel", "Eric", "Adam", "José", "Rubén", "Darío", "Oliver", "Víctor", "Rodrigo", "Aitor", "Jesús", "Raúl", "Aarón", "Guillermo", "Francisco", "Thiago", "Liam", "Gael", "Luca", "Dylan", "Jaime", "Pau", "Ian"],
}
GIVEN_NAMES_F = {  # INE Padrón 01/01/2022; top-24 per birth cohort; weight = thousands of people
    "<=1949": [("María", 143), ("María del Carmen", 136), ("Carmen", 135), ("Josefa", 106), ("Dolores", 74), ("Francisca", 70), ("Isabel", 68), ("Antonia", 68), ("María del Pilar", 55), ("María Teresa", 53), ("Pilar", 51), ("Concepción", 50), ("María Dolores", 47), ("María Luisa", 43), ("Manuela", 42), ("Juana", 42), ("Teresa", 39), ("Ana", 38), ("María de los Ángeles", 38), ("Rosario", 38), ("Mercedes", 38), ("Rosa", 38), ("Ana María", 35), ("Encarnación", 35)],
    "1950-1969": [("María del Carmen", 329), ("María Dolores", 132), ("María del Pilar", 130), ("Ana María", 121), ("María Teresa", 119), ("María de los Ángeles", 112), ("Carmen", 112), ("Josefa", 111), ("María Isabel", 103), ("María", 101), ("Isabel", 99), ("Francisca", 90), ("Antonia", 88), ("María José", 86), ("Rosa María", 80), ("María Luisa", 75), ("Dolores", 73), ("María Jesús", 72), ("Concepción", 62), ("Manuela", 59), ("Mercedes", 58), ("Ana", 55), ("Pilar", 51), ("Rosario", 51)],
    "1970-1989": [("María del Carmen", 141), ("Cristina", 118), ("Laura", 106), ("María", 102), ("María José", 91), ("Raquel", 91), ("Marta", 90), ("Ana María", 88), ("Mónica", 76), ("Sonia", 74), ("Silvia", 74), ("Beatriz", 70), ("Susana", 65), ("Patricia", 65), ("María Isabel", 62), ("Ana", 62), ("María del Pilar", 60), ("María Dolores", 60), ("Yolanda", 60), ("María Teresa", 59), ("María de los Ángeles", 57), ("Nuria", 56), ("Elena", 54), ("Verónica", 53)],
    "1990-2009": [("María", 155), ("Laura", 114), ("Lucía", 103), ("Paula", 100), ("Marta", 93), ("Sara", 79), ("Andrea", 78), ("Alba", 76), ("Cristina", 74), ("Ana", 65), ("Irene", 56), ("Claudia", 49), ("Elena", 47), ("Marina", 45), ("Nerea", 43), ("Carla", 43), ("Natalia", 41), ("Sandra", 40), ("Rocío", 39), ("Carmen", 38), ("Patricia", 38), ("Raquel", 36), ("Julia", 32), ("Noelia", 30)],
    "2010-2026": [("Lucía", 58), ("María", 51), ("Paula", 45), ("Martina", 43), ("Sofía", 43), ("Daniela", 39), ("Sara", 35), ("Julia", 35), ("Carla", 34), ("Alba", 33), ("Valeria", 32), ("Claudia", 28), ("Noa", 27), ("Emma", 26), ("Carmen", 26), ("Marta", 22), ("Irene", 21), ("Laura", 20), ("Ana", 20), ("Adriana", 19), ("Elena", 19), ("Aitana", 18), ("Alejandra", 17), ("Valentina", 17)],
}
GIVEN_NAMES_TAIL_F = {  # the rest of the same INE top-50 lists; sample uniformly
    "<=1949": ["Ángeles", "María Josefa", "Julia", "Margarita", "María Isabel", "María Jesús", "Amparo", "Ángela", "Consuelo", "Luisa", "María Rosa", "Emilia", "Josefina", "Catalina", "María de la Concepción", "Montserrat", "Vicenta", "Milagros", "Aurora", "Rosa María", "Purificación", "Elena", "Esperanza", "María del Rosario", "María Antonia", "María Mercedes", "Victoria", "Felisa", "Asunción", "Matilde", "Trinidad"],
    "1950-1969": ["Encarnación", "Montserrat", "Juana", "María Josefa", "María del Rosario", "María Mercedes", "Margarita", "Teresa", "Rosa", "María de la Concepción", "María del Mar", "María Rosa", "María Victoria", "María Antonia", "Elena", "María Nieves", "María Soledad", "Ana Isabel", "Inmaculada", "Yolanda", "María Elena", "Cristina", "Susana", "Nuria", "Marta", "Ángeles", "María Begoña", "Julia", "Amparo", "Consuelo", "Ángela", "Josefina", "Emilia", "Catalina", "Milagros", "María Asunción"],
    "1970-1989": ["Sandra", "Ana Belén", "María del Mar", "Rocío", "Isabel", "Eva", "Ana Isabel", "Eva María", "Noelia", "Inmaculada", "Natalia", "Esther", "Alicia", "Carmen", "Carolina", "Sara", "Rosa María", "Montserrat", "Vanesa", "Lorena", "María Jesús", "María Luisa", "Francisca", "Antonia", "Miriam", "Irene", "Olga", "María Elena", "Estefanía", "Mercedes", "Tamara", "Lucía", "Josefa", "Vanessa", "María Belén", "Jessica", "Paula", "Lidia"],
    "1990-2009": ["Nuria", "Miriam", "Ángela", "Lorena", "Silvia", "Alicia", "Isabel", "Sofía", "Eva", "Clara", "Celia", "Beatriz", "Carolina", "Ainhoa", "Daniela", "María del Carmen", "Alejandra", "Ana María", "Inés", "Aitana", "María José", "Adriana", "Estefanía", "Tamara", "Laia", "Mónica", "Ariadna", "Lidia", "Martina", "Sonia", "Verónica", "Anna", "Carlota", "Blanca", "Tania", "Candela", "Jennifer", "Noa", "Esther", "Ainara", "Belén"],
    "2010-2026": ["Lola", "Inés", "Laia", "Jimena", "Alma", "Vega", "Candela", "Olivia", "Marina", "Ariadna", "Ainhoa", "Carlota", "Rocío", "Vera", "Blanca", "Nerea", "Alicia", "Nora", "Clara", "Andrea", "Leire", "Ainara", "Victoria", "Ángela", "Celia", "Natalia", "Lara", "Mía", "Chloe", "Abril", "Triana", "Manuela", "Lía", "Zoe"],
}
GIVEN_TOP_SHARE = {  # INE: share of the cohort carrying one of its top-24/28 names; else draw from the tail
    "M": {'<=1949': 0.54, '1950-1969': 0.46, '1970-1989': 0.36, '1990-2009': 0.35, '2010-2026': 0.32},
    "F": {'<=1949': 0.45, '1950-1969': 0.39, '1970-1989': 0.28, '1990-2009': 0.32, '2010-2026': 0.3},
}

# Madrid/national ratio used for names outside the Madrid top 50: 0.153
SURNAMES = [  # INE Censo anual 01/01/2025; weight = hundreds of Madrid-province residents with it as 1st surname
    ("García", 2281), ("González", 1408), ("Sánchez", 1363), ("Fernández", 1341), ("Rodríguez", 1305),
    ("López", 1284), ("Martínez", 1048), ("Martín", 1017), ("Pérez", 989), ("Gómez", 825), ("Jiménez", 664),
    ("Díaz", 588), ("Hernández", 579), ("Moreno", 506), ("Muñoz", 496), ("Ruiz", 469), ("Álvarez", 415),
    ("Alonso", 351), ("Gutiérrez", 330), ("Romero", 299), ("Sanz", 271), ("Ramírez", 256), ("Torres", 254),
    ("Serrano", 240), ("Ramos", 231), ("Gil", 204), ("Domínguez", 200), ("Blanco", 198), ("Rubio", 191),
    ("Morales", 186), ("Delgado", 181), ("Ortega", 179), ("Navarro", 177), ("Ortiz", 177), ("Molina", 163),
    ("Castro", 160), ("Vázquez", 159), ("Núñez", 153), ("Castillo", 146), ("Santos", 146), ("Flores", 138),
    ("Cortés", 137), ("Medina", 134), ("Suárez", 131), ("Iglesias", 131), ("Peña", 128), ("Prieto", 128),
    ("Garrido", 127), ("Guerrero", 127), ("Marín", 126), ("Lozano", 124), ("Gallego", 122), ("Montero", 122),
    ("Cruz", 120), ("Esteban", 119), ("Herrera", 118), ("Cano", 118), ("Méndez", 118), ("León", 112),
    ("Cabrera", 110), ("Márquez", 110), ("Reyes", 109), ("Campos", 104), ("Vidal", 103), ("Calvo", 103),
    ("Vega", 102), ("Fuentes", 100), ("Aguilar", 98), ("Vargas", 97), ("Carrasco", 96), ("Caballero", 94),
    ("Nieto", 92), ("Díez", 91), ("Rojas", 90), ("Santana", 90), ("Giménez", 88), ("Benítez", 87),
    ("Arias", 87), ("Hidalgo", 87), ("Santiago", 85), ("Pascual", 85), ("Durán", 85), ("Mora", 85),
    ("Herrero", 85), ("Lorenzo", 84), ("Ibáñez", 82), ("Ferrer", 81), ("Carmona", 80), ("Soto", 79),
    ("Vicente", 78), ("Rivera", 75), ("Silva", 75), ("Román", 75), ("Parra", 74), ("Crespo", 74),
    ("Mendoza", 72), ("Velasco", 72), ("Pastor", 71), ("Bravo", 71), ("Rivas", 70), ("Moya", 69),
]
# count 101

GIVEN_NAME_COHORTS = [(None, 1949, "<=1949"), (1950, 1969, "1950-1969"), (1970, 1989, "1970-1989"),
                      (1990, 2009, "1990-2009"), (2010, 2026, "2010-2026")]
COMPOUND_GIVEN_NAME_ALT = {          # the chart spells some INE compounds either way; pick the alt 40% of the time
    "María del Carmen": "María Carmen", "María de los Ángeles": "María Ángeles",
    "María del Pilar": "María Pilar",
}
KNOWN_AS = {                         # hypocorisms a caller uses for themself; set on ~15% of adults 45+
    "María del Carmen": "Mari Carmen", "María Carmen": "Maricarmen", "Dolores": "Lola",
    "María Dolores": "Loli", "Josefa": "Pepa", "José": "Pepe", "Francisco": "Paco", "Manuel": "Manolo",
    "Concepción": "Conchi", "Rosario": "Charo", "María Teresa": "Maite", "María Luisa": "Marisa",
    "José María": "Chema", "Ignacio": "Nacho", "Enrique": "Quique", "Francisco Javier": "Javier",
    "Pilar": "Pili", "Mercedes": "Merche", "Encarnación": "Encarna", "Consuelo": "Chelo",
    "Juan José": "Juanjo", "José Miguel": "Josemi", "Antonio": "Toni", "María Isabel": "Maribel",
    "María de los Ángeles": "Marian", "Purificación": "Puri", "Inmaculada": "Inma", "Asunción": "Susi",
}
SURNAMES_TAIL = [  # INE 2025 national ranks 101-400 (accents restored by hand); sample uniformly
    "Franco", "Sáez", "Gallardo", "Ríos", "Soler", "Pardo", "Vera", "Lara", "Camacho", "Espinosa",
    "Merino", "Sierra", "Izquierdo", "Carrillo", "Arroyo", "Montes", "Contreras", "Luque", "Casado",
    "Segura", "Rey", "Redondo", "Galán", "Heredia", "Otero", "Bernal", "Salazar", "Palacios", "Pereira",
    "Robles", "Soriano", "Marcos", "Guerra", "Miranda", "Acosta", "Valero", "Varela", "Martí", "Macías",
    "Guzmán", "Vila", "Expósito", "Roldán", "Calderón", "Guillén", "Bueno", "Mateo", "Aguilera", "Benito",
    "Padilla", "Rivero", "Andrés", "Villar", "Escudero", "Bermúdez", "Salas", "Escobar", "Beltrán",
    "Mateos", "Ávila", "Casas", "Aparicio", "Hurtado", "Gálvez", "Estévez", "Quintana", "Trujillo", "Rico",
    "Pacheco", "Jurado", "Conde", "Aranda", "Menéndez", "Plaza", "Abad", "Villanueva", "Montoya", "Gracia",
    "Rueda", "Manzano", "Valencia", "Costa", "Maldonado", "Santamaría", "Paredes", "Blázquez", "Luna",
    "Mesa", "Roca", "Castaño", "Alarcón", "Zamora", "Serra", "Cuesta", "Miguel", "Tomás", "Millán",
    "Simón", "de la Fuente", "Bautista", "de la Cruz", "del Río", "Murillo", "Ponce", "Lázaro", "Pons",
    "Sancho", "Ordóñez", "Valverde", "Amador", "Ballesteros", "Cordero", "Salvador", "Valle", "Blasco",
    "Oliva", "Bermejo", "Barrera", "Cuevas", "Antón", "Aguirre", "Lorente", "Pozo", "Cárdenas", "Cuenca",
    "Quintero", "Arenas", "Collado", "Rodrigo", "Pulido", "Martos", "Quesada", "Barroso", "Sosa",
    "de la Torre", "Navas", "Paz", "Mas", "Zapata", "Juan", "Galindo", "Mena", "Correa", "Vallejo",
    "Bonilla", "Villalba", "Alba", "Cabello", "Naranjo", "Cáceres", "Linares", "Ros", "Soria", "Caro",
    "Ojeda", "Marco", "Pineda", "Leal", "Rojo", "Mata", "Corral", "Reina", "Aguado", "Morán", "Lucas",
    "Polo", "Escribano", "Chacón", "Gimeno", "Puig", "Saiz", "Domingo", "Asensio", "Burgos", "Ramón",
    "Saavedra", "Ayala", "Córdoba", "Barrios", "Villa", "Cardona", "Aragón", "Ferreira", "Carretero",
    "Villegas", "Carrión", "Cámara", "Velázquez", "Oliver", "Castellano", "Juárez", "Toledo", "Rosa",
    "Calero", "Salgado", "Salinas", "Clemente", "Carrera", "Pinto", "Rincón", "Alcaraz", "Solís", "Roig",
    "Cobo", "Prado", "Vela", "Alfonso", "Andreu", "Hernando", "Riera", "Sevilla", "Mejía", "Peláez",
    "Sola", "Olivares", "Arévalo", "Carbonell", "Vélez", "Requena", "Moral", "Duarte", "Palma", "Llorente",
    "de la Rosa", "Domènech", "Zambrano", "Ochoa", "Angulo", "Luis", "Carballo", "Perea", "Peralta",
    "Arribas", "Marrero", "Piñeiro", "Pino", "Estrada", "Porras", "Castellanos", "Cantero", "Alvarado",
    "Osorio", "Becerra", "Castilla", "Marqués", "Font", "Figueroa", "Esteve", "Ventura", "Vergara", "Grau",
    "Rosales", "Casanova", "Baena", "Bosch", "Carvajal", "Madrid", "Cid", "Godoy", "Palomo", "Toro",
    "Ballester", "Alfaro", "Tapia", "Sanchis", "Amaya", "Belmonte", "Mosquera", "Fajardo", "Cabezas",
    "Barba", "Chávez", "Bello", "Nicolás", "Recio", "Lago", "Cobos", "Granados", "Miralles", "Corrales",
    "Navarrete", "Duque", "Alcántara", "Dávila", "Muñiz", "Sala", "Gámez", "Herranz", "Valenzuela",
    "Arranz", "Cuadrado",
]
SURNAME_TIERS = {"SURNAMES": 0.39, "SURNAMES_TAIL": 0.61}

# No hyphenated surnames: `_verify` compares spoken words with on-file words, so 'García-Moreno'
# could never be verified by a caller saying 'García Moreno'.
EXTRA_COMPOUND_SURNAMES = ["del Pozo", "de Miguel", "del Valle", "San Martín", "Sáenz de Santamaría"]
EXTRA_COMPOUND_SHARE = 0.005

# ── Origin groups (who the patient is; drives names, id document, language, insurer) ──────────
ORIGIN = {  # share of records
    "es_general":   0.795,   # Spanish, INE Madrid names
    "es_catalan":   0.025,   # Catalan surnames (+ Catalan given name 50%); lives in Madrid
    "es_galician":  0.025,   # Galician surnames (+ Galician given name 25%)
    "es_basque":    0.015,   # Basque surnames (+ Basque given name 40%)
    "latam_dni":    0.010,   # Latin-American-born, now Spanish nationals (DNI), Latin names
    "latam_nie":    0.050,   # Venezuela, Colombia, Peru, Ecuador, Argentina, Honduras (NIE, Spanish-speaking)
    "expat_en":     0.035,   # UK, Ireland, US, plus Dutch/Nordic who prefer English (NIE)
    "expat_eu":     0.025,   # France, Italy, Germany, Portugal (NIE)
    "ro_ua":        0.010,   # Romania, Ukraine (NIE)
    "maghreb":      0.006,   # Morocco (NIE)
    "china":        0.004,   # China (NIE)
}
assert abs(sum(ORIGIN.values()) - 1) < 1e-9   # NIE holders = 13%; non-Spanish preferred language ~8%
PREFERRED_LANGUAGE = {  # by origin; values are BCP-47 codes, tools.py filters only ca/eu/gl
    "es_general": {"es": 1.0},
    "es_catalan": {"ca": 0.45, "es": 0.55},
    "es_galician": {"gl": 0.15, "es": 0.85},
    "es_basque": {"eu": 0.15, "es": 0.85},
    "latam_dni": {"es": 1.0}, "latam_nie": {"es": 1.0},
    "expat_en": {"en": 0.90, "es": 0.10},
    "expat_eu": {"fr": 0.30, "it": 0.30, "de": 0.20, "pt": 0.20},
    "ro_ua": {"ro": 0.55, "uk": 0.25, "es": 0.20},
    "maghreb": {"ar": 0.40, "fr": 0.20, "es": 0.40},
    "china": {"zh": 0.70, "es": 0.30},
}
REGIONAL_GIVEN = {
    "es_catalan": {"M": ["Jordi", "Josep", "Joan", "Marc", "Pau", "Pol", "Oriol", "Arnau", "Xavier", "Albert", "Jaume", "Martí"],
                   "F": ["Montserrat", "Núria", "Laia", "Mireia", "Anna", "Gemma", "Meritxell", "Neus", "Roser", "Carme", "Ariadna", "Júlia"]},
    "es_galician": {"M": ["Xoán", "Brais", "Iago", "Antón", "Xabier", "Martiño", "Uxío", "Roi"],
                    "F": ["Uxía", "Antía", "Iria", "Sabela", "Xiana", "Noa", "Aldara", "Lúa"]},
    "es_basque": {"M": ["Iker", "Aitor", "Unai", "Asier", "Mikel", "Jon", "Ander", "Iñaki", "Gorka", "Koldo"],
                  "F": ["Ainhoa", "Leire", "Nerea", "Amaia", "Itziar", "Maialen", "Ane", "Irati", "Garazi", "Miren", "Edurne", "Arantxa"]},
}
REGIONAL_SURNAMES = {  # INE 2025 top-50 by province of birth, names not in the national top 100
    "es_catalan": ["Puig", "Vila", "Soler", "Serra", "Martí", "Roca", "Font", "Pons", "Mas", "Riera", "Bosch", "Pujol", "Roig", "Sala", "Coll", "Casas"],
    "es_galician": ["Otero", "Varela", "Rey", "Souto", "Piñeiro", "Barreiro", "Seoane", "Freire", "Fraga", "Lema", "Pereira", "Lago", "Pazos", "Caamaño", "Mosquera", "Couto"],
    "es_basque": ["Etxeberria", "Aguirre", "Garmendia", "Larrañaga", "Zabala", "Urrutia", "Arrieta", "Uriarte", "Bilbao", "Mendizábal", "Aramburu", "Olaizola", "Jáuregui", "Goikoetxea"],
}
FOREIGN_NAMES = {  # (given M, given F, surnames). Two-surname rule: latam keeps two; others see SECOND_SURNAME_POLICY
    "latam": (["Carlos", "Luis", "José Luis", "Jesús", "Andrés", "Juan David", "Luis Fernando", "Miguel Ángel", "Jhon", "Santiago", "Sebastián", "Kevin"],
              ["María Fernanda", "Daniela", "Valentina", "Mariana", "Gabriela", "Andreína", "Paola", "Carolina", "Yesenia", "Luz Marina", "Ana Lucía", "Camila"],
              ["Rodríguez", "González", "Pérez", "Hernández", "Ramírez", "Rojas", "Castillo", "Mendoza", "Quispe", "Vargas", "Chávez", "Paredes", "Zambrano", "Contreras", "Barrios", "Guzmán", "Salazar", "Cárdenas"]),
    "en": (["Oliver", "James", "Jack", "Harry", "George", "Thomas", "William", "Daniel", "Michael", "Ryan", "Liam", "Sean"],
           ["Olivia", "Amelia", "Emily", "Sophie", "Charlotte", "Hannah", "Grace", "Jessica", "Sarah", "Emma", "Aoife", "Megan"],
           ["Smith", "Jones", "Williams", "Taylor", "Brown", "Davies", "Evans", "Wilson", "Thomas", "Johnson", "Roberts", "Walker", "Wright", "Hughes", "Murphy", "O'Brien", "Kelly", "Collins"]),
    "fr": (["Louis", "Hugo", "Julien", "Thomas", "Nicolas"], ["Camille", "Chloé", "Léa", "Manon", "Julie"], ["Martin", "Bernard", "Dubois", "Durand", "Lefebvre", "Moreau", "Laurent"]),
    "it": (["Marco", "Luca", "Alessandro", "Matteo", "Giuseppe"], ["Giulia", "Francesca", "Chiara", "Sara", "Martina"], ["Rossi", "Russo", "Ferrari", "Esposito", "Bianchi", "Romano", "Colombo"]),
    "de": (["Lukas", "Felix", "Jonas", "Maximilian"], ["Anna", "Lena", "Laura", "Julia"], ["Müller", "Schmidt", "Schneider", "Fischer", "Weber", "Wagner"]),
    "pt": (["João", "Pedro", "Tiago", "Rui"], ["Ana", "Beatriz", "Inês", "Mariana"], ["Silva", "Santos", "Ferreira", "Pereira", "Oliveira", "Costa"]),
    "ro": (["Andrei", "Alexandru", "Ionuț", "Mihai", "Florin", "Gabriel"], ["Maria", "Elena", "Ioana", "Andreea", "Mihaela", "Alina"], ["Popescu", "Popa", "Pop", "Radu", "Ionescu", "Dumitru", "Stan", "Stoica"]),
    "ua": (["Oleksandr", "Andriy", "Dmytro", "Serhiy"], ["Olena", "Iryna", "Kateryna", "Oksana"], ["Kovalenko", "Shevchenko", "Bondarenko", "Melnyk", "Tkachenko"]),
    "maghreb": (["Mohamed", "Youssef", "Ahmed", "Said", "Karim"], ["Fatima", "Khadija", "Salma", "Nadia", "Amina"], ["El Amrani", "Benali", "El Idrissi", "Alaoui", "Bennani", "Ouali"]),
    "china": (["Wei", "Jun", "Hao", "Ming", "Lei"], ["Mei", "Li Na", "Xin", "Yan", "Hui"], ["Wang", "Li", "Zhang", "Liu", "Chen", "Zhou"]),
}

# ── Identity documents ───────────────────────────────────────────────────────────────────────
DNI_LETTERS = "TRWAGMYFPDXBNJZSQVHLCKE"      # same table as backend/app/clinic.py:29

def dni(number: int) -> str:
    """8 digits zero-padded + check letter. Realistic numbers: 1_000_000..79_999_999."""
    return f"{number:08d}{DNI_LETTERS[number % 23]}"

def nie(prefix: str, number: int) -> str:
    """X/Y/Z + 7 digits + letter; the prefix counts as 0/1/2 for the check."""
    return f"{prefix}{number:07d}{DNI_LETTERS[int(str('XYZ'.index(prefix)) + f'{number:07d}') % 23]}"

DNI_NUMBER_RANGE = (1_000_000, 79_999_999)  # ~11% get a leading zero (01xxxxxx..09xxxxxx): a good read-back test
NIE_PREFIX = {"X": 0.35, "Y": 0.45, "Z": 0.20}  # X issued up to 2008 (long-settled), Y 2008-~2021, Z recent

# ── Phones (9 national digits, no prefix) ─────────────────────────────────────────────────────
MOBILE_FIRST_DIGITS = {"6": 0.88, "71": 0.03, "72": 0.03, "73": 0.03, "74": 0.03}  # 7x mobile range since 2011 (CNMC)
MOBILE_7X_SHARE_BY_AGE = {"<40": 0.16, "40-64": 0.10, "65+": 0.03}               # newer lines skew young
LANDLINE_PRIMARY_SHARE = {"65-79": 0.15, "80+": 0.40, "other_adults": 0.02}       # landline as the only/primary phone
LANDLINE_PREFIX_BY_SITE = {"centro": ["915", "913", "914"], "norte": ["913", "914", "915"], "sur": ["916"]}  # + 6 digits; Getafe is 91 6xx

# ── Email: RFC 2606 reserved domains only, so an auto-sent confirmation never reaches a person ─
EMAIL_ON_FILE = {"0-13": 0.70, "14-17": 0.45, "18-44": 0.85, "45-64": 0.75, "65-79": 0.45, "80+": 0.15}  # children: guardian's address
EMAIL_DOMAINS = {"example.com": 0.6, "example.org": 0.25, "example.net": 0.15}  # RFC 2606 reserved; never gmail/hotmail
EMAIL_LOCAL_PATTERNS = [  # (pattern, weight)
    ("{given}.{surname1}", 0.30), ("{given}{surname1}{yy}", 0.25), ("{given}.{surname1}.{surname2}", 0.15),
    ("{g1}{surname1}{surname2}", 0.10), ("{given}_{surname1}{nn}", 0.10), ("{surname1}.{given}", 0.10),
]  # ascii-fold, lowercase; yy = birth year 2 digits, nn = 1-99

# ── Insurance (catalogue plan ids) ───────────────────────────────────────────────────────────
INSURER_BASE = {  # adults, es_general; Madrid-weighted from ICEA 2025 premiums + a self-pay share
    "adeslas": 0.22, "sanitas": 0.20, "privado": 0.16, "asisa": 0.11, "dkv": 0.08,
    "mapfre": 0.08, "axa": 0.05, "caser": 0.04, "cigna": 0.04, "nueva_mutua": 0.02,
}
assert abs(sum(INSURER_BASE.values()) - 1) < 1e-9
INSURER_MULTIPLIERS = {  # multiply then renormalise
    "age_65+": {"asisa": 1.5, "adeslas": 1.3, "dkv": 0.6, "cigna": 0.3, "axa": 0.6},   # MUFACE retirees; DKV left MUFACE in 2025
    "home_sur": {"asisa": 0.1, "adeslas": 1.3, "mapfre": 1.3, "caser": 1.3, "nueva_mutua": 1.5, "cigna": 0.5},  # ASISA not valid at Sur
    "home_norte": {"nueva_mutua": 0.0, "sanitas": 1.3, "dkv": 1.3, "axa": 1.4, "cigna": 1.6, "caser": 0.7},    # NMS not valid at Norte
    "expat_en": {"cigna": 6.0, "axa": 4.0, "sanitas": 1.3, "asisa": 0.2, "nueva_mutua": 0.0, "caser": 0.3},
    "expat_eu": {"cigna": 3.0, "axa": 3.0, "dkv": 1.5, "nueva_mutua": 0.0},
    "latam_nie": {"privado": 1.6, "asisa": 0.5, "cigna": 0.2, "nueva_mutua": 0.2},
}
CHILD_INSURER = {"same_as_guardian": 0.92, "privado": 0.05, "other": 0.03}   # family policies

# ── Time-of-day demand (relative weight a cell is booked; free cells are the complement) ───────
TOD_MORNING = {"08:00": 1.25, "08:30": 1.25, "09:00": 1.30, "09:30": 1.25, "10:00": 1.15, "10:30": 1.00,
               "11:00": 0.90, "11:30": 0.85, "12:00": 0.90, "12:30": 1.00, "13:00": 1.10, "13:30": 1.15}
TOD_AFTERNOON = {"14:00": 0.90, "15:00": 1.05, "16:00": 1.10, "16:30": 1.20, "17:00": 1.10,  # physio to 17:00, ortho Fri to 18:00
                 "18:00": 1.30, "19:00": 1.30}                                              # derm Centro to 20:00
TOD_PAEDIATRICS = {"09:00": 1.30, "10:30": 0.85, "11:30": 0.80, "13:00": 1.20, "13:30": 1.25}  # school hours: extremes wanted

# ── Appointment-type mix (share of each specialty's bookings made by never-seen patients) ──────
NEW_PATIENT_SHARE = {"general_practice": 0.15, "paediatrics": 0.12, "dermatology": 0.20,
                     "orthopaedics": 0.25, "gynaecology": 0.10, "physiotherapy": 0.10}
TYPE_FOR = {  # (specialty, has_visited_before) -> appointment_type_id, minutes (clinic.json:1583-1729)
    ("general_practice", False): ("first_visit", 30), ("general_practice", True): ("review", 15),
    ("paediatrics", False): ("paediatric_first_visit", 30), ("paediatrics", True): ("paediatric_review", 30),
    ("dermatology", False): ("dermatology_first_visit", 30), ("dermatology", True): ("dermatology_review", 15),
    ("orthopaedics", False): ("orthopaedic_first_visit", 45), ("orthopaedics", True): ("orthopaedic_review", 15),
    ("gynaecology", False): ("first_visit", 30), ("gynaecology", True): ("gynaecology_review", 30),
    ("physiotherapy", False): ("physiotherapy_assessment", 45), ("physiotherapy", True): ("physiotherapy_session", 30),
}

LEAD_DAYS = {  # updated_at = start_time - lead (float epoch); median, p90
    "general_practice": (3, 10), "paediatrics": (4, 14), "dermatology": (24, 45),
    "orthopaedics": (10, 25), "gynaecology": (21, 60), "physiotherapy": (7, 21),
}


# ══ CALENDAR ════════════════════════════════════════════════════════════════════════════════
# Public holidays. scope: "all" closes every site; "madrid" closes the two Madrid-city sites
# (centro, norte); "getafe" closes Arenal Sur (Getafe).
# 2025 and 2026 are the published calendars (Comunidad de Madrid decrees, madrid.es, Ayto. Getafe).
# 2027 is PROVISIONAL: the regional decree was not out when this was written, so it holds the
# fixed-date national days plus Madrid's usual Jueves Santo; Getafe follows its own pattern
# (Ascension Thursday and Whit Monday, true in 2025 and 2026). Sunday holidays are left out: no
# site opens on Sundays.
HOLIDAYS = [
    (date(2025, 1, 1), "all", "Año Nuevo"),
    (date(2025, 1, 6), "all", "Epifanía del Señor"),
    (date(2025, 4, 17), "all", "Jueves Santo"),
    (date(2025, 4, 18), "all", "Viernes Santo"),
    (date(2025, 5, 1), "all", "Fiesta del Trabajo"),
    (date(2025, 5, 2), "all", "Fiesta de la Comunidad de Madrid"),
    (date(2025, 5, 15), "madrid", "San Isidro (Madrid)"),
    (date(2025, 5, 29), "getafe", "Fiestas de Getafe"),
    (date(2025, 6, 9), "getafe", "Fiestas de Getafe"),
    (date(2025, 7, 25), "all", "Santiago Apóstol"),
    (date(2025, 8, 15), "all", "Asunción de la Virgen"),
    (date(2025, 11, 1), "all", "Todos los Santos"),
    (date(2025, 11, 10), "madrid", "La Almudena (Madrid)"),
    (date(2025, 12, 6), "all", "Día de la Constitución"),
    (date(2025, 12, 8), "all", "Inmaculada Concepción"),
    (date(2025, 12, 25), "all", "Navidad"),
    (date(2026, 1, 1), "all", "Año Nuevo"),
    (date(2026, 1, 6), "all", "Epifanía del Señor"),
    (date(2026, 4, 2), "all", "Jueves Santo"),
    (date(2026, 4, 3), "all", "Viernes Santo"),
    (date(2026, 5, 1), "all", "Fiesta del Trabajo"),
    (date(2026, 5, 2), "all", "Fiesta de la Comunidad de Madrid"),
    (date(2026, 5, 14), "getafe", "Fiestas de Getafe"),
    (date(2026, 5, 15), "madrid", "San Isidro (Madrid)"),
    (date(2026, 5, 25), "getafe", "Fiestas de Getafe"),
    (date(2026, 8, 15), "all", "Asunción de la Virgen"),
    (date(2026, 10, 12), "all", "Fiesta Nacional de España"),
    (date(2026, 11, 2), "all", "Todos los Santos"),
    (date(2026, 11, 9), "madrid", "La Almudena (Madrid)"),
    (date(2026, 12, 7), "all", "Día de la Constitución"),
    (date(2026, 12, 8), "all", "Inmaculada Concepción"),
    (date(2026, 12, 25), "all", "Navidad"),
    (date(2027, 1, 1), "all", "Año Nuevo"),
    (date(2027, 1, 6), "all", "Epifanía del Señor"),
    (date(2027, 3, 25), "all", "Jueves Santo"),
    (date(2027, 3, 26), "all", "Viernes Santo"),
    (date(2027, 5, 1), "all", "Fiesta del Trabajo"),
    (date(2027, 5, 6), "getafe", "Fiestas de Getafe"),
    (date(2027, 5, 15), "madrid", "San Isidro (Madrid)"),
    (date(2027, 5, 17), "getafe", "Fiestas de Getafe"),
    (date(2027, 10, 12), "all", "Fiesta Nacional de España"),
    (date(2027, 11, 1), "all", "Todos los Santos"),
    (date(2027, 11, 9), "madrid", "La Almudena (Madrid)"),
    (date(2027, 12, 6), "all", "Día de la Constitución"),
    (date(2027, 12, 8), "all", "Inmaculada Concepción"),
    (date(2027, 12, 25), "all", "Navidad"),
]
HOLIDAY_SITES = {"all": (None,), "madrid": ("centro", "norte"), "getafe": ("sur",)}
CALENDAR_FIRST = date(2025, 1, 1)    # the seed refuses a window outside the table
CALENDAR_LAST = date(2027, 12, 31)

# Real 2026 congresses. When one falls inside the dense window it is used as is; otherwise the
# seed places a generic congress at the same offset from the anchor (see seed_clinic.absences).
CONGRESSES = {
    "PR05": [(date(2026, 9, 30), date(2026, 10, 2), "congress (EADV, Vienna)")],
    "PR10": [(date(2026, 9, 30), date(2026, 10, 2), "congress (SECOT, Córdoba)")],
    "PR01": [(date(2026, 10, 7), date(2026, 10, 10), "congress (SEMERGEN, Santiago)")],
}
# Summer leave as ISO weeks (Monday of the first, Friday of the last), the 2026 plan from
# realism.md §5.2 that keeps >=2 GPs, >=1 paediatrician, dermatologist and orthopaedist on duty.
SUMMER_LEAVE_WEEKS = {
    "PR01": (31, 33), "PR11": (31, 33), "PR05": (31, 33), "PR04": (32, 34), "PR06": (32, 34),
    "PR02": (33, 35), "PR09": (33, 35), "PR03": (34, 36), "PR12": (34, 36), "PR08": (35, 36),
    "PR10": (35, 36), "PR07": (36, 37),
}
CHRISTMAS_LEAVE = ("PR03", "PR08")   # 28 Dec - 4 Jan

# ══ OCCUPANCY (booked cells / open cells) ═══════════════════════════════════════════════════
# Dense weeks 1-4 after the anchor (realism.md §5.3 folded onto anchor-relative weeks). Tail weeks
# fall linearly from TAIL_OCCUPANCY[0] to TAIL_OCCUPANCY[1]. All of these are ceilings: with few
# patients the seed scales them down rather than handing anyone an absurd diary.
FUTURE_OCCUPANCY = {
    "general_practice": (0.92, 0.82, 0.75, 0.62),
    "paediatrics":      (0.92, 0.85, 0.75, 0.65),
    "dermatology":      (1.00, 0.99, 0.97, 0.75),
    "orthopaedics":     (0.90, 0.85, 0.85, 0.65),
    "gynaecology":      (0.93, 0.88, 0.80, 0.70),
    "physiotherapy":    (0.95, 0.90, 0.85, 0.80),
}
TAIL_OCCUPANCY = (0.55, 0.25)
TODAY_OCCUPANCY = 0.95
PAST_OCCUPANCY = [(10, 0.88), (24, 0.80), (56, 0.70)]   # (days before the anchor, occupancy)
AUGUST_FACTOR = 0.85
FULL_PROVIDER = "PR06"   # booked solid for the dense window (demo guarantee): Dr. Emilio Iglesia

# Upcoming appointments a patient is willing to hold ("episodes": a physiotherapy course is one).
FUTURE_BUDGET = {0: 0.30, 1: 0.42, 2: 0.18, 3: 0.10}
PAST_BUDGET = {0: 0.35, 1: 0.35, 2: 0.18, 3: 0.12}         # rows in the 8-week history window
OLD_VISITS = {1: 0.45, 2: 0.30, 3: 0.15, 4: 0.10}           # earlier history of seen patients
MAX_UPCOMING = 8
MAX_UPCOMING_PER_SPECIALTY = {"physiotherapy": 8, "paediatrics": 2, "gynaecology": 2, "orthopaedics": 2}
HAS_VISITED_BEFORE = 0.83
RECENT_FIRST_SHARE = 0.12   # seen patients whose first visit falls in the 8-week history window
PAST_STATUS = {"attended": 0.86, "no_show": 0.05, "cancelled": 0.09}
FUTURE_CANCELLED_SHARE = 0.03
PENDING_REFERRAL = {"dermatology": 0.03, "physiotherapy": 0.02}   # adults with a referral, no booking
PRIVATE_PAY = {"gynaecology": ("adeslas", "caser"), "dermatology": ("mapfre", "caser")}
PRIVATE_PAY_SHARE = 0.20
PHYSIO_SESSIONS = (6, 10)
PHYSIO_PAIRS = ((0, 2), (1, 3))   # Mon/Wed, Tue/Thu

# ══ NOTES (the only free text the model sees) ═══════════════════════════════════════════════
LANGUAGE_NOTE = {
    "ca": "Prefers to speak Catalan.", "gl": "Prefers to speak Galician.", "eu": "Prefers to speak Basque.",
    "en": "Speaks English; little Spanish.", "fr": "Speaks French; basic Spanish.",
    "it": "Speaks Italian; basic Spanish.", "de": "Speaks German; basic Spanish.",
    "pt": "Speaks Portuguese; understands Spanish.", "ro": "Speaks Romanian; basic Spanish.",
    "uk": "Speaks Ukrainian; basic Spanish.", "ar": "Speaks Arabic; basic Spanish.",
    "zh": "Speaks Mandarin; basic Spanish.",
}
# Caller-handling hints in the platform's own words (the recovered charts use the same set).
GENERIC_HINTS = [
    "Will ask what to bring and how early to arrive.",
    "Will ask what is available soonest before anything else.",
    "Asks whether they can be seen outside working hours.",
    "Read the appointment back before ending the call; they check it and will not ask.",
    "Repeats a time back as morning or afternoon; confirm the exact hour.",
    "Talks over the top of you; confirm each detail on its own.",
    "Will ask which entrance and which floor.",
    "Rings from work; keep it short and confirm once.",
    "Mishears numbers said at speed -- say the identifier back digit by digit.",
    "On speakerphone; expect a lag and some noise.",
    "Says the identifier as a run of digits; read it back grouped.",
    "Asks for a reference number at the end of the call.",
    "Spells their surname unprompted, and it is worth taking the spelling.",
    "Goes quiet while they check a diary; the pause is not a dropped line.",
    "Gets the date right and the weekday wrong; say both back.",
    "Will ask what it costs under their policy before agreeing to anything.",
    "Calling from somewhere busy; expect to repeat the date.",
    "Asks whether an appointment can be moved once it is made.",
    "Volunteers nothing; ask for each detail directly rather than waiting.",
    "Answers before the question is finished; check they heard the whole of it.",
    "Writes it down while you wait; leave a pause after the date.",
    "Corrects themselves mid-sentence -- take the last answer, not the first.",
    "Prefers to be addressed by surname.",
]
CHILD_HINTS = [
    "A parent is always the caller; the child never rings.",
    "The caller gives their own name first; the patient is the child.",
    "The parent has the child's details to hand but not always their own.",
    "A parent who asks whether the child needs to bring anything.",
    "The child is audible in the background; expect to repeat things.",
]
ELDERLY_HINTS = [
    "Hard of hearing; speak slowly and confirm each detail.",
    "Uses a walking frame; prefers late-morning appointments.",
    "Slow to settle into the call; give them a moment before the first question.",
    "Does not use email; everything has to be confirmed on the call itself.",
]
HINT_SHARE = 0.35

# ══ PEOPLE THAT MUST (NOT) EXIST ════════════════════════════════════════════════════════════
# Registration personas (they must stay unknown so REGISTER is right), the Studio new-patient
# persona, a deliberately misread DNI from a case, and the placeholder ids/phones the tests use as
# "nobody".
FORBIDDEN_NATIONAL_IDS = {"18921027P", "X0500252W", "50454876Y", "31426012P", "99887766P",
                          "94789619H", "12345678Z", "87654321X"}
FORBIDDEN_PHONES = {"699887766", "756960522", "783869132", "797574941", "792919982",
                    "731169717", "612345678", "600123456"}
FORBIDDEN_NAMES = {"Joaquín González Ortega", "Elizabeth Jones Evans", "Natalia Muñoz González",
                   "Sergio Martínez Ramírez", "Rubén Ortega Salas", "Prueba Sistema Temporal"}

# Demo personas (app/demo/scenarios.py): identity fields that must match exactly.
DEMO_PERSONAS: dict[str, dict[str, str]] = {
    "P00001": {"given_name": "Josefa", "first_surname": "Domínguez", "second_surname": "Navarro",
               "national_id": "48064716Y", "phone": "711330529", "date_of_birth": "2001-09-19",
               "insurer": "mapfre"},
    "P00003": {"given_name": "Lucas", "first_surname": "Jones", "second_surname": "Smith",
               "national_id": "Z5361712A", "phone": "757036760", "date_of_birth": "1980-04-04",
               "insurer": "sanitas"},
    "P00005": {"given_name": "Ignacio", "first_surname": "Vázquez", "second_surname": "Moreno",
               "national_id": "65699248R", "phone": "731169716", "date_of_birth": "1939-12-09",
               "insurer": "cigna"},
}
IGNACIO_APPOINTMENT: dict[str, Any] = {"appointment_id": "A001101", "patient_id": "P00005", "provider_id": "PR05",
                       "location_id": "sur", "appointment_type_id": "dermatology_review",
                       "time": "12:00", "weekday": 1, "min_days_ahead": 14, "policy_id": "cigna"}

# The adversarial case's protected person: someone real for the privacy check to protect.
AMELIA_WILLIAMS: dict[str, Any] = {"given_name": "Amelia", "first_surname": "Williams", "second_surname": "Williams",
                   "national_id": "X8148593S", "phone": "607034486", "sex": "F",
                   "date_of_birth": "1979-06-02", "insurer": "sanitas", "home": "centro",
                   "language": "en"}

# The "caller matching four people" cluster: P00358 (recovered) plus these three.
ROSARIO_SANZ: list[dict[str, Any]] = [
    {"key": "rosario_moreno", "given_name": "María del Rosario", "first_surname": "Sanz",
     "second_surname": "Moreno", "sex": "F", "date_of_birth": "1951-11-03", "insurer": "adeslas",
     "home": "centro", "phone_kind": "landline", "known_as": "Charo"},
    {"key": "rosario_gomez", "given_name": "Rosario", "first_surname": "Sanz", "second_surname": "Gómez",
     "sex": "F", "date_of_birth": "1962-06-17", "insurer": "sanitas", "home": "norte"},
    {"key": "rosario_martin", "given_name": "Rosario", "first_surname": "Martín", "second_surname": "Sanz",
     "sex": "F", "date_of_birth": "1987-02-09", "insurer": "mapfre", "home": "sur",
     "relatives": [("rosario_moreno", "Mother", "Daughter")]},
]

# Hand-shaped families (realism.md §4.11). Children share the phone of the member marked
# "phone_owner". "relatives": (other member key, what the other is to this one, what this one is
# to the other). "dob": "turns_14" = 14th birthday 13 days after the anchor.
FAMILIES: list[dict[str, Any]] = [
    {"site": "centro", "insurer": "sanitas", "members": [
        {"key": "laura", "given_name": "Laura", "first_surname": "Sánchez", "second_surname": "Moreno", "sex": "F", "date_of_birth": "1986-05-12", "phone_owner": True},
        {"key": "javier", "given_name": "Javier", "first_surname": "Ruiz", "second_surname": "Castillo", "sex": "M", "date_of_birth": "1984-11-30", "relatives": [("laura", "Partner", "Partner")]},
        {"key": "hugo", "given_name": "Hugo", "first_surname": "Ruiz", "second_surname": "Sánchez", "sex": "M", "date_of_birth": "2017-03-02", "relatives": [("laura", "Mother", "Son"), ("javier", "Father", "Son")]},
        {"key": "lucia", "given_name": "Lucía", "first_surname": "Ruiz", "second_surname": "Sánchez", "sex": "F", "date_of_birth": "2020-10-15", "relatives": [("laura", "Mother", "Daughter"), ("javier", "Father", "Daughter")]},
        {"key": "martina", "given_name": "Martina", "first_surname": "Ruiz", "second_surname": "Sánchez", "sex": "F", "date_of_birth": "2024-06-20", "relatives": [("laura", "Mother", "Daughter"), ("javier", "Father", "Daughter")]},
    ]},
    {"site": "norte", "insurer": "dkv", "members": [
        {"key": "ana", "given_name": "Ana", "first_surname": "Herrera", "second_surname": "Vidal", "sex": "F", "date_of_birth": "1988-01-22", "phone_owner": True},
        {"key": "david", "given_name": "David", "first_surname": "Gómez", "second_surname": "Ortega", "sex": "M", "date_of_birth": "1985-07-09", "relatives": [("ana", "Partner", "Partner")]},
        {"key": "mateo", "given_name": "Mateo", "first_surname": "Gómez", "second_surname": "Herrera", "sex": "M", "date_of_birth": "2021-03-08", "relatives": [("ana", "Mother", "Son"), ("david", "Father", "Son")], "note": "Twin of Leo; same date of birth and phone -- the given name is the only difference."},
        {"key": "leo", "given_name": "Leo", "first_surname": "Gómez", "second_surname": "Herrera", "sex": "M", "date_of_birth": "2021-03-08", "relatives": [("ana", "Mother", "Son"), ("david", "Father", "Son")], "note": "Twin of Mateo; same date of birth and phone -- the given name is the only difference."},
    ]},
    {"site": "sur", "insurer": "adeslas", "members": [
        {"key": "paco", "given_name": "Francisco", "first_surname": "Muñoz", "second_surname": "Díaz", "sex": "M", "date_of_birth": "1941-02-17", "phone_kind": "landline", "no_email": True, "known_as": "Paco", "note": "Hard of hearing; speak slowly and confirm each detail."},
        {"key": "majo", "given_name": "María José", "first_surname": "Muñoz", "second_surname": "Pérez", "sex": "F", "date_of_birth": "1969-08-04", "relatives": [("paco", "Father", "Daughter")], "carer_of": "paco"},
    ]},
    {"site": "norte", "insurer": "cigna", "language": "en", "members": [
        {"key": "emily", "given_name": "Emily", "first_surname": "Brown", "second_surname": "Taylor", "sex": "F", "date_of_birth": "1984-09-14", "phone_owner": True, "nie": "Y"},
        {"key": "tom", "given_name": "Tom", "first_surname": "Carter", "second_surname": "Wilson", "sex": "M", "date_of_birth": "1982-04-03", "nie": "Y", "relatives": [("emily", "Partner", "Partner")]},
        {"key": "oliver", "given_name": "Oliver", "first_surname": "Carter", "second_surname": "Brown", "sex": "M", "date_of_birth": "2016-12-01", "nie": "Y", "relatives": [("emily", "Mother", "Son"), ("tom", "Father", "Son")]},
        {"key": "sophie", "given_name": "Sophie", "first_surname": "Carter", "second_surname": "Brown", "sex": "F", "date_of_birth": "2019-05-27", "nie": "Y", "relatives": [("emily", "Mother", "Daughter"), ("tom", "Father", "Daughter")]},
    ]},
    {"site": "sur", "insurer": "mapfre", "members": [
        {"key": "yolanda", "given_name": "Yolanda", "first_surname": "Castillo", "second_surname": "Rubio", "sex": "F", "date_of_birth": "1979-03-15", "phone_owner": True},
        {"key": "adrian", "given_name": "Adrián", "first_surname": "Pérez", "second_surname": "Castillo", "sex": "M", "date_of_birth": "turns_14", "relatives": [("yolanda", "Mother", "Son")]},
        {"key": "noa", "given_name": "Noa", "first_surname": "Pérez", "second_surname": "Castillo", "sex": "F", "date_of_birth": "2018-02-11", "relatives": [("yolanda", "Mother", "Daughter")]},
    ]},
    {"site": "norte", "insurer": "sanitas", "language": "ca", "members": [
        {"key": "montse", "given_name": "Montserrat", "first_surname": "Vila", "second_surname": "Roca", "sex": "F", "date_of_birth": "1977-01-19", "phone_owner": True},
        {"key": "jordi", "given_name": "Jordi", "first_surname": "Puig", "second_surname": "Soler", "sex": "M", "date_of_birth": "1975-06-02", "relatives": [("montse", "Partner", "Partner")]},
        {"key": "pau", "given_name": "Pau", "first_surname": "Puig", "second_surname": "Vila", "sex": "M", "date_of_birth": "2014-09-30", "relatives": [("montse", "Mother", "Son"), ("jordi", "Father", "Son")]},
    ]},
    {"site": "centro", "insurer": "privado", "members": [
        {"key": "mafe", "given_name": "María Fernanda", "first_surname": "Rojas", "second_surname": "Contreras", "sex": "F", "date_of_birth": "1990-12-05", "phone_owner": True, "nie": "Z"},
        {"key": "valentina", "given_name": "Valentina", "first_surname": "Salazar", "second_surname": "Rojas", "sex": "F", "date_of_birth": "2019-08-21", "nie": "Z", "relatives": [("mafe", "Mother", "Daughter")]},
    ]},
    {"site": "centro", "insurer": "asisa", "members": [
        {"key": "antonio_sr", "given_name": "Antonio", "first_surname": "Pérez", "second_surname": "Gómez", "sex": "M", "date_of_birth": "1950-04-28", "phone_kind": "landline", "note": "Shares his name with his son Antonio Pérez Ruiz; check the second surname and date of birth."},
        {"key": "antonio_jr", "given_name": "Antonio", "first_surname": "Pérez", "second_surname": "Ruiz", "sex": "M", "date_of_birth": "1978-12-12", "insurer": "sanitas", "relatives": [("antonio_sr", "Father", "Son")]},
    ]},
]

# Family links among the recovered case identities (from the platform's case personas):
# (patient, relative, what the relative is to the patient, what the patient is to the relative).
RECOVERED_LINKS = [
    ("P00005", "P00196", "Daughter", "Father"),
    ("P00009", "P00293", "Mother", "Daughter"),
    ("P00009", "P00301", "Father", "Daughter"),
    ("P00020", "P00402", "Grandmother", "Grandson"),
    ("P00023", "P00100", "Daughter", "Mother"),
    ("P00038", "P00330", "Father", "Daughter"),
]
