#!/usr/bin/env python3
from migrate.versioning.shell import main
from util import mysql_connection_string

if __name__ == '__main__':
    main(repository='database', url=mysql_connection_string(), debug='False')
