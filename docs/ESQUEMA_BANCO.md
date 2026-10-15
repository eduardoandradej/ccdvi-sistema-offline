# Esquema do banco de dados (PostgreSQL 16)

Gerado a partir do banco migrado pela revisão Alembic `0001` (`backend/alembic/versions/0001_esquema_inicial.py`).
Diagrama ER e significado das entidades: [ARQUITETURA.md](ARQUITETURA.md).

## Migrações

```bash
cd backend && .venv/bin/alembic upgrade head      # aplica
.venv/bin/alembic downgrade base                 # reverte tudo (somente laboratório)
.venv/bin/alembic revision --autogenerate -m "descrição"   # nova migração após alterar app/models.py
```

A migração 0001 também cria a função e os gatilhos `audit_events_immutable`, que bloqueiam UPDATE, DELETE e TRUNCATE em `audit_events`.


## am_cases

| Coluna | Tipo | Nulo |
|---|---|---|
| id | uuid | não |
| operation_id | uuid | não |
| origin_base_id | uuid | não |
| am_number | character varying | não |
| status | character varying | não |
| family_name | character varying | sim |
| given_names | character varying | sim |
| sex | character varying | sim |
| date_of_birth | date | sim |
| age_years | integer | sim |
| height_min_cm | integer | sim |
| height_max_cm | integer | sim |
| weight_min_kg | integer | sim |
| weight_max_kg | integer | sim |
| build | character varying | sim |
| height_certainty | character varying | sim |
| category_status | jsonb | não |
| form_data | jsonb | não |
| created_by | uuid | não |
| updated_by | uuid | não |
| version | integer | não |
| created_at | timestamp with time zone | não |
| updated_at | timestamp with time zone | não |

## am_interviews

| Coluna | Tipo | Nulo |
|---|---|---|
| id | uuid | não |
| am_case_id | uuid | não |
| informant_name | character varying | não |
| relationship_to_missing | character varying | sim |
| contact | character varying | sim |
| address | text | sim |
| interview_date | date | sim |
| location | character varying | sim |
| is_point_of_contact | boolean | não |
| notes | text | sim |
| interviewer_id | uuid | não |
| created_at | timestamp with time zone | não |
| updated_at | timestamp with time zone | não |

## attachments

| Coluna | Tipo | Nulo |
|---|---|---|
| id | uuid | não |
| operation_id | uuid | não |
| base_id | uuid | não |
| am_case_id | uuid | sim |
| pm_case_id | uuid | sim |
| doc_type | character varying | não |
| subject | character varying | não |
| title | character varying | não |
| description | text | sim |
| source | character varying | sim |
| evidence_ref | character varying | sim |
| obtained_at | timestamp with time zone | sim |
| uploaded_at | timestamp with time zone | não |
| uploaded_by | uuid | não |
| original_filename | character varying | não |
| safe_filename | character varying | não |
| mime_type | character varying | não |
| size_bytes | bigint | não |
| sha256 | character varying | não |
| storage_key | character varying | não |
| page_count | integer | sim |
| status | character varying | não |
| version | integer | não |
| supersedes_id | uuid | sim |
| superseded | boolean | não |
| withdrawn_reason | text | sim |

## audit_events

| Coluna | Tipo | Nulo |
|---|---|---|
| id | bigint | não |
| occurred_at | timestamp with time zone | não |
| user_id | uuid | sim |
| username | character varying | sim |
| operation_id | uuid | sim |
| base_id | uuid | sim |
| role | character varying | sim |
| action | character varying | não |
| object_type | character varying | sim |
| object_id | character varying | sim |
| outcome | character varying | não |
| details | jsonb | não |
| client_ip | character varying | sim |

## authorizations

| Coluna | Tipo | Nulo |
|---|---|---|
| id | uuid | não |
| user_id | uuid | não |
| operation_id | uuid | não |
| base_id | uuid | não |
| role | character varying | não |
| active | boolean | não |
| created_at | timestamp with time zone | não |
| updated_at | timestamp with time zone | não |

## bases

| Coluna | Tipo | Nulo |
|---|---|---|
| id | uuid | não |
| operation_id | uuid | não |
| code | character varying | não |
| name | character varying | não |
| kind | character varying | não |
| created_at | timestamp with time zone | não |
| updated_at | timestamp with time zone | não |

## custody_events

| Coluna | Tipo | Nulo |
|---|---|---|
| id | uuid | não |
| pm_case_id | uuid | não |
| event_type | character varying | não |
| occurred_at | timestamp with time zone | não |
| location | character varying | sim |
| responsible | character varying | não |
| notes | text | sim |
| recorded_by | uuid | não |
| recorded_at | timestamp with time zone | não |

## effects

| Coluna | Tipo | Nulo |
|---|---|---|
| id | uuid | não |
| am_case_id | uuid | sim |
| pm_case_id | uuid | sim |
| field_code | character varying | não |
| item_code | character varying | não |
| type_style | character varying | sim |
| colour | character varying | sim |
| brand | character varying | sim |
| material | character varying | sim |
| size | character varying | sim |
| inscription | character varying | sim |
| where_worn | character varying | sim |
| serial_number | character varying | sim |
| description | text | sim |
| certainty | character varying | não |
| created_at | timestamp with time zone | não |
| updated_at | timestamp with time zone | não |

## match_reviews

| Coluna | Tipo | Nulo |
|---|---|---|
| id | uuid | não |
| operation_id | uuid | não |
| am_case_id | uuid | não |
| pm_case_id | uuid | não |
| status | character varying | não |
| notes | text | sim |
| algorithm_version | character varying | não |
| parameters | jsonb | não |
| result_snapshot | jsonb | não |
| technical_index | double precision | sim |
| reviewed_by | uuid | não |
| created_at | timestamp with time zone | não |
| updated_at | timestamp with time zone | não |

