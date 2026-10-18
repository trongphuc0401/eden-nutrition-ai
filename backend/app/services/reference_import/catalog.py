"""Static catalogs that map the workbook's headers/labels onto stable codes."""
from __future__ import annotations

# (column index in Data_Ingredients, code, name_vi, name_en, unit, group, is_core)
_N = [
    (9, "water_g", "Nước", "Water", "g", "macro", True),
    (10, "energy_kcal", "Năng lượng", "Energy", "kcal", "macro", True),
    (11, "protein_g", "Protein", "Protein", "g", "macro", True),
    (12, "fat_g", "Chất béo (lipid)", "Total fat", "g", "macro", True),
    (13, "carbohydrate_g", "Glucid (carbohydrate)", "Carbohydrate", "g", "macro", True),
    (14, "fiber_g", "Chất xơ", "Dietary fiber", "g", "macro", True),
    (15, "ash_g", "Tro", "Ash", "g", "macro", False),
    (16, "galactose_g", "Galactose", "Galactose", "g", "sugar", False),
    (17, "maltose_g", "Maltose", "Maltose", "g", "sugar", False),
    (18, "lactose_g", "Lactose", "Lactose", "g", "sugar", False),
    (19, "fructose_g", "Fructose", "Fructose", "g", "sugar", False),
    (20, "glucose_g", "Glucose", "Glucose", "g", "sugar", False),
    (21, "sucrose_g", "Sucrose", "Sucrose", "g", "sugar", False),
    (22, "total_sugar_g", "Đường tổng số", "Total sugars", "g", "sugar", True),
    (23, "calcium_mg", "Canxi", "Calcium", "mg", "mineral", True),
    (24, "iron_mg", "Sắt", "Iron", "mg", "mineral", True),
    (25, "magnesium_mg", "Magie", "Magnesium", "mg", "mineral", False),
    (26, "manganese_mg", "Mangan", "Manganese", "mg", "mineral", False),
    (27, "phosphorus_mg", "Phospho", "Phosphorus", "mg", "mineral", False),
    (28, "sodium_mg", "Natri", "Sodium", "mg", "mineral", True),
    (29, "zinc_mg", "Kẽm", "Zinc", "mg", "mineral", False),
    (30, "copper_ug", "Đồng", "Copper", "ug", "mineral", False),
    (31, "selenium_ug", "Selen", "Selenium", "ug", "mineral", False),
    (32, "potassium_mg", "Kali", "Potassium", "mg", "mineral", True),
    (33, "vitamin_c_mg", "Vitamin C", "Vitamin C", "mg", "vitamin", True),
    (34, "vitamin_b1_mg", "Vitamin B1", "Thiamin", "mg", "vitamin", False),
    (35, "vitamin_b2_mg", "Vitamin B2", "Riboflavin", "mg", "vitamin", False),
    (36, "niacin_mg", "Vitamin PP (B3, niacin)", "Niacin", "mg", "vitamin", False),
    (37, "vitamin_b5_mg", "Vitamin B5", "Pantothenic acid", "mg", "vitamin", False),
    (38, "vitamin_b6_mg", "Vitamin B6", "Pyridoxine", "mg", "vitamin", False),
    (39, "folate_ug", "Folat", "Folate", "ug", "vitamin", False),
    (40, "vitamin_b9_ug", "Vitamin B9 (cột trùng với Folat)", "Vitamin B9", "ug", "vitamin", False),
    (41, "biotin_ug", "Vitamin H (biotin)", "Biotin", "ug", "vitamin", False),
    (42, "vitamin_b12_ug", "Vitamin B12", "Cobalamin", "ug", "vitamin", False),
    (43, "vitamin_a_ug", "Vitamin A", "Vitamin A", "ug", "vitamin", False),
    (44, "vitamin_d_ug", "Vitamin D", "Vitamin D", "ug", "vitamin", False),
    (45, "vitamin_e_mg", "Vitamin E", "Vitamin E", "mg", "vitamin", False),
    (46, "vitamin_k_ug", "Vitamin K", "Vitamin K", "ug", "vitamin", False),
    (47, "beta_carotene_ug", "Beta-caroten", "Beta-carotene", "ug", "carotenoid", False),
    (48, "alpha_carotene_ug", "Alpha-caroten", "Alpha-carotene", "ug", "carotenoid", False),
    (49, "beta_cryptoxanthin_ug", "Beta-cryptoxanthin", "Beta-cryptoxanthin", "ug", "carotenoid", False),
    (50, "lycopene_ug", "Lycopen", "Lycopene", "ug", "carotenoid", False),
    (51, "lutein_zeaxanthin_ug", "Lutein + Zeaxanthin", "Lutein + Zeaxanthin", "ug", "carotenoid", False),
    (52, "purine_mg", "Purin", "Purine", "mg", "other", False),
    (53, "daidzein_mg", "Daidzein", "Daidzein", "mg", "isoflavone", False),
    (54, "genistein_mg", "Genistein", "Genistein", "mg", "isoflavone", False),
    (55, "glycitein_mg", "Glycetin", "Glycitein", "mg", "isoflavone", False),
    (56, "palmitic_g", "Palmitic", "Palmitic acid", "g", "fatty_acid", False),
    (57, "margaric_g", "Margaric", "Margaric acid", "g", "fatty_acid", False),
    (58, "stearic_g", "Stearic", "Stearic acid", "g", "fatty_acid", False),
    (59, "arachidic_g", "Arachidic", "Arachidic acid", "g", "fatty_acid", False),
    (60, "behenic_g", "Behenic", "Behenic acid", "g", "fatty_acid", False),
    (61, "lignoceric_g", "Lignoceric", "Lignoceric acid", "g", "fatty_acid", False),
    (62, "myristoleic_g", "Myristoleic", "Myristoleic acid", "g", "fatty_acid", False),
    (63, "palmitoleic_g", "Palmitoleic", "Palmitoleic acid", "g", "fatty_acid", False),
    (64, "oleic_g", "Oleic", "Oleic acid", "g", "fatty_acid", False),
    (65, "linoleic_g", "Linoleic", "Linoleic acid", "g", "fatty_acid", False),
    (66, "linolenic_g", "Linolenic", "Linolenic acid", "g", "fatty_acid", False),
    (67, "arachidonic_g", "Arachidonic", "Arachidonic acid", "g", "fatty_acid", False),
    (68, "epa_g", "Eicosapentaenoic (EPA)", "EPA", "g", "fatty_acid", False),
    (69, "dha_g", "Docosahexaenoic (DHA)", "DHA", "g", "fatty_acid", False),
    (70, "cholesterol_mg", "Cholesterol", "Cholesterol", "mg", "sterol", False),
    (71, "phytosterol_mg", "Phytosterol", "Phytosterol", "mg", "sterol", False),
    (72, "lysine_mg", "Lysin", "Lysine", "mg", "amino_acid", False),
    (73, "methionine_mg", "Methionin", "Methionine", "mg", "amino_acid", False),
    (74, "tryptophan_mg", "Tryptophan", "Tryptophan", "mg", "amino_acid", False),
    (75, "phenylalanine_mg", "Phenylalanin", "Phenylalanine", "mg", "amino_acid", False),
    (76, "threonine_mg", "Threonin", "Threonine", "mg", "amino_acid", False),
    (77, "valine_mg", "Valin", "Valine", "mg", "amino_acid", False),
    (78, "leucine_mg", "Leucin", "Leucine", "mg", "amino_acid", False),
    (79, "isoleucine_mg", "Isoleucin", "Isoleucine", "mg", "amino_acid", False),
    (80, "arginine_mg", "Arginin", "Arginine", "mg", "amino_acid", False),
    (81, "histidine_mg", "Histidin", "Histidine", "mg", "amino_acid", False),
    (82, "cystine_mg", "Cystin", "Cystine", "mg", "amino_acid", False),
    (83, "tyrosine_mg", "Tyrosin", "Tyrosine", "mg", "amino_acid", False),
    (84, "alanine_mg", "Alanin", "Alanine", "mg", "amino_acid", False),
    (85, "aspartic_acid_mg", "Acid aspartic", "Aspartic acid", "mg", "amino_acid", False),
    (86, "glutamic_acid_mg", "Acid glutamic", "Glutamic acid", "mg", "amino_acid", False),
    (87, "glycine_mg", "Glycin", "Glycine", "mg", "amino_acid", False),
    (88, "proline_mg", "Prolin", "Proline", "mg", "amino_acid", False),
    (89, "serine_mg", "Serin", "Serine", "mg", "amino_acid", False),
]

