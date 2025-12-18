-- ================================================
-- LUDINHO • MEGA SEED COMPLETO (consolidado 010 + 011)
-- Popular base com dados de teste: INSERT/UPDATE/DELETE/etc.
-- Execute após aplicar o schema completo.
-- ================================================

BEGIN;
insert into public.clientes (telefone, nome, ludocoins_saldo) values
 ('558581482543','Santiago Teste',0),
 ('558899000111','Cliente Demo',50),
 ('558899000222','Ana Jogadora',10),
 ('558899000333','Bruno Estratégia',0),
 ('558899000444','Carla Família',0),
 ('558899000555','Diego Euro',0)
on conflict (telefone) do update set nome = excluded.nome;

insert into public.jogos (nome, nome_evento, preco_brl, status, sku, categoria) values
  ('Azul','Azul - Listinha',250,'DISPONIVEL','AZUL-001','Abstrato'),
  ('Ticket to Ride','TTR - Listinha',320,'DISPONIVEL','TTR-001','Família'),
  ('Catan','Catan - Listinha',299.90,'PRE-VENDA','CAT-001','Euro'),
  ('Dixit','Dixit - Listinha',199.90,'DISPONIVEL','DIX-001','Família'),
  ('Wingspan','Wingspan - Listinha',420,'PRE-VENDA','WIN-001','Engine'),
  ('Splendor','Splendor - Listinha',230,'DISPONIVEL','SPL-001','Engine'),
  ('Carcassonne','Carcassonne - Listinha',189.90,'DISPONIVEL','CARC-001','Tile'),
  ('Pandemic','Pandemic - Listinha',280,'DISPONIVEL','PAND-001','Coop'),
  ('7 Wonders','7 Wonders - Listinha',310,'DISPONIVEL','7W-001','Draft'),
  ('Gloomhaven','Gloomhaven - Listinha',999,'PRE-VENDA','GH-001','Dungeon'),
  ('Root','Root - Listinha',420,'DISPONIVEL','ROOT-001','Guerra'),
  ('Terraforming Mars','TM - Listinha',410,'DISPONIVEL','TM-001','Engine'),
  ('Everdell','Everdell - Listinha',450,'PRE-VENDA','EVE-001','Worker'),
  ('Scythe','Scythe - Listinha',520,'DISPONIVEL','SCY-001','4X'),
  ('Patchwork','Patchwork - Listinha',140,'DISPONIVEL','PAT-001','2P'),
  ('Brass: Birmingham','Brass - Listinha',650,'PRE-VENDA','BRASS-001','Econ'),
  ('Spirit Island','SI - Listinha',480,'DISPONIVEL','SI-001','Coop'),
  ('Azul Summer','Azul Summer - Listinha',270,'PRE-VENDA','AZUL-002','Abstrato'),
  ('Codenames','Codenames - Listinha',120,'DISPONIVEL','CODE-001','Party'),
  ('Hive','Hive - Listinha',160,'DISPONIVEL','HIVE-001','2P')
on conflict (sku) do update
  set nome = excluded.nome,
      nome_evento = excluded.nome_evento,
      preco_brl = excluded.preco_brl,
      status = excluded.status,
      categoria = excluded.categoria,
      ativo = true;

insert into public.containers (id, telefone_cliente, status) values
  ('558581482543-SEED1','558581482543','ABERTO'),
  ('558899000111-SEED1','558899000111','ABERTO'),
  ('558899000222-SEED1','558899000222','ABERTO'),
  ('558899000333-SEED1','558899000333','ABERTO'),
  ('558899000444-SEED1','558899000444','ABERTO'),
  ('558899000555-SEED1','558899000555','ABERTO')
on conflict (id) do update set status = excluded.status, updated_at = now();

insert into public.container_itens (container_id, jogo_id, origem, status_item, preco_aplicado_brl)
select '558581482543-SEED1', j.id, x.origem, x.status_item, x.preco
from (values
  ('AZUL-001','COMPRA','DISPONIVEL',250.00),
  ('CAT-001','COMPRA','PRE-VENDA', 299.90),
  ('DIX-001','LISTINHA',  'DISPONIVEL',199.90),
  ('WIN-001','LISTINHA',  'PRE-VENDA', 420.00),
  ('TM-001', 'COMPRA','DISPONIVEL',410.00),
  ('CODE-001','LISTINHA', 'DISPONIVEL',120.00)
) as x(sku, origem, status_item, preco)
join public.jogos j on j.sku = x.sku;

insert into public.container_itens (container_id, jogo_id, origem, status_item, preco_aplicado_brl)
select '558899000111-SEED1', j.id, x.origem, x.status_item, x.preco
from (values
  ('TTR-001','COMPRA','DISPONIVEL',320.00),
  ('SPL-001','LISTINHA','DISPONIVEL',230.00),
  ('ROOT-001','LISTINHA','DISPONIVEL',420.00),
  ('GH-001','COMPRA','PRE-VENDA',999.00)
) as x(sku, origem, status_item, preco)
join public.jogos j on j.sku = x.sku;

