ALTER TABLE games
ADD COLUMN finished_at_tmp DATE;

Update games
SET finished_at_tmp = to_date(finished_at, 'DD.MM.YYYY');

ALTER TABLE games
DROP COLUMN finished_at;

ALTER TABLE games
RENAME COLUMN finished_at_tmp TO finished_at;