# Sanity ceiling per 100 g by unit; anything above is treated as corrupted input.
_CEILING = {"g": 100, "kcal": 900, "mg": 50000, "ug": 1_000_000}
_SUGARS = {"galactose_g", "maltose_g", "lactose_g", "fructose_g", "glucose_g", "sucrose_g"}

NUTRIENTS = [
    {
        "col": col, "code": code, "name_vi": vi, "name_en": en, "unit": unit, "group": group,
        "is_core": core, "plausible_max": _CEILING[unit],
        "parent_code": "total_sugar_g" if code in _SUGARS else None,
        "display_order": i,
    }
    for i, (col, code, vi, en, unit, group, core) in enumerate(_N)
]
NUTRIENT_BY_COL = {n["col"]: n for n in NUTRIENTS}
CORE_CODES = tuple(n["code"] for n in NUTRIENTS if n["is_core"])

# Sheet metric name -> (nutrient_code, basis)
THRESHOLD_METRICS = {
    "lipid_g_energy": ("fat_g", "percent_energy"),
    "protein_g_energy": ("protein_g", "percent_energy"),
    "carb_g_energy": ("carbohydrate_g", "percent_energy"),
    "salt_mg": ("sodium_mg", "absolute"),
    "fiber_g": ("fiber_g", "absolute"),
    "energy_kcal_per_serving": ("energy_kcal", "absolute"),
    "energy_kcal": ("energy_kcal", "absolute"),
    "protein_g": ("protein_g", "absolute"),
    "sugar_g": ("total_sugar_g", "absolute"),
    "total_sugar_g": ("total_sugar_g", "absolute"),
}

