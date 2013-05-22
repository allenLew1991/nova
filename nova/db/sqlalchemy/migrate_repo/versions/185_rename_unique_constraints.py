# Copyright 2013 Mirantis Inc.
# All Rights Reserved
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
# @author: Victor Sergeyev, Mirantis Inc.
#
# vim: tabstop=4 shiftwidth=4 softtabstop=4

from migrate.changeset import UniqueConstraint
from migrate import ForeignKeyConstraint
from sqlalchemy import MetaData, Table

from nova.db.sqlalchemy import utils

UC_DATA = {
    # (table_name: ((columns,), old_uc_name_1), (columns,), old_uc_name_2)
    "floating_ips": (
        (("address", "deleted",), "uniq_address_x_deleted"),
    ),
    "instance_type_projects": (
        (("instance_type_id", "project_id", "deleted"),
         "uniq_instance_type_id_x_project_id_x_deleted"),
    ),
    "instance_types": (
        (("name", "deleted"), "uniq_name_x_deleted"),
        (("flavorid", "deleted",), "uniq_flavorid_x_deleted"),
    ),
    "key_pairs": (
        (("user_id", "name", "deleted"), "key_pairs_uniq_name_and_user_id"),
    ),
    "networks": (
        (("vlan", "deleted",), "uniq_vlan_x_deleted"),
    ),
    "task_log": (
        (("task_name", "host", "period_beginning", "period_ending"),
         "uniq_task_name_x_host_x_period_beginning_x_period_ending"),
    ),
}
# some UC names are different for mysql and postgresql
UC_SPEC_DB_DATA = {
    # {engine: {table_name: (((columns,), old_uc_name), (...))}}
    "sqlite": {
        "instance_info_caches": (
            (("instance_uuid",), "instance_uuid"),
        ),
        "virtual_interfaces": (
            (("address",), "virtual_interfaces_instance_uuid_fkey"),
        ),
    },
    "mysql": {
        "instance_info_caches": (
            (("instance_uuid",), "instance_uuid"),
        ),
        "virtual_interfaces": (
            (("address",), "virtual_interfaces_instance_uuid_fkey"),
        ),
    },
    "postgresql": {
        "instance_info_caches": (
            (("instance_uuid",), "instance_info_caches_instance_uuid_key"),
        ),
        "virtual_interfaces": (
            (("address",), "virtual_interfaces_address_key"),
        ),
    },
}


constraint_names = {
    "instance_info_caches": "instance_info_caches_instance_uuid_fkey",
    "virtual_interfaces": "virtual_interfaces_instance_uuid_fkey",
}


def _uc_rename(migrate_engine, upgrade=True):
    UC_DATA.update(UC_SPEC_DB_DATA[migrate_engine.name])

    meta = MetaData(bind=migrate_engine)

    for table in UC_DATA:
        t = Table(table, meta, autoload=True)

        for columns, old_uc_name in UC_DATA[table]:
            new_uc_name = "uniq_{0}0{1}".format(table, "0".join(columns))

            if table in constraint_names and migrate_engine.name == "mysql":
                instances = Table("instances", meta, autoload=True)

                ForeignKeyConstraint(
                    columns=[t.c.instance_uuid],
                    refcolumns=[instances.c.uuid],
                    name=constraint_names[table]
                ).drop(engine=migrate_engine)

            if upgrade:
                old_name, new_name = old_uc_name, new_uc_name
            else:
                old_name, new_name = new_uc_name, old_uc_name

            utils.drop_unique_constraint(migrate_engine, table,
                                         old_name, *(columns))
            UniqueConstraint(*columns, table=t, name=new_name).create()

            if table in constraint_names and migrate_engine.name == "mysql":
                ForeignKeyConstraint(
                    columns=[t.c.instance_uuid],
                    refcolumns=[instances.c.uuid],
                    name=constraint_names[table]
                ).create(engine=migrate_engine)


def upgrade(migrate_engine):
    return _uc_rename(migrate_engine, upgrade=True)


def downgrade(migrate_engine):
    return _uc_rename(migrate_engine, upgrade=False)
