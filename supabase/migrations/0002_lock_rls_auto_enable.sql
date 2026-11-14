-- =====================================================================
-- 0002: take public.rls_auto_enable() off the Data API.
--
-- New Supabase projects ship an event trigger (ensure_rls) that turns on row level security for
-- every new table. Its function, public.rls_auto_enable(), is SECURITY DEFINER and executable by
-- anon and authenticated, so the Data API lists it at /rest/v1/rpc/rls_auto_enable and the security
-- advisor flags it (lints 0028 and 0029). Nobody calls it directly, and an event trigger fires
-- whether or not anyone holds EXECUTE (checked on scratch Postgres 16 on 14 Nov 2026), so revoke it.
--
-- Skipped where the function does not exist, as on scratch Postgres.
-- Applied to the Supabase project on 14 Nov 2026 as migration lock_rls_auto_enable. FROZEN.
-- =====================================================================

do $$ begin
  if to_regprocedure('public.rls_auto_enable()') is not null then
    revoke execute on function public.rls_auto_enable() from public, anon, authenticated;
  end if;
end $$;