## number_counters

| Coluna | Tipo | Nulo |
|---|---|---|
| operation_id | uuid | não |
| kind | character varying | não |
| last_value | integer | não |

## operations

| Coluna | Tipo | Nulo |
|---|---|---|
| id | uuid | não |
| code | character varying | não |
| name | character varying | não |
| kind | character varying | não |
| status | character varying | não |
| country_code | character varying | não |
| disaster_place | character varying | sim |
| disaster_nature | character varying | sim |
| disaster_date | date | sim |
| created_at | timestamp with time zone | não |
| updated_at | timestamp with time zone | não |

## physical_marks

| Coluna | Tipo | Nulo |
|---|---|---|
| id | uuid | não |
| am_case_id | uuid | sim |
| pm_case_id | uuid | sim |
| mark_type | character varying | não |
| region | character varying | não |
| description | text | sim |
| certainty | character varying | não |
| source | character varying | sim |
| created_at | timestamp with time zone | não |
| updated_at | timestamp with time zone | não |

## pm_cases

| Coluna | Tipo | Nulo |
|---|---|---|
| id | uuid | não |
| operation_id | uuid | não |
| origin_base_id | uuid | não |
| pm_number | character varying | não |
| scene_ref | character varying | sim |
| status | character varying | não |
| recovery_date | date | sim |
| recovery_place | character varying | sim |
| state_of_body | character varying | sim |
| sex | character varying | sim |
| sex_reason | character varying | sim |
| age_min_years | integer | sim |
| age_max_years | integer | sim |
| age_method | character varying | sim |
| height_min_cm | integer | sim |
| height_max_cm | integer | sim |
| weight_min_kg | integer | sim |
| weight_max_kg | integer | sim |
| build | character varying | sim |
| height_certainty | character varying | sim |
| category_status | jsonb | não |
| form_data | jsonb | não |
| created_by | uuid | não |
| updated_by | uuid | não |
| version | integer | não |
| created_at | timestamp with time zone | não |
| updated_at | timestamp with time zone | não |

## sessions

| Coluna | Tipo | Nulo |
|---|---|---|
| id | uuid | não |
| token_hash | character varying | não |
| user_id | uuid | não |
| created_at | timestamp with time zone | não |
| expires_at | timestamp with time zone | não |
| revoked | boolean | não |
| operation_id | uuid | sim |
| base_id | uuid | sim |
| role | character varying | sim |

## users

| Coluna | Tipo | Nulo |
|---|---|---|
| id | uuid | não |
| username | character varying | não |
| full_name | character varying | não |
| job_title | character varying | sim |
| password_hash | character varying | não |
| active | boolean | não |
| created_at | timestamp with time zone | não |
| updated_at | timestamp with time zone | não |

## Restrições (CHECK e UNIQUE)

| Tabela | Restrição | Definição |
|---|---|---|
| operations | ck_operation_kind | `CHECK (((kind)::text = ANY ((ARRAY['TREINAMENTO'::character varying, 'REAL'::character varying])::text[])))` |
| operations | ck_operation_status | `CHECK (((status)::text = ANY ((ARRAY['ATIVA'::character varying, 'ENCERRADA'::character varying])::text[])))` |
| operations | operations_code_key | `UNIQUE (code)` |
| users | users_username_key | `UNIQUE (username)` |
| bases | ck_base_kind | `CHECK (((kind)::text = ANY ((ARRAY['COMANDO'::character varying, 'AM'::character varying, 'PM'::character varying, 'OUTRO'::character varying])::text[])))` |
| bases | uq_base_operation_code | `UNIQUE (operation_id, code)` |
| am_cases | ck_am_sex | `CHECK (((sex IS NULL) OR ((sex)::text = ANY ((ARRAY['M'::character varying, 'F'::character varying, 'O'::character varying, 'U'::character varying])::text[]))))` |
| am_cases | uq_am_number | `UNIQUE (operation_id, am_number)` |
| authorizations | uq_authorization | `UNIQUE (user_id, operation_id, base_id, role)` |
| pm_cases | ck_pm_sex | `CHECK (((sex IS NULL) OR ((sex)::text = ANY ((ARRAY['M'::character varying, 'F'::character varying, 'I'::character varying])::text[]))))` |
| pm_cases | uq_pm_number | `UNIQUE (operation_id, pm_number)` |
| sessions | sessions_token_hash_key | `UNIQUE (token_hash)` |
| attachments | attachments_storage_key_key | `UNIQUE (storage_key)` |
| attachments | ck_attachment_owner | `CHECK (((am_case_id IS NULL) <> (pm_case_id IS NULL)))` |
| attachments | ck_attachment_status | `CHECK (((status)::text = ANY ((ARRAY['ARMAZENADO'::character varying, 'RETIRADO'::character varying, 'ERRO'::character varying])::text[])))` |
| effects | ck_effect_owner | `CHECK (((am_case_id IS NULL) <> (pm_case_id IS NULL)))` |
| match_reviews | ck_match_status | `CHECK (((status)::text = ANY ((ARRAY['SUGERIDO'::character varying, 'EM_ANALISE'::character varying, 'INFORMACOES_COMPLEMENTARES'::character varying, 'DESCARTADO'::character varying, 'ENCAMINHADO_AVALIACAO_TECNICA'::character varying])::text[])))` |
| match_reviews | uq_match_pair | `UNIQUE (am_case_id, pm_case_id)` |
| physical_marks | ck_mark_owner | `CHECK (((am_case_id IS NULL) <> (pm_case_id IS NULL)))` |