CATEGORY_MAP = {
    "fruit": "fruit", "vegetable": "vegetable", "protein": "protein", "liquid": "liquid",
    "seed": "seed", "sweetener": "sweetener", "milk": "dairy", "dairy": "dairy",
    "roots and tubers": "roots_tubers", "roots_tubers": "roots_tubers",
}

# Canonical health conditions. keywords_vi matches free-text medical notes;
# ingredient_keywords (accent-free) link ingredients to the condition.
CONDITIONS = {
    "peanut_allergy": ("allergy", "Dị ứng đậu phộng", ["dau phong", "lac"], ["dau phong", "=lạc"]),
    "tree_nut_allergy": ("allergy", "Dị ứng hạt cây", ["hat cay", "hanh nhan", "oc cho", "hat dieu"],
                         ["hanh nhan", "oc cho", "hat dieu", "mac ca", "qua phi", "ho dao", "hat de"]),
    "celery_allergy": ("allergy", "Dị ứng cần tây", ["can tay"], ["can tay"]),
    "soy_allergy": ("allergy", "Dị ứng đậu nành", ["dau nanh", "soy"], ["dau nanh", "soy"]),
    "sesame_allergy": ("allergy", "Dị ứng mè (vừng)", ["me", "vung"], ["=mè", "vung"]),
    "kiwi_allergy": ("allergy", "Dị ứng kiwi", ["kiwi"], ["kiwi"]),
    "milk_allergy": ("allergy", "Dị ứng sữa bò", ["sua", "milk"], ["sua", "whey", "pho mai", "yaourt", "sua chua"]),
    "peach_allergy": ("allergy", "Dị ứng đào", ["dao"], ["=đào"]),
    "pear_allergy": ("allergy", "Dị ứng lê", ["le"], ["=lê"]),
    "apple_allergy": ("allergy", "Dị ứng táo", ["tao"], ["=táo"]),
    "latex_fruit_syndrome": ("allergy", "Hội chứng dị ứng latex-trái cây", ["latex"],
                             ["chuoi", "kiwi", "=bơ", "hat de"]),
    "gastric_ulcer": ("disease", "Viêm loét dạ dày", ["loet da day", "viem da day"], []),
    "gerd": ("disease", "Trào ngược dạ dày thực quản", ["trao nguoc"], []),
    "ibs": ("disease", "Hội chứng ruột kích thích", ["ruot kich thich"], []),
    "nafld": ("disease", "Gan nhiễm mỡ không do rượu", ["gan nhiem mo"], []),
    "hereditary_fructose_intolerance": ("disease", "Không dung nạp fructose di truyền", ["fructose"], ["mat ong"]),
    "kidney_stones": ("disease", "Sỏi thận", ["soi than"], ["rau bina", "cu den", "hanh nhan"]),
    "hypertension": ("disease", "Tăng huyết áp", ["huyet ap"], []),
    "prediabetes": ("disease", "Tiền đái tháo đường", ["tien dai thao duong", "duong huyet"], []),
    "diabetes": ("disease", "Đái tháo đường", ["dai thao duong", "tieu duong"], []),
}

# Disease rows: slug of the sheet's condition label -> canonical code.
DISEASE_LABELS = {
    "gastric-ulcer_disease": "gastric_ulcer",
    "gastroesophageal-reflux_disease": "gerd",
    "like-stock-certificate_disease": "ibs",
    "non-alcoholic-fatty-liver-disease": "nafld",
    "hereditary-fructose-intolerance": "hereditary_fructose_intolerance",
    "kidney-stones_disease": "kidney_stones",
    "high-blood-pressure_disease": "hypertension",
}

# Allergy rules put different allergens under the same label (e.g. peanut under "tree-nut");
# derive the real condition from the rule's target text instead.
ALLERGY_TARGET_KEYWORDS = [
    ("peanut", "peanut_allergy"), ("almond", "tree_nut_allergy"), ("hazelnut", "tree_nut_allergy"),
    ("pecan", "tree_nut_allergy"), ("cashew", "tree_nut_allergy"), ("macadamia", "tree_nut_allergy"),
    ("walnut", "tree_nut_allergy"), ("celery", "celery_allergy"), ("soy", "soy_allergy"),
    ("sesame", "sesame_allergy"), ("kiwi", "kiwi_allergy"), ("milk", "milk_allergy"),
    ("peach", "peach_allergy"), ("pear", "pear_allergy"), ("apple", "apple_allergy"),
    ("latex", "latex_fruit_syndrome"), ("banana", "latex_fruit_syndrome"),
]

# Keywords prefixed "=" are matched against the accented lowercase name (bơ/bò, mè/me, lạc/lac collide once accents are stripped).
# Ingredients whose name contains one of these words are never linked to the key's condition (plant milks are not dairy).
CONDITION_EXCLUDES = {
    "pear_allergy": ["dua"],
    "milk_allergy": ["vu sua", "dau nanh", "dau tuong", "hanh nhan", "dua", "gao", "yen mach", "hat", "me den"],
}
