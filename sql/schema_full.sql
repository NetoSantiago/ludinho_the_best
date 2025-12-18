-- ================================================
-- LUDINHO • SCHEMA COMPLETO (consolidado 010 + 011 + auth + ajustes)
-- Gera toda a estrutura: tipos, tabelas, índices, funções, triggers, views.
-- Observação: sem comandos DROP/BEGIN/COMMIT e sem dados (exceto bootstrap de admin).
-- ================================================

create extension if not exists "uuid-ossp";
create extension if not exists pgcrypto;

-- =========================
-- CLIENTES
-- =========================
create table if not exists public.clientes (
  telefone text primary key,
  nome text not null,
  endereco text, -- adicionado
  ludocoins_saldo numeric(12,2) not null default 0,
  opt_in_whatsapp boolean not null default true,
  created_at timestamptz not null default now()
);

-- =========================
-- JOGOS
-- =========================
create table if not exists public.jogos (
  id uuid primary key default gen_random_uuid(),
  nome text not null,
  nome_evento text,
  preco_brl numeric(12,2) not null check (preco_brl >= 0),
  status text not null check (status in ('DISPONIVEL','PRE-VENDA')),
  sku text unique,
  categoria text,
  ativo boolean not null default true,
  created_at timestamptz not null default now()
);

