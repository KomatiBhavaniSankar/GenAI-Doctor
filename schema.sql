-- Run in Supabase: SQL Editor
create table doctors (
  id uuid primary key default gen_random_uuid(),
  name text not null, specialization text not null, hospital text not null,
  created_at timestamptz default now()
);
create table sessions (
  id uuid primary key default gen_random_uuid(),
  doctor_id uuid references doctors(id),
  tab text, story text, opening text,
  device text, user_agent text, screen text,
  started_at timestamptz default now()
);
-- every click, page view, page time (ms), video skip, timer expiry, add-to-sheet
create table events (
  id bigint generated always as identity primary key,
  session_id uuid references sessions(id),
  doctor_id uuid references doctors(id),
  page text, event_type text, label text, duration_ms int,
  client_ts timestamptz,            -- when it happened on the doctor's device
  created_at timestamptz default now()  -- when the server stored it
);
create index events_session_idx on events(session_id, created_at);
create index events_doctor_idx on events(doctor_id, created_at);
create table patient_records (
  id uuid primary key default gen_random_uuid(),
  session_id uuid references sessions(id),
  doctor_id uuid references doctors(id),
  patient_name text, items jsonb, notes text,
  payload jsonb,                    -- case, transcript, plan, follow-up, approval
  created_at timestamptz default now()
);
-- clicks and seconds per page, per session
create view page_stats as
select session_id, page,
  count(*) filter (where event_type = 'click') as clicks,
  round(coalesce(sum(duration_ms) filter (where event_type = 'page_time'), 0) / 1000.0, 1) as seconds
from events group by session_id, page;

-- v2 tables (transcripts, treatment_plan_items, cases): see migrate_v2.sql
