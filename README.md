docker --version;
docker-compose down;
docker-compose up --build -d;

Get the IP for nef_db host
docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' nef_db


SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE nef_db.questions;
TRUNCATE TABLE nef_db.categories;
SET FOREIGN_KEY_CHECKS = 1;

DEPLOYMENT
PythonAnywhere - without Docker
