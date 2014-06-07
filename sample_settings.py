
# credentials to the database that contains the locator table
LOCATOR_DB_CREDENTIALS = {
    'user': 'root',
    'password': '',
    'host': 'localhost',
    'port': 3306,
    'dbname': 'shards',
}

# column values can be a string column name or can be valid sql that can be used in the select fields
# eg, if the fqdn is separated into separate host/sub/domain columns, you can set the value as a concat:  'host_col': 'concat(hostname,".",subdomain,".",domain)'
LOCATOR_TABLE = {
    # this is the table that can be used to lookup where shards are located
    'tablename': 'locator',
    # this is the schema name of the specific shard (this should be unique)
    'shardname_col': 'shard',
    # this is the column that holds the hostname or ip address of the host containing the shard
    'host_col': 'hostname',
    # column that holds the port number for the shard host
    'port_col': 'port',
    # the following slave configs can be set to "NULL" to disable this form of monitoring of single slave for pt-online-schema-change and enable normal --recursion-method based monitoring
    # this is the column that holds the hostname or ip address of the slave host containing the shard (used to make pt-online-schema-change only monitor one slave)
    'slave_host_col': "NULL",
    # column that holds the port number for the shard slave host port
    'slave_port_col': "NULL",
    # this is a where clause that gets appended to the select query from the shard locator table
    'where_clause': None
}
# The locator query is built as follows, so any values in LOCATOR_TABLE that make this a valid query and return the same number of columns in right order are valid
# sql = "select " + settings.LOCATOR_TABLE['shardname_col'] + ", " + settings.LOCATOR_TABLE['host_col'] + ", " \
#            + settings.LOCATOR_TABLE['port_col'] + " from " + settings.LOCATOR_TABLE['tablename'] + whereclause




# path to pt-online-schema-change, if it has been installed with a package manger then default should be /usr/local/bin, /usr/bin or /bin
PT_OSC = '/usr/local/bin/pt-online-schema-change'

# This contains default set of options to send to pt-online-schema-change
# if the option should not be sent at all, comment it out, if the option is a flag type option (no parameter), set its value to "" (empty string)
# the values of the enabled options are the default values for pt-osc
PT_OSC_OPTIONS = {
    'check-interval': 1,
    # 'chunk-index': 'some_index_name',  # index name should be provided
    # 'chunk-index-columns': 3, # 3 is not default
    'chunk-size': 1000,
    'chunk-size-limit': 4.0,
    'chunk-time': 0.5,
    'drop-new-table': '',
    #'nodrop-new-table': '',
    'drop-old-table': '',
    #'nodrop-old-table': '',
    'max-lag': 1,
    #'max-load': 'Threads_running=25',
    'progress': 'time,30',
    #'recurse': 1,  # 1 is not default
    'recursion-method': 'processlist,hosts',
}

# this is the shared credentials for all of the shard hosts, this account needs the privileges to do any ddl changes you wish to perform with the tool
SHARD_DB_CREDENTIALS = {
    'user': 'root',
    'password': '',
}

# this is the credentials for the host that holds the model shard schema
MODEL_SHARD_DB_CREDENTIALS = {
    'user': 'root',
    'password': '',
    'host': 'localhost',
    'port': 3306,
    'dbname': 'model_shard',
    # use these to set single specific host for pt-osc to monitor on replication
    'slave_host': None,
    'slave_port': None,
}


# these represent the default options and many can be overridden with command line options
OPTIONS = {
    'mode':             'direct',
    'concurrency':      1,
    'tablename':        None,
    'direct_query':     None,
    'online_alter':     None,
    'running_mode':     'dry-run',
    'filter_shards':    [],
    'ignore_errors':    False,

}

AUDITOR_LOGGING_ENABLED = False

AUDITOR_LOGDB_CREDENTIALS = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': '',
    'dbname': 'shard_auditor'
}

SHARD_AUDITOR_SETTINGS = {
}

