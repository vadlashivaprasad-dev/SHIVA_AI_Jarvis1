-- Initialize the main application database (must run in the postgres server context).

-- Important: this file is executed only when the Postgres container initializes the
-- data directory (i.e., first boot). If you already have volumes mounted with an
-- existing data dir, you must recreate the container/volume for this to run.

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
    RAISE NOTICE 'init: creating shivaai_db';
    EXECUTE 'CREATE DATABASE shivaai_db';
  END IF;
END $$;