-- =========================
-- CONTAINERS
-- =========================
create table if not exists public.containers (
  id text primary key,
  telefone_cliente text not null references public.clientes(telefone) on delete cascade,
  status text not null check (status in ('ABERTO','PENDENTE','FECHADO','ENVIADO','AGUARDANDO_PAGAMENTO')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- no máximo 1 ABERTO por telefone
create unique index if not exists ux_one_open_container_per_phone
on public.containers(telefone_cliente)
where status = 'ABERTO';

-- =========================
-- MOVIMENTOS
-- =========================
create table if not exists public.movimentos (
  id uuid primary key default gen_random_uuid(),
  tipo text not null check (tipo in ('COMPRA','LISTINHA')),
  telefone_cliente text not null references public.clientes(telefone),
  jogo_id uuid not null references public.jogos(id),
  preco_aplicado_brl numeric(12,2) not null,
  container_id text not null references public.containers(id),
  container_item_id uuid,
  created_at timestamptz not null default now()
);

alter table public.movimentos
  add constraint if not exists uq_mov_container_item unique (container_item_id);

-- =========================
-- CONTAINER_ITENS
-- =========================
create table if not exists public.container_itens (
  id uuid primary key default gen_random_uuid(),
  container_id text not null references public.containers(id) on delete cascade,
  jogo_id uuid not null references public.jogos(id),
  origem text not null check (origem in ('COMPRA','LISTINHA')),
  status_item text not null check (status_item in ('RESERVADO','DISPONIVEL','PRE-VENDA','RESGATADO')),
  preco_aplicado_brl numeric(12,2) not null default 0,
  elegivel_ludocoin boolean not null default false,
  movimento_id uuid references public.movimentos(id),
  created_at timestamptz not null default now()
);

-- trigger: elegibilidade automática (origem=LISTINHA)
create or replace function public.trg_container_item_elegibilidade()
returns trigger language plpgsql as $$
begin
  new.elegivel_ludocoin := (new.origem = 'LISTINHA');
  return new;
end;
$$;

create trigger if not exists tgi_container_item_elegibilidade
before insert or update on public.container_itens
for each row execute function public.trg_container_item_elegibilidade();

-- =========================
-- LUDOCOIN_TRANSACOES
-- =========================
create table if not exists public.ludocoin_transacoes (
  id uuid primary key default gen_random_uuid(),
  telefone_cliente text not null references public.clientes(telefone),
  tipo text not null check (tipo in ('CREDITO_CONVERSAO','DEBITO_UTILIZACAO','AJUSTE')),
  valor numeric(12,2) not null,
  referencia_item_id uuid,
  observacao text,
  created_at timestamptz not null default now()
);

-- =========================
-- ENVIOS
-- =========================
create table if not exists public.envios (
  id uuid primary key default gen_random_uuid(),
  container_id text not null references public.containers(id),
  telefone_cliente text not null references public.clientes(telefone),
  nome_cliente text not null,
  status_envio text not null check (status_envio in ('PENDENTE','EM_PREPARACAO','AGUARDANDO_PAGAMENTO','ENVIADO','CANCELADO')),
  itens_snapshot_json jsonb not null,
  created_at timestamptz not null default now()
);

-- =========================
-- LOGS/AUDITORIA
-- =========================
create table if not exists public.whatsapp_logs (
  id uuid primary key default gen_random_uuid(),
  telefone text not null,
  direcao text not null check (direcao in ('IN','OUT')),
  conteudo text not null,
  contexto_json jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.auditoria (
  id uuid primary key default gen_random_uuid(),
  usuario text,
  acao text not null,
  detalhes jsonb,
  created_at timestamptz not null default now()
);

-- =========================
-- CHAT STATES
-- =========================
create table if not exists public.chat_states (
  telefone text primary key,
  state text not null,
  data jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

create or replace function public.trg_chat_states_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at := now();
  return new;
end;
$$;

create trigger if not exists tgu_chat_states_updated_at
before insert or update on public.chat_states
for each row execute function public.trg_chat_states_updated_at();

-- =========================
-- VIEW: Passivo de LudoCoins
-- =========================
create or replace view public.v_passivo_ludocoins as
select coalesce(sum(ludocoins_saldo),0) as total_ludocoins from public.clientes;

-- =========================
-- RPC: Conversão de item → LudoCoins
-- =========================
create or replace function public.convert_item_to_ludocoins(p_item_id uuid, p_atendente text)
returns json language plpgsql as $$
declare
  v_item record;
  v_valor numeric(12,2);
begin
  select ci.*, c.telefone_cliente into v_item
  from public.container_itens ci
  join public.containers c on c.id = ci.container_id
  where ci.id = p_item_id
  for update;
  if not found then
    raise exception 'Item não encontrado';
  end if;
  if v_item.origem <> 'LISTINHA' then
    raise exception 'Item não é de LISTINHA';
  end if;
  if v_item.status_item not in ('DISPONIVEL','PRE-VENDA') then
    raise exception 'Item não elegível (status=%).', v_item.status_item;
  end if;

  v_valor := round(v_item.preco_aplicado_brl * 0.85, 2);

  update public.clientes
     set ludocoins_saldo = ludocoins_saldo + v_valor
   where telefone = v_item.telefone_cliente;

  insert into public.ludocoin_transacoes (telefone_cliente, tipo, valor, referencia_item_id, observacao)
  values (v_item.telefone_cliente, 'CREDITO_CONVERSAO', v_valor, v_item.id, 'Conversão 85%');

  update public.container_itens
     set status_item = 'RESGATADO'
   where id = v_item.id;

  insert into public.auditoria (usuario, acao, detalhes)
  values (p_atendente, 'CONVERSAO_LUDOCOINS', json_build_object('item_id', v_item.id, 'valor', v_valor));

  return json_build_object('ok', true, 'valor', v_valor);
end;
$$;

-- =========================
-- CONFIGURAÇÕES
-- =========================
create table if not exists public.configuracoes (
  id int primary key default 1,
  numero_recebimento_comprovantes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- =========================
-- AUTENTICAÇÃO (DB) — usuários + RPCs
-- =========================
create table if not exists public.usuarios (
  email text primary key,
  password_hash text not null,
  role text not null check (role in ('admin','normal')),
  nome text,
  created_at timestamptz not null default now()
);

create or replace function public.auth_create_user(
  p_email    text,
  p_password text,
  p_role     text,
  p_nome     text
) returns json language plpgsql as $$
declare r json;
begin
  insert into public.usuarios(email, password_hash, role, nome)
  values (
    lower(p_email),
    crypt(p_password, gen_salt('bf')),
    case when lower(p_role)='admin' then 'admin' else 'normal' end,
    nullif(p_nome,'')
  )
  on conflict (email) do update set
    role = excluded.role,
    nome = coalesce(excluded.nome, public.usuarios.nome);

  select json_build_object('email', u.email, 'role', u.role, 'nome', u.nome)
    into r
    from public.usuarios u
   where u.email = lower(p_email);
  return r;
end;
$$;

create or replace function public.auth_verify_user(
  p_email    text,
  p_password text
) returns json language plpgsql as $$
declare r json;
begin
  select json_build_object('email', u.email, 'role', u.role, 'nome', u.nome)
    into r
    from public.usuarios u
   where u.email = lower(p_email)
     and u.password_hash = crypt(p_password, u.password_hash);
  return r; -- null quando inválido
end;
$$;

-- -- Bootstrap de admin inicial (opcional, mantido aqui por conveniência)
-- DO $$
-- BEGIN
--   IF NOT EXISTS (SELECT 1 FROM public.usuarios) THEN
--     INSERT INTO public.usuarios(email, password_hash, role, nome)
--     VALUES ('admin@local', crypt('admin123', gen_salt('bf')), 'admin', 'Administrador');
--   END IF;
-- END $$;

-- =========================
-- (Consultas rápidas opcionais, úteis em dev)
-- =========================
-- select 'clientes' as t, count(*) from public.clientes
-- union all select 'jogos', count(*) from public.jogos
-- union all select 'containers', count(*) from public.containers
-- union all select 'container_itens', count(*) from public.container_itens
-- union all select 'movimentos', count(*) from public.movimentos
-- union all select 'ludocoin_transacoes', count(*) from public.ludocoin_transacoes
-- union all select 'envios', count(*) from public.envios
-- order by 1;

-- select j.nome, ci.origem, ci.status_item, ci.preco_aplicado_brl
-- from public.container_itens ci
-- join public.jogos j on j.id = ci.jogo_id
-- where ci.container_id = '558581482543-SEED1'
-- order by j.nome;
