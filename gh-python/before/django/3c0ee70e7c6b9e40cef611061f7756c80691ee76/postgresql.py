"""
PostgreSQL database backend for Django.

Requires psycopg 1: http://initd.org/projects/psycopg1
"""

from django.core.db import base, typecasts
import psycopg as Database

DatabaseError = Database.DatabaseError

class DatabaseWrapper:
    def __init__(self):
        self.connection = None
        self.queries = []

    def cursor(self):
        from django.conf.settings import DATABASE_USER, DATABASE_NAME, DATABASE_HOST, DATABASE_PASSWORD, DEBUG, TIME_ZONE
        if self.connection is None:
            # Note that "host=" has to be last, because it might be blank.
            self.connection = Database.connect("user=%s dbname=%s password=%s host=%s" % \
                (DATABASE_USER, DATABASE_NAME, DATABASE_PASSWORD, DATABASE_HOST))
            self.connection.set_isolation_level(1) # make transactions transparent to all cursors
        cursor = self.connection.cursor()
        cursor.execute("SET TIME ZONE %s", [TIME_ZONE])
        if DEBUG:
            return base.CursorDebugWrapper(cursor, self)
        return cursor

    def commit(self):
        return self.connection.commit()

    def rollback(self):
        if self.connection:
            return self.connection.rollback()

    def close(self):
        if self.connection is not None:
            self.connection.close()
            self.connection = None

def dictfetchone(cursor):
    "Returns a row from the cursor as a dict"
    return cursor.dictfetchone()

def dictfetchmany(cursor, number):
    "Returns a certain number of rows from a cursor as a dict"
    return cursor.dictfetchmany(number)

def dictfetchall(cursor):
    "Returns all rows from a cursor as a dict"
    return cursor.dictfetchall()

def get_last_insert_id(cursor, table_name, pk_name):
    cursor.execute("SELECT CURRVAL('%s_%s_seq')" % (table_name, pk_name))
    return cursor.fetchone()[0]

# Register these custom typecasts, because Django expects dates/times to be
# in Python's native (standard-library) datetime/time format, whereas psycopg
# use mx.DateTime by default.
Database.register_type(Database.new_type((1082,), "DATE", typecasts.typecast_date))
Database.register_type(Database.new_type((1083,1266), "TIME", typecasts.typecast_time))
Database.register_type(Database.new_type((1114,1184), "TIMESTAMP", typecasts.typecast_timestamp))
Database.register_type(Database.new_type((16,), "BOOLEAN", typecasts.typecast_boolean))

OPERATOR_MAPPING = {
    'exact': '=',
    'iexact': 'ILIKE',
    'contains': 'LIKE',
    'icontains': 'ILIKE',
    'ne': '!=',
    'gt': '>',
    'gte': '>=',
    'lt': '<',
    'lte': '<=',
    'startswith': 'LIKE',
    'endswith': 'LIKE'
}

# This dictionary maps Field objects to their associated PostgreSQL column
# types, as strings. Column-type strings can contain format strings; they'll
# be interpolated against the values of Field.__dict__ before being output.
# If a column type is set to None, it won't be included in the output.
DATA_TYPES = {
    'AutoField':         'serial',
    'BooleanField':      'boolean',
    'CharField':         'varchar(%(maxlength)s)',
    'CommaSeparatedIntegerField': 'varchar(%(maxlength)s)',
    'DateField':         'date',
    'DateTimeField':     'timestamp with time zone',
    'EmailField':        'varchar(75)',
    'FileField':         'varchar(100)',
    'FloatField':        'numeric(%(max_digits)s, %(decimal_places)s)',
    'ImageField':        'varchar(100)',
    'IntegerField':      'integer',
    'IPAddressField':    'inet',
    'ManyToManyField':   None,
    'NullBooleanField':  'boolean',
    'PhoneNumberField':  'varchar(20)',
    'PositiveIntegerField': 'integer CHECK (%(name)s >= 0)',
    'PositiveSmallIntegerField': 'smallint CHECK (%(name)s >= 0)',
    'SlugField':         'varchar(50)',
    'SmallIntegerField': 'smallint',
    'TextField':         'text',
    'TimeField':         'time',
    'URLField':          'varchar(200)',
    'USStateField':      'varchar(2)',
    'XMLField':          'text',
}
