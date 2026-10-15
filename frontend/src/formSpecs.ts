// Seleção inicial RASTREÁVEL de campos dos formulários INTERPOL DVI AM/PM 2023 (form_data).
// "code" = número do campo no formulário oficial; "EXT" = extensão proposta pelo sistema.
// Ver docs/RASTREABILIDADE.md.
import type { FieldSpec } from "./components/Fields";

const YES_NO = { "1": "Não", "2": "Sim" };
const NO_NP_YES = { "1": "Não", "2": "Não possível", "3": "Sim" };
const HAIR_COLOUR = {
  "1": "Loiro", "2": "Castanho", "3": "Preto", "4": "Ruivo", "5": "Grisalho", "6": "Branco",
  "7": "Misto grisalho", "8": "Outro",
};
const HAIR_LENGTH = { "1": "Curto (<6 cm)", "2": "Médio (<12 cm)", "3": "Longo (>12 cm)", "4": "Raspado" };
const HAIR_TYPE = { "1": "Natural", "2": "Extensão", "3": "Aplique", "4": "Peruca", "5": "Implante" };
const EYES = {
  "1": "Azul", "2": "Cinza", "3": "Verde", "4": "Castanho", "5": "Preto", "6": "Avelã", "7": "Marrom-avermelhado",
  "8": "Rosa",
};
const FACIAL_HAIR = { "1": "Barbeado", "2": "Bigode", "3": "Cavanhaque", "4": "Costeletas", "5": "Barba cheia", "6": "Outro" };
const DENTITION = { "1": "Decídua", "2": "Mista", "3": "Permanente" };

export const AM_SECTIONS: Record<string, { title: string; specs: FieldSpec[] }> = {
  circumstances: {
    title: "Desaparecimento",
    specs: [
      { key: "last_seen_date", label: "Visto pela última vez em", code: "EXT", type: "date" },
      { key: "last_seen_place", label: "Local onde foi visto pela última vez", code: "EXT", wide: true },
      { key: "circumstances", label: "Circunstâncias informadas", code: "EXT", type: "textarea" },
    ],
  },
  admin: {
    title: "Dados administrativos",
    specs: [
      { key: "100_agency", label: "Órgão responsável", code: "100" },
      { key: "100_police_file", label: "Nº do procedimento policial", code: "100" },
      { key: "120_fingerprinted", label: "Possui registro papiloscópico", code: "120", type: "select", options: YES_NO },
      { key: "120_where", label: "Onde (registro papiloscópico)", code: "120" },
      { key: "125_sources", label: "Fontes de impressões obtíveis (residência, biometria)", code: "125", type: "textarea" },
    ],
  },
  nominal: {
    title: "Dados nominais",
    specs: [
      { key: "200_birth_family_name", label: "Sobrenome de nascimento", code: "200" },
      { key: "200_mother_maiden_name", label: "Nome de solteira da mãe", code: "200" },
      { key: "205_nicknames", label: "Apelidos", code: "205" },
      { key: "210_aliases", label: "Outros nomes usados", code: "210" },
      { key: "215_nationality", label: "Nacionalidade", code: "215" },
      { key: "220_birthplace", label: "Naturalidade (cidade/país)", code: "220" },
      { key: "225_national_id", label: "Nº de documento nacional (fictício)", code: "225" },
      {
        key: "230_marital_status", label: "Estado civil", code: "230", type: "select",
        options: { "1": "Solteiro(a)", "2": "Noivo(a)", "3": "União estável", "4": "Casado(a)", "5": "Divorciado(a)", "6": "Viúvo(a)" },
      },
      { key: "235_occupation", label: "Ocupação", code: "235" },
      { key: "238_home_address", label: "Endereço residencial", code: "238", wide: true },
      { key: "240_current_address", label: "Endereço atual (ex.: hotel)", code: "240", wide: true },
      { key: "241_phones", label: "Telefone(s) celular(es)", code: "241" },
      { key: "243_online", label: "Presença online (e-mail, redes sociais)", code: "243" },
    ],
  },
  body: {
    title: "Descrição corporal",
    specs: [
      { key: "420_hair_type", label: "Cabelo — tipo", code: "420", type: "select", options: HAIR_TYPE },
      { key: "420_hair_length", label: "Cabelo — comprimento", code: "420", type: "select", options: HAIR_LENGTH },
      { key: "420_hair_natural_colour", label: "Cabelo — cor natural", code: "420", type: "select", options: HAIR_COLOUR },
      { key: "420_hair_dyed_colour", label: "Cabelo — cor tingida", code: "420", type: "select", options: HAIR_COLOUR },
      { key: "428_eye_colour", label: "Olhos — cor", code: "428", type: "select", options: EYES },
      { key: "436_facial_hair", label: "Pelos faciais", code: "436", type: "select", options: FACIAL_HAIR },
      { key: "440_ears", label: "Orelhas (lóbulo, furos)", code: "440" },
      { key: "472_circumcision", label: "Circuncisão", code: "472", type: "select", options: YES_NO },
      { key: "4xx_other_features", label: "Outras características distintivas (sobrancelhas, nariz, lábios, mãos…)", code: "424–468", type: "textarea" },
    ],
  },
  medical: {
    title: "Dados médicos de referência",
    specs: [
      { key: "500_practitioner", label: "Médico/serviço de saúde de referência", code: "500", wide: true },
      { key: "505_history", label: "Histórico médico (diagnósticos, fraturas, cirurgias, cicatrizes)", code: "505", type: "textarea" },
      { key: "520_internal_prostheses", label: "Próteses internas", code: "520" },
      { key: "525_artificial_aids", label: "Outros auxílios artificiais", code: "525" },
    ],
  },
  dental: {
    title: "Referências odontológicas",
    specs: [
      { key: "600_dentist", label: "Dentista/clínica", code: "600", wide: true },
      { key: "600_period", label: "Período coberto pelos registros", code: "600" },
      { key: "615_images", label: "Imagens odontológicas disponíveis (PA, BW, OPG, TC, fotos)", code: "615" },
      { key: "635_specific", label: "Dados específicos (coroas, pontes, implantes, próteses)", code: "635", type: "textarea" },
      { key: "640_other", label: "Outros achados (oclusão, desgaste, manchas)", code: "640", type: "textarea" },
      { key: "645_dentition", label: "Tipo de dentição", code: "645", type: "select", options: DENTITION },
    ],
  },
  dna: {
    title: "Referências de DNA",
    specs: [
      { key: "555_direct_reference", label: "Referência direta (perfil, biobanco, objeto pessoal)", code: "555", type: "textarea" },
      { key: "560_relatives", label: "Amostras de parentes biológicos (vínculo, referência laboratorial)", code: "560", type: "textarea" },
    ],
  },
  supporting: {
    title: "Informações complementares",
    specs: [{ key: "700_notes", label: "Informações complementares (indicar campo de referência)", code: "700", type: "textarea" }],
  },
};