insert into public.container_itens (container_id, jogo_id, origem, status_item, preco_aplicado_brl)
select '558899000222-SEED1', j.id, x.origem, x.status_item, x.preco
from (values
  ('EVE-001','COMPRA','PRE-VENDA',450.00),
  ('CARC-001','LISTINHA','DISPONIVEL',189.90),
  ('7W-001','COMPRA','DISPONIVEL',310.00)
) as x(sku, origem, status_item, preco)
join public.jogos j on j.sku = x.sku;

insert into public.container_itens (container_id, jogo_id, origem, status_item, preco_aplicado_brl)
select '558899000333-SEED1', j.id, x.origem, x.status_item, x.preco
from (values
  ('SCY-001','COMPRA','DISPONIVEL',520.00),
  ('BRASS-001','LISTINHA','PRE-VENDA',650.00),
  ('HIVE-001','LISTINHA','DISPONIVEL',160.00)
) as x(sku, origem, status_item, preco)
join public.jogos j on j.sku = x.sku;

insert into public.container_itens (container_id, jogo_id, origem, status_item, preco_aplicado_brl)
select '558899000444-SEED1', j.id, x.origem, x.status_item, x.preco
from (values
  ('PAT-001','COMPRA','DISPONIVEL',140.00),
  ('SI-001','LISTINHA','DISPONIVEL',480.00),
  ('PAND-001','COMPRA','DISPONIVEL',280.00)
) as x(sku, origem, status_item, preco)
join public.jogos j on j.sku = x.sku;

insert into public.container_itens (container_id, jogo_id, origem, status_item, preco_aplicado_brl)
select '558899000555-SEED1', j.id, x.origem, x.status_item, x.preco
from (values
  ('BRASS-001','COMPRA','PRE-VENDA',650.00),
  ('SCY-001','LISTINHA','DISPONIVEL',520.00),
  ('EVE-001','LISTINHA','PRE-VENDA',450.00)
) as x(sku, origem, status_item, preco)
join public.jogos j on j.sku = x.sku;

insert into public.movimentos (tipo, telefone_cliente, jogo_id, preco_aplicado_brl, container_id, container_item_id)
select
  ci.origem as tipo,
  c.telefone_cliente,
  ci.jogo_id,
  ci.preco_aplicado_brl,
  ci.container_id,
  ci.id as container_item_id
from public.container_itens ci
join public.containers c on c.id = ci.container_id
on conflict (container_item_id) do nothing;

insert into public.ludocoin_transacoes (telefone_cliente, tipo, valor, observacao) values
 ('558899000111','AJUSTE',20,'Bônus de boas-vindas'),
 ('558899000222','DEBITO_UTILIZACAO',5,'Uso em desconto'),
 ('558581482543','AJUSTE',10,'Crédito inicial')
on conflict do nothing;

update public.clientes set ludocoins_saldo = ludocoins_saldo + 20 where telefone='558899000111';

update public.clientes set ludocoins_saldo = greatest(ludocoins_saldo - 5,0) where telefone='558899000222';

update public.clientes set ludocoins_saldo = ludocoins_saldo + 10 where telefone='558581482543';

insert into public.envios (container_id, telefone_cliente, nome_cliente, status_envio, itens_snapshot_json)
select
  '558899000111-SEED1',
  '558899000111',
  'Cliente Demo',
  'PENDENTE',
  coalesce(
    jsonb_agg(
      jsonb_build_object(
        'jogo', j.nome,
        'origem', ci.origem,
        'status_item', ci.status_item,
        'preco_aplicado_brl', ci.preco_aplicado_brl
      )
    ), '[]'::jsonb
  )
from public.container_itens ci
join public.jogos j on j.id = ci.jogo_id
where ci.container_id = '558899000111-SEED1'
on conflict do nothing;

insert into public.envios (container_id, telefone_cliente, nome_cliente, status_envio, itens_snapshot_json)
select
  '558899000333-SEED1',
  '558899000333',
  'Bruno Estratégia',
  'EM_PREPARACAO',
  coalesce(
    jsonb_agg(
      jsonb_build_object(
        'jogo', j.nome,
        'origem', ci.origem,
        'status_item', ci.status_item,
        'preco_aplicado_brl', ci.preco_aplicado_brl
      )
    ), '[]'::jsonb
  )
from public.container_itens ci
join public.jogos j on j.id = ci.jogo_id
where ci.container_id = '558899000333-SEED1'
on conflict do nothing;

insert into public.envios (container_id, telefone_cliente, nome_cliente, status_envio, itens_snapshot_json)
select
  '558899000444-SEED1',
  '558899000444',
  'Carla Família',
  'ENVIADO',
  coalesce(
    jsonb_agg(
      jsonb_build_object(
        'jogo', j.nome,
        'origem', ci.origem,
        'status_item', ci.status_item,
        'preco_aplicado_brl', ci.preco_aplicado_brl
      )
    ), '[]'::jsonb
  )
from public.container_itens ci
join public.jogos j on j.id = ci.jogo_id
where ci.container_id = '558899000444-SEED1'
on conflict do nothing;

update public.containers
set created_at = now(), updated_at = now()
where id in (
  '558581482543-SEED1','558899000111-SEED1','558899000222-SEED1',
  '558899000333-SEED1','558899000444-SEED1','558899000555-SEED1'
);

insert into public.configuracoes (id) values (1)
on conflict (id) do nothing;
COMMIT;
