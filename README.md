# Airflow SFTP extensions provider

Provides Airflow Operators to use commands provided by SFTP server extensions.

## Example

Provides the `StatvfsOperator` to check the disk space available on the remote server.

For details, see https://libssh2.org/libssh2_sftp_statvfs.html

```python
from airflow.sdk import DAG
from airflow_sftp_statvfs_operator import StatvfsOperator

with DAG(
    dag_id="disk_stats",
    schedule="5 * * * *",
    start_date=datetime.datetime(2016, 1, 1),
    catchup=False,
    doc_md="""
Collect disk usage statistics similar to `df`
""",
):
    StatvfsOperator(ssh_conn_id="sftp-service", remote_filepath="/", task_id="sshfs_disk_usage")
```

Returns:
```json
{
    "flag": 0,
    "fsid": 1132944995873264800,
    "bfree": 1250443143,
    "bsize": 4096,
    "ffree": 0,
    "files": 0,
    "bavail": 1250443143,
    "blocks": 16399309210,
    "favail": 0,
    "frsize": 4096,
    "namemax": 255
}
```

## About SFTP protocol extensions

Extensions provided by the SFTP subsystem of openssh 9.6 (as found on Ubuntu 24.04):

```json
[
 ["posix-rename@openssh.com", "1"],
 ["statvfs@openssh.com", "2"],
 ["fstatvfs@openssh.com", "2"],
 ["hardlink@openssh.com", "1"],
 ["fsync@openssh.com", "1"],
 ["lsetstat@openssh.com",  "1"],
 ["limits@openssh.com", "1"],
 ["expand-path@openssh.com", "1"],
 ["copy-data", "1"],
 ["home-directory", "1"],
 ["users-groups-by-id@openssh.com", "1"]
]
```

Protocol details are explained in section 4 of https://github.com/openssh/openssh-portable/blob/master/PROTOCOL

At the moment only querying the supported extensions and `statvfs` are implemented in this repository.

## Implementation:

* The `SFTPClientWExtension` is subclassed from paramiko's `SFTPClient`,
  implementing the low level SFTP protocol functionality.
* The airflow `SFTPHookWExtension` makes use of the `SFTPClientWExtension` class.
* The operator/s are provided in `SFTPExtensionOperators` module.