export const PM_SECTIONS: Record<string, { title: string; specs: FieldSpec[] }> = {
  reception: {
    title: "Recepção",
    specs: [
      { key: "recovery_team", label: "Equipe de recuperação", code: "EXT" },
      { key: "linked_pm_numbers", label: "Números PM de partes possivelmente relacionadas", code: "EXT", wide: true },
      { key: "185_refs", label: "Números de referência (AFIS, DNA, polícia, outros)", code: "185", wide: true },
    ],
  },
  checklist: {
    title: "Checklist de procedimentos no necrotério",
    specs: [
      { key: "155_photos", label: "Fotografias realizadas", code: "155", type: "select", options: YES_NO },
      { key: "160_effects", label: "Pertences coletados", code: "160", type: "select", options: YES_NO },
      { key: "165_fingers", label: "Impressões — dedos", code: "165", type: "select", options: NO_NP_YES },
      { key: "165_palms", label: "Impressões — palmas", code: "165", type: "select", options: NO_NP_YES },
      { key: "165_feet", label: "Impressões — pés", code: "165", type: "select", options: NO_NP_YES },
      { key: "170_external", label: "Exame externo", code: "170", type: "select", options: YES_NO },
      { key: "170_partial", label: "Necropsia parcial", code: "170", type: "select", options: YES_NO },
      { key: "170_full", label: "Necropsia completa", code: "170", type: "select", options: YES_NO },
      { key: "170_pathologist", label: "Patologista/perito responsável", code: "170" },
      { key: "175_dental_done", label: "Exame odontológico concluído", code: "175", type: "select", options: YES_NO },
      { key: "175_odontologist", label: "Odontolegista", code: "175" },
      { key: "180_dna_pathologist", label: "Amostras para DNA coletadas (patologia)", code: "180", type: "select", options: YES_NO },
      { key: "180_dna_odontologist", label: "Amostras para DNA coletadas (odontologia)", code: "180", type: "select", options: YES_NO },
    ],
  },
  body: AM_SECTIONS.body,
  fingerprint: {
    title: "Necropapiloscopia",
    specs: [
      { key: "484_skin", label: "Pele de onde foram obtidas", code: "484", type: "select", options: { "1": "Epiderme", "2": "Derme" } },
      {
        key: "488_technique", label: "Técnica de revelação", code: "488", type: "select",
        options: { "1": "Lavagem e coleta", "2": "Água fervente", "3": "Luva epidérmica", "4": "Moldagem com silicone", "5": "Outra" },
      },
      {
        key: "492_recorded", label: "Registro por", code: "492", type: "select",
        options: { "1": "Pó preto e fita", "2": "Tinta", "3": "Scanner digital", "4": "Fotografia", "5": "Outro" },
      },
      { key: "496_areas", label: "Áreas de onde as impressões foram obtidas", code: "496", type: "textarea" },
    ],
  },
  pathology: {
    title: "Patologia",
    specs: [
      { key: "510_internal", label: "Exame interno (achados por região, fraturas consolidadas, cirurgias)", code: "510", type: "textarea" },
      { key: "520_internal_prostheses", label: "Próteses internas", code: "520" },
      { key: "525_artificial_aids", label: "Outros auxílios artificiais", code: "525" },
      { key: "550_further", label: "Outras informações de identificação", code: "550", type: "textarea" },
    ],
  },
  dna: {
    title: "Amostras de DNA",
    specs: [
      { key: "545_specimens", label: "Amostras (nº, tipo: osso/dente/músculo/sangue, estado)", code: "545", type: "textarea" },
    ],
  },
  dental: {
    title: "Odontologia",
    specs: [
      { key: "610_material", label: "Material presente para exame (arcadas, dentes, fragmentos)", code: "610", type: "textarea" },
      { key: "615_images", label: "Imagens odontológicas produzidas", code: "615" },
      { key: "625_jaws", label: "Condição das arcadas / outros detalhes", code: "625", type: "textarea" },
      { key: "635_specific", label: "Dados específicos (coroas, pontes, implantes, canal)", code: "635", type: "textarea" },
      { key: "645_dentition", label: "Tipo de dentição", code: "645", type: "select", options: DENTITION },
      { key: "647_age", label: "Idade estimada pela odontologia", code: "647" },
    ],
  },
  supporting: AM_SECTIONS.supporting,
};
