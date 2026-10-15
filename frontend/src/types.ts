export type Dict = Record<string, string>;

export interface Operation {
  id: string;
  code: string;
  name: string;
  kind: "TREINAMENTO" | "REAL";
  status: string;
  country_code: string;
  disaster_place: string | null;
  disaster_nature: string | null;
  disaster_date: string | null;
}

export interface OpBase {
  id: string;
  code: string;
  name: string;
  kind: string;
}

export interface AuthorizationInfo {
  operation: Operation;
  base: OpBase;
  role: string;
  role_label: string;
}

export interface Me {
  id: string;
  username: string;
  full_name: string;
  job_title: string | null;
  authorizations: AuthorizationInfo[];
  context: { operation: Operation; base: OpBase; role: string; role_label: string } | null;
  permissions: string[];
}

export interface Vocab {
  mark_types: Dict;
  regions: Dict;
  effect_fields: Dict;
  effect_items: Record<string, Dict>;
  colours: Dict;
  certainty_am: Dict;
  certainty_pm: Dict;
  category_status: Dict;
  am_sex: Dict;
  pm_sex: Dict;
  state_of_body: Dict;
  build: Dict;
  case_status: Dict;
  custody_events: Dict;
  attachment_types: Dict;
  attachment_types_am: string[];
  attachment_types_pm: string[];
  attachment_subjects_am: Dict;
  attachment_subjects_pm: Dict;
  roles: Dict;
}

export interface Mark {
  id: string;
  mark_type: string;
  region: string;
  description: string | null;
  certainty: string;
  source: string | null;
}

export interface Effect {
  id: string;
  field_code: string;
  item_code: string;
  type_style: string | null;
  colour: string | null;
  brand: string | null;
  material: string | null;
  size: string | null;
  inscription: string | null;
  where_worn: string | null;
  serial_number: string | null;
  description: string | null;
  certainty: string;
}

export interface Interview {
  id: string;
  informant_name: string;
  relationship_to_missing: string | null;
  contact: string | null;
  address: string | null;
  interview_date: string | null;
  location: string | null;
  is_point_of_contact: boolean;
  notes: string | null;
  created_at: string;
}

export interface CaseCommon {
  id: string;
  status: string;
  height_min_cm: number | null;
  height_max_cm: number | null;
  weight_min_kg: number | null;
  weight_max_kg: number | null;
  build: string | null;
  height_certainty: string | null;
  category_status: Dict;
  form_data: Record<string, Record<string, unknown>>;
  version: number;
  created_at: string;
  updated_at: string;
  marks: Mark[];
  effects: Effect[];
}

export interface AmCase extends CaseCommon {
  am_number: string;
  family_name: string | null;
  given_names: string | null;
  sex: string | null;
  date_of_birth: string | null;
  age_years: number | null;
  interviews: Interview[];
}

export interface Custody {
  id: string;
  event_type: string;
  occurred_at: string;
  location: string | null;
  responsible: string;
  notes: string | null;
  recorded_at: string;
}

export interface PmCase extends CaseCommon {
  pm_number: string;
  scene_ref: string | null;
  recovery_date: string | null;
  recovery_place: string | null;
  state_of_body: string | null;
  sex: string | null;
  sex_reason: string | null;
  age_min_years: number | null;
  age_max_years: number | null;
  age_method: string | null;
  custody: Custody[];
}

export interface Attachment {
  id: string;
  am_case_id: string | null;
  pm_case_id: string | null;
  doc_type: string;
  subject: string;
  title: string;
  description: string | null;
  source: string | null;
  evidence_ref: string | null;
  obtained_at: string | null;
  uploaded_at: string;
  uploaded_by_name: string | null;
  original_filename: string;
  mime_type: string;
  size_bytes: number;
  sha256: string;
  page_count: number | null;
  status: string;
  version: number;
  supersedes_id: string | null;
  superseded: boolean;
  withdrawn_reason: string | null;
}

export interface HistoryEntry {
  id: number;
  occurred_at: string;
  username: string | null;
  role: string | null;
  action: string;
  outcome: string;
  details: Record<string, unknown>;
}

export interface FieldResult {
  attribute: string;
  field_code: string;
  outcome: string;
  am_value: string | null;
  pm_value: string | null;
  explanation: string;
  critical: boolean;
  text_similarity: number | null;
}

export interface CandidateSummary {
  am_case_id: string;
  pm_case_id: string;
  am_number: string;
  pm_number: string;
  technical_index: number;
  coincidences: number;
  divergences: number;
  critical_divergences: number;
  missing: number;
  review_status: string | null;
}
