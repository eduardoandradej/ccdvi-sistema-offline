"""Vocabulários controlados extraídos dos formulários INTERPOL DVI AM/PM 2023.

Os códigos numéricos são os do próprio formulário (rastreabilidade em
docs/RASTREABILIDADE.md). Os rótulos em português são traduções propostas pelo projeto.
"""

# 404 — colunas "Specific details"
MARK_TYPES = {
    "1": "Cicatriz",
    "2": "Piercing",
    "3": "Tatuagem",
    "4": "Mancha/marca de pele",
    "5": "Malformação",
    "6": "Amputação",
}

# 404 — linhas (regiões anatômicas). Lateralidade implícita no código (2x esquerda, 3x direita).
REGIONS = {
    "01": "Cabeça",
    "02": "Pescoço",
    "11": "Tronco — frente",
    "12": "Tronco — costas",
    "13": "Genitália",
    "14": "Nádegas",
    "21": "Braço esquerdo",
    "22": "Antebraço esquerdo",
    "23": "Mão esquerda",
    "24": "Coxa esquerda",
    "25": "Joelho esquerdo",
    "26": "Perna esquerda",
    "27": "Pé esquerdo",
    "31": "Braço direito",
    "32": "Antebraço direito",
    "33": "Mão direita",
    "34": "Coxa direita",
    "35": "Joelho direito",
    "36": "Perna direita",
    "37": "Pé direito",
}


def region_side(code: str) -> str | None:
    if code.startswith("2"):
        return "ESQUERDO"
    if code.startswith("3"):
        return "DIREITO"
    return None


def contralateral(code: str) -> str | None:
    if code.startswith("2"):
        return "3" + code[1]
    if code.startswith("3"):
        return "2" + code[1]
    return None


# 300–350 / 515 — categorias de objetos e itens por código
EFFECT_FIELDS = {
    "300": "Vestimentas",
    "305": "Calçados",
    "310": "Relógio",
    "315": "Óculos",
    "335": "Joias/adornos",
    "340": "Documentos de identidade",
    "345": "Objetos pessoais",
    "350": "Dispositivos eletrônicos",
    "515": "Implantes",
}

EFFECT_ITEMS = {
    "300": {
        "101": "Chapéu/cobertura de cabeça", "102": "Cachecol", "103": "Gravata", "199": "Outro (cabeça/pescoço)",
        "201": "Luvas", "202": "Sobretudo", "203": "Casaco/jaqueta", "204": "Cardigã", "205": "Colete",
        "206": "Suspensório", "207": "Pulôver", "208": "Blusa", "209": "Camisa", "210": "Camiseta",
        "211": "Camiseta de baixo", "212": "Sutiã", "299": "Outro (parte superior)",
        "301": "Cinto", "302": "Calça", "303": "Bermuda/short", "304": "Saia", "305": "Meia-calça",
        "306": "Meias", "307": "Meias longas", "308": "Roupa íntima", "399": "Outro (parte inferior)",
        "401": "Macacão", "402": "Vestido", "403": "Traje religioso/cultural/tradicional",
        "404": "Uniforme", "405": "Traje de banho", "499": "Outro (corpo inteiro)",
    },
    "305": {"01": "Botas", "02": "Calçado aberto", "03": "Sapatos", "99": "Outro"},
    "310": {"01": "Relógio de pulso digital", "02": "Relógio de pulso analógico", "03": "Smartwatch",
            "04": "Relógio, outro tipo"},
    "315": {"01": "Armação"},
    "335": {"01": "Tornozeleira", "02": "Pulseira", "03": "Brinco de pressão", "04": "Brincos",
            "05": "Corrente de pescoço", "06": "Colar", "07": "Pingente", "08": "Aliança",
            "09": "Outros anéis", "10": "Outros anéis no dedo", "99": "Outro"},
    "340": {"01": "Cartões bancários", "02": "Carteira de motorista", "03": "Carteira de identidade",
            "04": "Passaporte", "99": "Outro"},
    "345": {"01": "Crachás/chaves", "02": "Pochete", "03": "Dinheiro", "04": "Agenda",
            "05": "Bolsa", "06": "Bilhete", "07": "Carteira", "99": "Outro"},
    "350": {"01": "Câmera", "02": "Telefone celular", "03": "Reprodutor de música", "04": "SIM",
            "05": "Tablet/portátil", "06": "Vídeo", "07": "Mídia de armazenamento", "99": "Outro"},
    "515": {"01": "Mama", "02": "Marca-passo", "03": "Bomba de insulina", "04": "Outros implantes cirúrgicos"},
}

# "Only use these colours" (formulários 300–350)
COLOURS = {
    "BLACK": "Preto", "BLUE": "Azul", "BROWN": "Marrom", "GREEN": "Verde", "GREY": "Cinza",
    "ORANGE": "Laranja", "PINK": "Rosa", "PURPLE": "Roxo", "RED": "Vermelho", "WHITE": "Branco",
    "YELLOW": "Amarelo", "UNKNOWN": "Desconhecida", "SILVER": "Prata", "GOLD": "Dourado",
    "MULTI": "Multicolorido",
}

