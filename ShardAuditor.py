import MySQLdb
import re
import pprint
from settings import SHARD_AUDITOR_SETTINGS as CONFIG
import datetime


pprinter = pprint.PrettyPrinter(indent=4)




class ShardAuditor:
    
    def __init__(self):
        self.connected = False
        self.db = None
        self.baseline_table_data = {}
        self.baseline_tables = []
        self.debug = True
        self.metadb = None
        self.metadbconn = None
        self.schema_regex = None
        curtime = datetime.datetime.now()
        self.runtime = str(curtime)
        self.custom_log_error_function = None


    def metadb_config(self, user, password, host, port, schema):
        self.metadbconn = MySQLdb.connect(host=host, port=port, user=user, passwd=password, db=schema)
        self.metadb = self.metadbconn.cursor()
        # self deploys the table if it does not already exist
        self.metadb.execute(
            """CREATE TABLE IF NOT EXISTS `shard_auditor_errors` (
              `entity_type` varchar(255) DEFAULT NULL,
              `error_type` varchar(255) DEFAULT NULL,
              `host` varchar(255) DEFAULT NULL,
              `port` int(11) DEFAULT NULL,
              `schema` varchar(255) DEFAULT NULL,
              `table` varchar(255) DEFAULT NULL,
              `entity` varchar(255) DEFAULT NULL,
              `runtime` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
              `notes` varchar(255) DEFAULT NULL
            )"""
        )


    def debug_enabled(self, enabled=True):
        self.debug = enabled


    def connect(self, user, password, host, port, database=""):
        db = MySQLdb.connect(host=host, port=port, user=user, passwd=password, db=database)
        self.db = db.cursor()


    def load_baseline_schema(self, user, password, host, port, schema):
        self.connect(user, password, host, port, schema)
        self.baseline_tables = self.get_tables(schema)
        self.baseline_table_data = {}
        for table in self.baseline_tables:
            self.baseline_table_data[table] = self.get_table_mapping(schema, table)

    def log_error(self, entity_type, error_type, host, port, schema, table, entity, notes):
        if self.custom_log_error_function:
            self.custom_log_error_function(entity_type, error_type, host, port, schema, table, entity, notes)
        if self.debug:
            output_string = "%s %s ERROR %s:%s %s" % (error_type, entity_type, host, port, schema)
            if table:
                output_string = "%s.%s" % (output_string, table)
            if entity:
                output_string = "%s.%s" % (output_string, entity)
            if notes:
                output_string = "%s %s" % (output_string, notes)
            print output_string
        if self.metadb:
            self.metadb.execute("""insert into shard_auditor_errors
                                    (`entity_type`,`error_type`,`host`,`port`,`schema`,`table`,`entity`, `runtime`,`notes`)
                                    values(%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                                (entity_type, error_type, host, port, schema, table, entity, self.runtime, notes)
                                )
            self.metadbconn.commit()
            pass

    def audit_host(self, user, password, host, port = 3306):
        try:
            self.connect(user, password, host, port)
            hostconfig = {}
            if 'hosts' in CONFIG:
                if host + ":" + str(port) in CONFIG['hosts']:
                    hostconfig = CONFIG['hosts'][host + ":" + str(port)]
            hostconfig["host"] = host
            hostconfig["port"] = port

            schemas = self.get_schemas()
        except:
            self.log_error("AUDITOR", "CONNECTERROR", host, port, None, None, None, "Unable to connect to host to run audit")
            return

        for schema in schemas:
            if 'ignore_schemas' in host and schema in host['ignore_schemas']:
                continue
            if 'ignore_schemas' in CONFIG and schema in CONFIG['ignore_schemas']:
                continue
            audit_table_data = {}
            # this catches a schema that may need to be upgraded, see: http://www.coretanium.net/mysql-server-5-1-upgrade-mysql50
            if re.match(r'#mysql50#', schema):
                self.log_error("MYSQL", "UPGRADE", host, port, schema, None, None, "may need to run \"ALTER DATABASE " + schema + " UPGRADE DATA DIRECTORY NAME\"")
                #print "MYSQL UPGRADE ERROR: may need to run \"ALTER DATABASE `" + schema + "` UPGRADE DATA DIRECTORY NAME\" on " + host['host']
                continue

            if self.schema_regex and not re.match(self.schema_regex, schema):
                continue

            tables = self.get_tables(schema)
            for table in tables:
                audit_table_data[table] = self.get_table_mapping(schema, table)
            self.audit_tables(self.baseline_table_data, audit_table_data, hostconfig, schema)


    def audit_schema(self, user, password, host, schema, port = 3306):
        try:
            self.connect(user, password, host, port)
            hostconfig = {}
            if 'hosts' in CONFIG:
                if host + ":" + str(port) in CONFIG['hosts']:
                    hostconfig = CONFIG['hosts'][host + ":" + str(port)]
            hostconfig["host"] = host
            hostconfig["port"] = port

        except:
            self.log_error("AUDITOR", "CONNECTERROR", host, port, None, None, None, "Unable to connect to host to run audit")
            return

        audit_table_data = {}

        tables = self.get_tables(schema)
        for table in tables:
            audit_table_data[table] = self.get_table_mapping(schema, table)
        self.audit_tables(self.baseline_table_data, audit_table_data, hostconfig, schema)


    def audit_tables(self, baseline_schema_data, audit_schema_data, hostconfig, schemaname):
        if 'ignore_tables' in CONFIG:
            gig_tables = CONFIG['ignore_tables']
        else:
            gig_tables = {}
        if 'ignore_tables' in hostconfig.keys():
            ig_tables = hostconfig['ignore_tables']
        else:
            ig_tables = {}

        # look for missing tables
        for table in baseline_schema_data:
            # check if table should be ignored and skip if so
            if table in ig_tables.keys():
                if 'ignore_all' in ig_tables[table].keys() and ig_tables[table]['ignore_all'] is True:
                    continue
            if table in gig_tables.keys():
                if 'ignore_all' in gig_tables[table].keys() and gig_tables[table]['ignore_all'] is True:
                    continue

            if table not in audit_schema_data.keys():
                self.log_error("TABLE", "MISSING", hostconfig['host'], hostconfig['port'], schemaname, table, None, "not found")
                #print "MISSING TABLE ERROR: " + table + " not found in " + schemaname + " on " + hostconfig['host']
            else:
                if audit_schema_data[table]['engine'] != baseline_schema_data[table]['engine']:
                    self.log_error("TABLE", "ENGINE", hostconfig['host'], hostconfig['port'], schemaname, table, None, "is " + audit_schema_data[table]['engine'] + " and should be " + baseline_schema_data[table]['engine'])
                    #print "TABLE ENGINE ERROR: on " + hostconfig['host'] + ": engine is " + \
                    #      audit_schema_data[table]['engine'] + " and should be " + baseline_schema_data[table]['engine']
                self.audit_table(baseline_schema_data[table], audit_schema_data[table], hostconfig, schemaname, table)

        # look for extraneous tables
        for table in audit_schema_data:
            # check if table should be ignored and skip if so
            if table in ig_tables.keys():
                if 'ignore_all' in ig_tables[table].keys() and ig_tables[table]['ignore_all'] is True:
                    continue
            if table in gig_tables.keys():
                if 'ignore_all' in gig_tables[table].keys() and gig_tables[table]['ignore_all'] is True:
                    continue

            if table not in baseline_schema_data.keys():
                self.log_error("TABLE", "EXTRANEOUS", hostconfig['host'], hostconfig['port'], schemaname, table, None, None)
                #print "EXTRANEOUS TABLE ERROR: " + table + " found in " + schemaname + " on " + hostconfig['host']




    def audit_table(self, baseline_table_data, audit_table_data, hostconfig, schemaname, tablename):
        if 'ignore_tables' in CONFIG and tablename in CONFIG['ignore_tables']:
            gig_table = CONFIG['ignore_tables'][tablename]
        else:
            gig_table = {}
        if 'ignore_tables' in hostconfig.keys() and tablename in hostconfig['ignore_tables']:
            ig_table = hostconfig['ignore_tables'][tablename]
        else:
            ig_table = {}



        base_cols = baseline_table_data['columns'].keys()
        audit_cols = audit_table_data['columns'].keys()

        # remove ignored columns from list of columns to check
        if 'columns' in ig_table:
            for column in ig_table['columns']:
                if column in base_cols:
                    base_cols.remove(column)
                if column in audit_cols:
                    audit_cols.remove(column)
        if 'columns' in gig_table:
            for column in gig_table['columns']:
                if column in base_cols:
                    base_cols.remove(column)
                if column in audit_cols:
                    audit_cols.remove(column)

        if base_cols != audit_cols and sorted(base_cols) == sorted(audit_cols):
            self.log_error("COLUMN", "ORDER", hostconfig['host'], hostconfig['port'], schemaname, tablename, None, "columns out of order")
            #print "COLUMN ORDER ERROR: Columns are out of order on " + hostconfig['host'] + " " + schemaname + "." + tablename

        for col in base_cols:
            if col not in audit_cols:
                self.log_error("COLUMN", "MISSING", hostconfig['host'], hostconfig['port'], schemaname, tablename, col, "not found")
                #print "MISSING COLUMN ERROR: " + hostconfig['host'] + " " + schemaname + "." + tablename + "." + col + " not found"
            else:
                if audit_table_data['columns'][col]['type'] != baseline_table_data['columns'][col]['type']:
                    self.log_error("COLUMN", "TYPE", hostconfig['host'], hostconfig['port'], schemaname, tablename, col, "defined as " + audit_table_data['columns'][col]['type'] + " but should be " + baseline_table_data['columns'][col]['type'])
                    #print "COLUMN TYPE ERROR: " + hostconfig['host'] + " " + schemaname + "." + tablename + "." + col \
                    #      + " defined as " + audit_table_data['columns'][col]['type'] + " but should be " + baseline_table_data['columns'][col]['type']
                if audit_table_data['columns'][col]['extra'] != baseline_table_data['columns'][col]['extra']:
                    self.log_error("COLUMN", "TYPE", hostconfig['host'], hostconfig['port'], schemaname, tablename, col, "defined as " + audit_table_data['columns'][col]['extra'] + " but should be " + baseline_table_data['columns'][col]['extra'])
                    #print "COLUMN TYPE ERROR: " + hostconfig['host'] + " " + schemaname + "." + tablename + "." + col \
                    #      + " defined as " + audit_table_data['columns'][col]['extra'] + " but should be " + baseline_table_data['columns'][col]['extra']

        for col in audit_cols:
            if col not in base_cols:
                self.log_error("COLUMN", "EXTRANEOUS", hostconfig['host'], hostconfig['port'], schemaname, tablename, col, "found extra")
                #print "EXTRANEOUS COLUMN ERROR: " + hostconfig['host'] + " " + schemaname + "." + tablename + "." + col + " found extra"

        for index in baseline_table_data['indexes']:
            if index not in audit_table_data['indexes']:
                self.log_error("INDEX", "MISSING", hostconfig['host'], hostconfig['port'], schemaname, tablename, index, "not found")
                #print "INDEX MISSING ERROR: " + hostconfig['host'] + " " + schemaname + "." + tablename + "." + index + " not found"
            else:
                if baseline_table_data['indexes'][index]['type'] != audit_table_data['indexes'][index]['type']:
                    base_idx_type = baseline_table_data['indexes'][index]['type'] if baseline_table_data['indexes'][index]['type'] is not None else "regular"
                    audit_idx_type = audit_table_data['indexes'][index]['type'] if audit_table_data['indexes'][index]['type'] is not None else "regular"
                    self.log_error("INDEX", "TYPE", hostconfig['host'], hostconfig['port'], schemaname, tablename, index, " defined as " + audit_idx_type + " but should be " + base_idx_type)
                    #print "INDEX TYPE ERROR: " + hostconfig['host'] + " " + schemaname + "." + tablename + "." + index + " defined as " \
                    #      + audit_idx_type + " but should be " + base_idx_type
                if baseline_table_data['indexes'][index]['cols'] != audit_table_data['indexes'][index]['cols']:
                    self.log_error("INDEX", "COLUMN", hostconfig['host'], hostconfig['port'], schemaname, tablename, index, " on " + audit_table_data['indexes'][index]['cols'] + " but should be on " + baseline_table_data['indexes'][index]['cols'])
                    #print "INDEX COLUMN ERROR: " + hostconfig['host'] + " " + schemaname + "." + tablename + "." + index + " on " \
                    #      + audit_table_data['indexes'][index]['cols'] + " but should be on " + baseline_table_data['indexes'][index]['cols']

        for index in audit_table_data['indexes']:
            if index not in baseline_table_data['indexes']:
                self.log_error("INDEX", "EXTRA", hostconfig['host'], hostconfig['port'], schemaname, tablename, index, "found extra")
                #print "EXTRA INDEX ERROR: " + hostconfig['host'] + " " + schemaname + "." + tablename + "." + index + " found extra"


    def get_schemas(self):
        self.db.execute("show databases")
        rows = self.db.fetchall()
        schemas = []
        for row in rows:
            schema = row[0]
            schemas.append(schema)
        return schemas


    def get_tables(self, schema):
        self.db.execute("show tables in " + schema)
        rows = self.db.fetchall()
        tables = []
        for row in rows:
            table = row[0]
            tables.append(table)
        return tables


    def get_table_mapping(self, schema, table):
        self.db.execute("show create table " + schema + "." + table)
        res = self.db.fetchone()
        show = res[1]
        create_parts = show.split("\n")
        if re.match('CREATE TABLE', show):
            engine = None
            key_entries = {}
            col_entries = {}
            for i in range(1, len(create_parts)):

                # process column definitions
                if re.match(r'\s*`', create_parts[i]):
                    m = re.match(r'\s*`(?P<name>.*?)`\s*(?P<type>\w+(:?\([0-9]*\))?)\s*(?P<extra>.*?),?', create_parts[i])
                    col_entries[m.group('name')] = {
                        'type': m.group('type'),
                        'extra': m.group('extra')
                    }

                # get indexes
                if re.match(r'\s*(PRIMARY|FULLTEXT|UNIQUE)?\s*KEY', create_parts[i]):
                    m = re.match(r'\s*(?P<type>PRIMARY|FULLTEXT|UNIQUE)?\s*KEY\s*(:?`(?P<ix_name>.*?)`)?\s*\((?P<cols>.*?)\).*?', create_parts[i])

                    if m.group('type') == 'PRIMARY':
                        key_entries["PRIMARY"] = {
                            'type': 'PRIMARY',
                            'cols': m.group('cols')
                        }
                    else:
                        key_entries[m.group('ix_name')] = {
                            'type': m.group('type'),
                            'cols': m.group('cols')
                        }

                if re.match(r'\) ENGINE', create_parts[i]):
                    m = re.match(r'.*?ENGINE=(?P<engine>\w+)\s.*', create_parts[i])
                    engine = m.group('engine')

            table_data = {
                "columns": col_entries,
                "indexes": key_entries,
                "engine": engine
            }
    
        return table_data

    # allows you to set a regex to identify schemas to process
    def schema_name_pattern(self, schema_regex):
        self.schema_regex = schema_regex


    # function should have the same arguments as the log_error function
    def set_custom_log_error_callback(self, function):
        self.custom_log_error_function = function