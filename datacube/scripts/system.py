from __future__ import absolute_import

import logging

import click
from click import echo, style
from sqlalchemy.exc import OperationalError

import datacube
from datacube.drivers.manager import DriverManager
from datacube.index.postgres._connections import IndexSetupError
from datacube.ui import click as ui
from datacube.ui.click import cli, handle_exception

_LOG = logging.getLogger('datacube-system')


@cli.group(name='system', help='System commands')
def system():
    pass


@system.command('init', help='Initialise the database')
@click.option(
    '--default-types/--no-default-types', is_flag=True, default=True,
    help="Add default types? (default: true)"
)
@click.option(
    '--init-users/--no-init-users', is_flag=True, default=True,
    help="Include user roles and grants. (default: true)"
)
@click.option(
    '--recreate-views/--no-recreate-views', is_flag=True, default=True,
    help="Recreate dynamic views"
)
@click.option(
    '--rebuild/--no-rebuild', is_flag=True, default=False,
    help="Rebuild all dynamic fields (caution: slow)"
)
@click.option(
    '--lock-table/--no-lock-table', is_flag=True, default=False,
    help="Allow table to be locked (eg. while creating missing indexes)"
)
@click.option(
    '--create-s3-tables', '-s3', is_flag=True, default=False,
    help="Create S3 datables."
)
@ui.pass_index(expect_initialised=False)
def database_init(index, default_types, init_users, recreate_views, rebuild, lock_table, create_s3_tables):
    echo('Initialising database...')

    was_created = index.init_db(with_default_types=default_types,
                                with_permissions=init_users,
                                with_s3_tables=create_s3_tables)

    if was_created:
        echo(style('Created.', bold=True))
    else:
        echo(style('Updated.', bold=True))

    echo('Checking indexes/views.')
    index.metadata_types.check_field_indexes(
        allow_table_lock=lock_table,
        rebuild_indexes=rebuild,
        rebuild_views=recreate_views or rebuild,
    )
    echo('Done.')


@system.command('check', help='Check and display current configuration')
@ui.pass_config
def check(config_file):
    """
    Verify & view current configuration
    """
    echo('Version:\t' + style(str(datacube.__version__), bold=True))
    echo('Config files:\t' + style(','.join(config_file.files_loaded), bold=True))
    echo('Host:\t\t' +
         style('{}:{}'.format(config_file.db_hostname or 'localhost',
                              config_file.db_port or '5432'), bold=True))
    echo('Database:\t' + style('{}'.format(config_file.db_database), bold=True))
    echo('User:\t\t' + style('{}'.format(config_file.db_username), bold=True))

    echo()
    echo('Valid connection:\t', nl=False)
    try:
        # Initialise driver manager singleton
        index = DriverManager(default_driver_name=None, index=None, local_config=config_file).index
        echo(style('YES', bold=True))
        for role, user, description in index.users.list_users():
            if user == config_file.db_username:
                echo('You have %s privileges.' % style(role.upper(), bold=True))
    except OperationalError as e:
        handle_exception('Error Connecting to Database: %s', e)
    except IndexSetupError as e:
        handle_exception('Database not initialised: %s', e)
