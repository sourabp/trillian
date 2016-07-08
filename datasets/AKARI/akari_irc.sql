CREATE TABLE dataset_akari.irc (
    objid bigint NOT NULL,
    objname text,
    ra numeric,
    "dec" numeric,
    poserrmj numeric,
    poserrmi numeric,
    poserrpa numeric,
    flux09 numeric,
    flux18 numeric,
    ferr09 numeric,
    ferr18 numeric,
    fqual09 integer,
    fqual18 integer,
    flags09 text,
    flags18 text,
    nscanc09 integer,
    nscanc18 integer,
    nscanp09 integer,
    nscanp18 integer,
    mconf09 integer,
    mconf18 integer,
    ndens09 integer,
    ndens18 integer,
    extended09 integer,
    extended18 integer,
    mean_ab09 numeric,
    mean_ab18 numeric,
    ndata_pos integer,
    ndata09 integer,
    ndata18 integer
);