# Extensão do sistema (B): grau de certeza/origem da informação
CERTAINTY_AM = {"RELATADO": "Relato de familiar/fonte", "DOCUMENTADO": "Confirmado por documento",
                "INCERTO": "Incerto"}
CERTAINTY_PM = {"OBSERVADO": "Observado no exame", "PROVAVEL": "Provável", "INCERTO": "Incerto"}
CERTAINTIES = {**CERTAINTY_AM, **CERTAINTY_PM}

# Extensão do sistema (B): situação de uma categoria (ex.: tatuagens) quando não há itens.
# Ausência de registro NÃO é tratada como evidência negativa.
CATEGORY_STATUS = {
    "NAO_INFORMADO": "Não informado",
    "NAO_OBSERVADO": "Não observado",
    "NAO_EXAMINAVEL": "Não examinável",
    "NEGATIVO": "Negativo (verificado: não possui)",
    "DESCONHECIDO": "Desconhecido",
    "POSITIVO": "Possui (ver itens)",
}

AM_SEX = {"M": "Masculino", "F": "Feminino", "O": "Outro", "U": "Desconhecido"}
PM_SEX = {"M": "Masculino", "F": "Feminino", "I": "Indeterminado"}  # campo 535
STATE_OF_BODY = {"COMPLETO": "Completo", "INCOMPLETO": "Incompleto", "SEGMENTO": "Segmento corporal"}  # 402
BUILD = {"1": "Delgado", "2": "Médio", "3": "Robusto"}  # 416

AM_STATUS = {"RASCUNHO": "Rascunho", "PRONTO_RECONCILIACAO": "Pronto para reconciliação"}
PM_STATUS = AM_STATUS

CUSTODY_EVENTS = {
    "RECEBIMENTO": "Recebimento", "TRANSFERENCIA": "Transferência", "ARMAZENAMENTO": "Armazenamento",
    "EXAME": "Exame", "COLETA_AMOSTRA": "Coleta de amostra", "LIBERACAO": "Liberação",
}

# Tipos de anexo e a qual sujeito podem se referir
ATTACHMENT_TYPES = {
    "DOC_IDENTIFICACAO": "Documento de identificação",
    "FOTO_REFERENCIA_AM": "Fotografia de referência (AM)",
    "FOTO_ACHADO_PM": "Fotografia de achado/exame (PM)",
    "DOC_MEDICO": "Documento médico",
    "DOC_ODONTOLOGICO": "Documento odontológico",
    "REGISTRO_PERTENCE": "Registro de pertence/objeto",
    "ADMINISTRATIVO": "Material administrativo autorizado",
    "OUTRO": "Outro documento",
}
ATTACHMENT_SUBJECTS_AM = {"DESAPARECIDO": "Pessoa desaparecida", "ENTREVISTADO": "Entrevistado/fonte"}
ATTACHMENT_SUBJECTS_PM = {"REGISTRO_PM": "Registro PM"}
ATTACHMENT_TYPES_AM = set(ATTACHMENT_TYPES) - {"FOTO_ACHADO_PM"}
ATTACHMENT_TYPES_PM = set(ATTACHMENT_TYPES) - {"FOTO_REFERENCIA_AM"}

# Motivos de tatuagem — vocabulário controlado mínimo (extensão B, v0.1) usado para
# indicar "categoria de motivo compatível". Não substitui a análise de especialista.
TATTOO_MOTIF_CATEGORIES = {
    "FLORAL": {"rosa", "rosas", "flor", "flores", "floral", "lirio", "lírio", "tulipa", "orquidea",
               "orquídea", "girassol", "lotus", "lótus", "margarida"},
    "ANIMAL": {"leao", "leão", "tigre", "aguia", "águia", "cobra", "serpente", "dragao", "dragão",
               "lobo", "passaro", "pássaro", "borboleta", "gato", "cachorro", "escorpiao", "escorpião"},
    "RELIGIOSO": {"cruz", "terco", "terço", "santa", "santo", "anjo", "jesus", "biblia", "bíblia"},
    "TEXTO": {"nome", "frase", "letras", "escrita", "palavra", "iniciais", "data"},
    "GEOMETRICO": {"tribal", "geometrico", "geométrico", "mandala", "estrela", "circulo", "círculo"},
}


def vocabularies() -> dict:
    return {
        "mark_types": MARK_TYPES,
        "regions": REGIONS,
        "effect_fields": EFFECT_FIELDS,
        "effect_items": EFFECT_ITEMS,
        "colours": COLOURS,
        "certainty_am": CERTAINTY_AM,
        "certainty_pm": CERTAINTY_PM,
        "category_status": CATEGORY_STATUS,
        "am_sex": AM_SEX,
        "pm_sex": PM_SEX,
        "state_of_body": STATE_OF_BODY,
        "build": BUILD,
        "case_status": AM_STATUS,
        "custody_events": CUSTODY_EVENTS,
        "attachment_types": ATTACHMENT_TYPES,
        "attachment_types_am": sorted(ATTACHMENT_TYPES_AM),
        "attachment_types_pm": sorted(ATTACHMENT_TYPES_PM),
        "attachment_subjects_am": ATTACHMENT_SUBJECTS_AM,
        "attachment_subjects_pm": ATTACHMENT_SUBJECTS_PM,
    }
