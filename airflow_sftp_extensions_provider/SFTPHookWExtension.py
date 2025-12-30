from contextlib import contextmanager
from typing import Generator

from airflow.providers.sftp.hooks.sftp import SFTPHook, handle_connection_management
from paramiko import SSHClient

from .SFTPClientWExtension import SFTPClientWExtension


class SFTPHookWExtension(SFTPHook):

    hook_name = "SFTPWExtension"

    def get_conn(self) -> SFTPClientWExtension:  # type: ignore[override]
        """Open an SFTP connection to the remote host."""
        if self.conn is None:
            self.conn = SFTPClientWExtension(super(SFTPHook, self).get_conn().get_transport())
        return self.conn

    @contextmanager
    def get_managed_conn(self) -> Generator[SFTPClientWExtension, None, None]:
        """Context manager that closes the connection after use."""
        if self._sftp_conn is None:
            ssh_conn: SSHClient = super(SFTPHook, self).get_conn()
            self._ssh_conn = ssh_conn
            self._sftp_conn = SFTPClientWExtension.from_transport(
                ssh_conn.get_transport()
            )
        self._conn_count += 1

        try:
            yield self._sftp_conn
        finally:
            self._conn_count -= 1
            if (
                self._conn_count == 0
                and self._ssh_conn is not None
                and self._sftp_conn is not None
            ):
                self._sftp_conn.close()
                self._sftp_conn = None
                self._ssh_conn.close()
                self._ssh_conn = None
                if hasattr(self, "host_proxy"):
                    del self.host_proxy

    @handle_connection_management
    def get_extensions(self) -> list[tuple[str, str]]:
        """
        Get the extensions advertised by the SFTP server.
        
        :return: tuples of extension name and version
        :rtype: list[tuple[str, str]
        """
        return self.conn.server_extensions

    @handle_connection_management
    def statvfs(self, path: str) -> dict[str, int]:
        return self.conn.statvfs(path)
