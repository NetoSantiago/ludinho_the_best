-- =====================================================
-- LUDINHO • RESET TOTAL (limpa banco para recriar schema/seed)
-- Uso: rode este script e depois execute schema_full.sql e mega_seed_full.sql
-- Seguro para rodar múltiplas vezes (IF EXISTS + CASCADE)
-- =====================================================

BEGIN;

-- 1) Views (antes, para evitar dependências)
DROP VIEW IF EXISTS public.v_passivo_ludocoins;

-- 2) Tabelas do projeto (CASCADE remove FKs, triggers e constraints dependentes)
DROP TABLE IF EXISTS public.auditoria              CASCADE;
DROP TABLE IF EXISTS public.whatsapp_logs          CASCADE;
DROP TABLE IF EXISTS public.envios                 CASCADE;
DROP TABLE IF EXISTS public.ludocoin_transacoes    CASCADE;
DROP TABLE IF EXISTS public.container_itens        CASCADE;
DROP TABLE IF EXISTS public.movimentos             CASCADE;
DROP TABLE IF EXISTS public.containers             CASCADE;
DROP TABLE IF EXISTS public.jogos                  CASCADE;
DROP TABLE IF EXISTS public.chat_states            CASCADE;
DROP TABLE IF EXISTS public.clientes               CASCADE;
DROP TABLE IF EXISTS public.configuracoes          CASCADE;

-- 3) Funções explícitas do projeto (caso algo tenha sobrado após os DROPs)
DROP FUNCTION IF EXISTS public.trg_chat_states_updated_at()          CASCADE;
DROP FUNCTION IF EXISTS public.trg_container_item_elegibilidade()    CASCADE;
DROP FUNCTION IF EXISTS public.convert_item_to_ludocoins(uuid, text) CASCADE;

COMMIT;

-- Pronto! Agora rode:
--   1) schema_full.sql
--   2) mega_seed_full.sql
