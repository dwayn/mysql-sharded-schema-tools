mysql-sharded-schema-tools
===========================

Source URL: https://github.com/dwayn/mysql-sharded-schema-tools

# Introduction
This is a set of tools intended to aid in managing schema changes and auditing of schema in sharded mysql environments.

## Tools
* [mysql-sharded-schema-change](#mysql-sharded-schema-change)
 * Multithreaded tool to apply DDL changes to all shards while allowing control of concurrency per host
* [mysql-sharded-schema-auditor](#mysql-sharded-schema-auditor)
 * Tool to audit the schema definitions of all shards, compare them against the model shard and show any differences
* [mysql-sharded-schema-safe-drop](#mysql-sharded-schema-safe-drop)
 * Tool to drop inactive shards on hosts that brings protections against dropping active shards


## Architecture Requirements
There are a few assumptions that have been made with these tools.

1. Currently it is required that the mysql credentials are the same for all shards
2. Each shard is contained in a separate schema
3. A locator table exists that can be used to get the mapping of shard to host:port where it is located
4. There exists an extra schema that acts as the model shard
 * Modified first when doing a schema change to allow a point for the tool to bail out if there is an issue before attempting live nodes
 * This is the shard used for dry run operations for schema changes
 * Used by the auditor as the model schema to compare all of the shard schemas against
5. If you wish to do online alters, pt-online-schema-change must be installed on the host running the tool


# Installation & Configuration
* Clone this git repo
* pip install -r requirements.txt (this will either need to be done as root or within a virtualenv)
 * Currently the only requirements are mysql-python, argparse, and prettytable
* Copy sample_settings.py to settings.py
 * settings.py is in the .gitignore, this will allow you to update the code with a git pull without stomping on your config file
* Edit the credentials for the locator DB, shard DBs, and model shard DB
* Edit the LOCATOR_TABLE variables to allow the tool to query the mapping of shard to host/port
* Set the path to pt-online-schema-change if you intend to do online alters
* Suggested: Add the directory containing this repo to your path for convenience in using the tools


------------------------------------

# mysql-sharded-schema-change

## Introduction
This script is designed to aid in applying schema changes to sharded MySQL environments. It will run the schema changes in parallel
and allows control of the number of processes per server. Internally this is implemented using multiprocessing and a queue per
unique host/port of changes to make.

Operations currently supported:

* Table alters, either direct by mysql query or online using pt-onine-schema-change
* Create table
* Drop table
* Script
 * Note: The script support is very basic currently, and due to limitations of python's mysql adapter the script has to be split into
 its separate queries. The breaking up of the script is done by splitting the contents of the file on semicolons rather than query parsing, so be careful that
 you do not have semicolons in the script that are not query separators. I plan to reimplement the script handling to use the mysql
 command line client to execute them in the future.




## Operations

### Alter Table
Table alters are supported as direct queries or as online alters using pt-online-schema-change. Alters support --dry-run option for both
online and direct mode, and the dry-run will be run against the model shard.

Options required: --mode, --table, --alter

The --alter option should be the portion of an ALTER TABLE statement after the table name.

Example:

with an alter table of:

    ALTER TABLE foo ADD COLUMN bar INTEGER(11)

The options to directly apply the above alter using the tool would be:

    mysql-sharded-schema-change --table 'foo' --alter 'ADD COLUMN bar INTEGER(11)' --mode direct --execute

#### Options

      -t TABLE, --table TABLE
                            Name of table to alter
      --alter ALTER         Alter operations portion of an alter statement similar
                            to pt-online-schema-change, eg: "ADD COLUMN foo
                            VARCHAR(10) AFTER bar, DROP COLUMN baz, ENGINE=InnoDB"
      --type alter
                            Type of operation to run
      -n CONCURRENCY, --concurrency CONCURRENCY
                            Number of concurrent operations to run on each
                            database node
      --ignore-errors       Ignore errors on single shards and continue with the
                            DDL operation. Shards that had errors will be listed
                            in a report at the end of the run.
      --shards SHARD_NAME [SHARD_NAME ...]
                            Space separated list of shards to run against (used to
                            filter the global list from locator DB). Used for
                            rolling back or resuming changes that have only been
                            partially applied
      --dry-run             Perform a dry run of the operation on the model shard.
                            No direct DDL change statements will be run, and pt-
                            osc will be run with --dry-run
      --execute             execute the operation

#### Options for pt-online-schema-change
These options get passed to all pt-online-schema-change processes when
performing an online mode alter, refer to the documentation for pt-online-schema-
change. Some or all of theses options (and more) may be defined in the settings file as defaults for pt-osc.

      --check-interval CHECK_INTERVAL
      --chunk-size CHUNK_SIZE
      --chunk-size-limit CHUNK_SIZE_LIMIT
      --chunk-time CHUNK_TIME
      --drop-new-table
      --nodrop-new-table
      --drop-old-table
      --nodrop-old-table
      --max-lag MAX_LAG
      --progress PROGRESS
      --recursion-method RECURSION_METHOD
      --recurse RECURSE
      --max-load MAX_LOAD
      --chunk-index CHUNK_INDEX
      --chunk-index-columns CHUNK_INDEX_COLUMNS



### Create Table
Table creation is executed using direct queries and requires a CREATE TABLE statement to be provided.

Options required: --type=create, --create

Example:

With a create statement of

    CREATE TABLE `test1` (
      `id` int(11) NOT NULL AUTO_INCREMENT,
      `random` varchar(500) DEFAULT NULL,
      PRIMARY KEY (`id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8

The options to use the tool to create the table in all shards would be:

    mysql-sharded-schema-change --type create --execute --create '
    CREATE TABLE `test1` (
      `id` int(11) NOT NULL AUTO_INCREMENT,
      `random` varchar(500) DEFAULT NULL,
      PRIMARY KEY (`id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8'


#### Options

      -t TABLE, --table TABLE
                            Name of table to alter
      --create CREATE_STATEMENT
                            Create table statement to use for create type
      --type create
                            Type of operation to run
      -n CONCURRENCY, --concurrency CONCURRENCY
                            Number of concurrent operations to run on each
                            database node
      --ignore-errors       Ignore errors on single shards and continue with the
                            DDL operation. Shards that had errors will be listed
                            in a report at the end of the run.
      --shards SHARD_NAME [SHARD_NAME ...]
                            Space separated list of shards to run against (used to
                            filter the global list from locator DB). Used for
                            rolling back or resuming changes that have only been
                            partially applied
      --execute             execute the operation



### Drop Table
Table drops are executed using a direct query and only require a table name

Options required: --type=drop, --table

Example:

To drop table "foo" in all shards:

    mysql-sharded-schema-change --type drop --table foo --execute

#### Options

      -t TABLE, --table TABLE
                            Name of table to alter
      --type drop
                            Type of operation to run
      -n CONCURRENCY, --concurrency CONCURRENCY
                            Number of concurrent operations to run on each
                            database node
      --ignore-errors       Ignore errors on single shards and continue with the
                            DDL operation. Shards that had errors will be listed
                            in a report at the end of the run.
      --shards SHARD_NAME [SHARD_NAME ...]
                            Space separated list of shards to run against (used to
                            filter the global list from locator DB). Used for
                            rolling back or resuming changes that have only been
                            partially applied
      --execute             execute the operation



### Script
The script type operation takes a path to a sql script file that will be executed in every shard.

 * Note: The script support is very basic currently, and due to limitations of python's mysql adapter the script has to be split into
 its separate queries. The breaking up of the script is done by splitting the contents of the file on semicolons rather than query parsing, so be careful that
 you do not have semicolons in the script that are not query separators. I plan to reimplement the script handling to use the mysql
 command line client to execute them in the future.

Example:

    mysql-sharded-schema-change --type script --script /tmp/some_script.sql --execute

#### Options

      --script SCRIPT_PATH  Run provided SQL script against all shards
      --type script
                            Type of operation to run
      -n CONCURRENCY, --concurrency CONCURRENCY
                            Number of concurrent operations to run on each
                            database node
      --ignore-errors       Ignore errors on single shards and continue with the
                            DDL operation. Shards that had errors will be listed
                            in a report at the end of the run.
      --shards SHARD_NAME [SHARD_NAME ...]
                            Space separated list of shards to run against (used to
                            filter the global list from locator DB). Used for
                            rolling back or resuming changes that have only been
                            partially applied
      --execute             execute the operation




## Full Options List

### Options for mysql-sharded-schema-change

      -h, --help            show this help message and exit
      -t TABLE, --table TABLE
                            Name of table to alter
      --alter ALTER         Alter operations portion of an alter statement similar
                            to pt-online-schema-change, eg: "ADD COLUMN foo
                            VARCHAR(10) AFTER bar, DROP COLUMN baz, ENGINE=InnoDB"
      --create CREATE_STATEMENT
                            Create table statement to use for create type
      --script SCRIPT_PATH  Run provided SQL script against all shards
      -n CONCURRENCY, --concurrency CONCURRENCY
                            Number of concurrent operations to run on each
                            database node
      --type {alter,create,drop,script}
                            Type of operation to run
      --mode {direct,online}
                            Set the mode of alter to run the alter directly or use
                            pt-online-schema-change to perform online alter
                            (default defined in settings)
      --ignore-errors       Ignore errors on single shards and continue with the
                            DDL operation. Shards that had errors will be listed
                            in a report at the end of the run.
      --shards SHARD_NAME [SHARD_NAME ...]
                            Space separated list of shards to run against (used to
                            filter the global list from locator DB). Used for
                            rolling back or resuming changes that have only been
                            partially applied
      --dry-run             Perform a dry run of the operation on the model shard.
                            No direct DDL change statements will be run, and pt-
                            osc will be run with --dry-run
      --execute             execute the operation

### Options that get passed onto pt-online-schema-change

      options get passed to all pt-online-schema-change processes when
      performing online alter, refer to the documentation for pt-online-schema-
      change. Some or all of theses options may be defined in the settings file.

      --check-interval CHECK_INTERVAL
      --chunk-size CHUNK_SIZE
      --chunk-size-limit CHUNK_SIZE_LIMIT
      --chunk-time CHUNK_TIME
      --drop-new-table
      --nodrop-new-table
      --drop-old-table
      --nodrop-old-table
      --max-lag MAX_LAG
      --progress PROGRESS
      --recursion-method RECURSION_METHOD
      --recurse RECURSE
      --max-load MAX_LOAD
      --chunk-index CHUNK_INDEX
      --chunk-index-columns CHUNK_INDEX_COLUMNS


## Error Handling
mysql-sharded-schema-change will keep track of the shards that it has run the current operation against, the success or failure
of the operation and will provide this to you at the end of the run.

Successful run against all shards will output:

    DDL operation successfully completed on all shards

If any shards have errors or the script is interrupted the following will be output (along with detailed error states)

    DDL operation did not complete successfully on all shards

If there is any errors with the run, you will get output telling you which shards were successful, which had errors, which were skipped, and which
ones are in a state that is unknown, as well as the information that is known about the errors that occurred.

In an error state, one or more of the following output blocks may exist:

#### Errors received
This block give you the information that is known about what the errors were on the shards. Unfortunately, in the case of an
online alter, this is limited to the code that pt-online-schema-change exited with, so you will have to go back and read through
the stdout/stderr output from the pt-online-schema-change threads (this is all shipped back to main thread and output to stdout)

Online operation example:

    Errors received
    shard_6: pt-online-schema-change exited with exit code 255
    shard_0: pt-online-schema-change exited with exit code 255

Direct operation example:

    Errors received
    shard_6: (1146, "Table 'shard_6.test1' doesn't exist")
    shard_0: (1146, "Table 'shard_0.test1' doesn't exist")


#### Shards that had errors

    The following shards had errors
    -------------------------------
    shard_6 shard_0
    -------------------------------

These are shards that had an error processing the schema change. If you are using --ignore_errors, this list is very useful for going
back and reapplying the schema change to tables that had issues. If you do wish to reprocess these shards, you can copy the list of
shards provided here and paste them as the argument for the --shards option to another call to mysql-sharded-schema-change

    mysql-sharded-schema-change --shards shard_6 shard_0  ....


#### Shards that completed successfully

    The following shards completed successfully (this is the list to use if rollback is needed)
    -------------------------------------------------------------------------------------------
    shard_2 shard_1 model_shard
    -------------------------------------------------------------------------------------------

This is the list of shards that were successfully altered. If you do need to roll back this is the list that you will pass
to --shards to do your rollback operation.

#### Unknown state shards

    The following shards are in an unknown state due to abort
    ---------------------------------------------------------
    shard_7 shard_5
    ---------------------------------------------------------

Unknown state happens when the script is interrupted with CTRL+C, and you should check on any shards that are
in this state after interrupting a run. The reason these are unknown is because if you are running an online operation then pt-online-schema-change
may have left a temporary table and triggers behind when it exited, and if you are running a direct operation and CTRL+C more than
once (the first CTRL+C sets a flag to initiate shutdown, but does not kill the mysql connections) then the mysql
connections are killed and the queries abandoned, but the actual queries may or may not have actually stop and roll back as the server
may continue running the queries. Once you have verified the state and cleaned up as necessary, you can pass this list of shards to
the --shards option to attempt to apply the schema change to them again or do a roll back operation.

#### Shards not processed

    DDL operation was not attempted on the following shards
    -------------------------------------------------------
    shard_3 shard_4
    -------------------------------------------------------

This is the list of shards that were skipped due to an error (without setting --ignore-errors) or user interruption and have no schema changes applied. If you wish to
continue operation then you can pass this list of shards to the --shards option to continue the schema change operation on the list of shards.


----------------------------------------------------


# mysql-sharded-schema-auditor

## Introduction
Tool for auditing all of the shard schemas to check if they match the model shard.

This tool will identify:

* missing or extraneous tables
* missing or extraneous columns in tables
* column definitions that do not match the model shard schema definitions

## Configuration
The only extra configuration that this tool requires is AUDITOR_LOGDB_CREDENTIALS to be configured and AUDITOR_LOGGING_ENABLED set to
True if you want to log the results of auditor passes to a database table, otherwise, the tool will use all of the same configurations
that the mysql-sharded-schema-change tool uses.

## Operation
Standard operation of the tool is to run it with no options, but you can provide host, port and/or list of shards for the tool to audit

    mysql-sharded-schema-auditor

Example output:

    TYPE COLUMN ERROR localhost0:3306 shard_0.foonew2.random2 defined as int(11) but should be varchar(10)
    TYPE COLUMN ERROR localhost0:3306 shard_0.test2.random2 defined as int(11) but should be varchar(10)
    TYPE COLUMN ERROR localhost0:3306 shard_0.foonew.random2 defined as int(11) but should be varchar(10)
    EXTRANEOUS TABLE ERROR localhost0:3306 shard_0.shard_0
    EXTRANEOUS TABLE ERROR localhost0:3306 shard_1.shard_1
    EXTRANEOUS TABLE ERROR localhost1:3306 shard_2.shard_2
    MISSING COLUMN ERROR localhost1:3306 shard_3.foonew2.random2 not found
    MISSING COLUMN ERROR localhost1:3306 shard_3.test2.random2 not found
    MISSING COLUMN ERROR localhost1:3306 shard_3.foonew.random2 not found
    EXTRANEOUS TABLE ERROR localhost1:3306 shard_3.shard_3
    MISSING TABLE ERROR localhost0:3306 shard_4.test1 not found
    MISSING TABLE ERROR localhost0:3306 shard_4.foo not found
    MISSING TABLE ERROR localhost0:3306 shard_5.test1 not found
    MISSING TABLE ERROR localhost0:3306 shard_5.foo not found
    MISSING TABLE ERROR localhost1:3306 shard_6.test1 not found
    MISSING TABLE ERROR localhost1:3306 shard_6.foo not found
    MISSING TABLE ERROR localhost1:3306 shard_7.test1 not found
    MISSING TABLE ERROR localhost1:3306 shard_7.foo not found

## Options

      -h, --help            show this help message and exit
      -H HOST, --host HOST  Hostname to filter all shard hosts
      -p PORT, --port PORT  Port to filter all shard hosts
      --shards SHARDS [SHARDS ...]
                            space separate list of shards to audit





# mysql-sharded-schema-safe-drop

## Introduction
The original design for this was  based on an environment where multiple shards exist on a single mysql host and the operation to
scale out involves setting up a replica, diverting read/write traffic for some number of the shards to the replica, breaking
replication and dropping the shards that are no longer active on each host. This tool is designed to provide a safety wrapper
for dropping the inactive shards from databases that will not allow you to drop the active shards (as determined by the locator table).


### Safety Features
* When attempting to drop a shard it will verify that the host:port which you are trying to drop the shard from is not in the locator as the
active host for the shard
* Ensures that an active shard cannot be dropped inadvertently due to a scenario such as if there is more than one hostname that maps to the
same mysqldb in the locator table.
 * Example: There is one host, host_a", and in this host there is 2 shards, shard_1 and shard_2, there is also a second hostname, host_b, that
   routes to host_a. In the shard locator table there is an entry that maps shard_1 to host_a and shard_2 to host_b. With this configuration,
   conceivably shard_1 looks like an inactive shard on host_b and shard_2 looks like an inactive shard on host_a, but dropping would be bad in
   this case and is protected against
* This tool is not intended to provide functionality for dropping any schemas other than the shard schemas nor is it intended to be used
  to drop databases on hosts that are not in the locator table. Thus it will not allow you to do any operations on hosts that are not in
  your active configuration. (why would you need to do all these safety checks if the host is completely inactive?)

Functions exposed:
* List all the hosts in the locator table that are hosting active shards
* List the active, inactive or all shards on a host
* Perform complete run of shard drops without executing the SQL statements to drop tables/schemas and print out statements that will be run
* Perform complete run of shard drops


## Configuration
No extra configuration is needed for this tool beyond the standard configuration for the mysql-sharded-schema-change tool.

## Operations

### List hosts
Lists all of the hosts that are in the locator table with active shards.

    mysql-sharded-schema-safe-drop --list hosts

### List Shards
Active shards (shards on the host that are actively routed to by locator table)

    mysql-sharded-schema-safe-drop --host HOSTNAME --port PORT --list

Inactive shards (shards on the host that are not actively routed to by locator table)

    mysql-sharded-schema-safe-drop --host HOSTNAME --port PORT --list

All shards

    mysql-sharded-schema-safe-drop --host HOSTNAME --port PORT --list

### Drop Shards
Test run

    mysql-sharded-schema-safe-drop --host HOSTNAME --port PORT --drop --shards shard_1 shard_2 shard_3

Execution run (adding the --execute flag causes the drops to be executed)

    mysql-sharded-schema-safe-drop --host HOSTNAME --port PORT --drop --execute --shards shard_1 shard_2 shard_3


## Options

      -h, --help            show this help message and exit
      -H HOST, --host HOST  Hostname to drop shards on
      -p PORT, --port PORT  Port for the host to drop shards
      --shards SHARD [SHARD ...]
                            Space separated list of one or more shards to drop
      -l {active,inactive,all,hosts}, --list {active,inactive,all,hosts}
                            List shards on a host
      --drop                Drop the listed shards
      --execute             This is required to actually execute the drops;
                            otherwise, you will get SQL output for the table
                            drops, but they will not be executed
