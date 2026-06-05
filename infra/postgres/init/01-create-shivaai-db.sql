-- Initialize the main application database (must run in the postgres server context).

DO $$
BEGIN
  -- Gateway expects database named `shivaai` (not `shivaai_db`).
  IF NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'shivaai') THEN
    RAISE NOTICE 'init: creating shivaai';
    EXECUTE 'CREATE DATABASE shivaai';
  ELSE
    RAISE NOTICE 'init: shivaai already exists';
  END IF;

  -- Backward compatibility: also create shivaai_db if older configs/migrations use it.
  IF NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'shivaai_db') THEN
    EXECUTE 'CREATE DATABASE shivaai_db';
  END IF;
END $$;




