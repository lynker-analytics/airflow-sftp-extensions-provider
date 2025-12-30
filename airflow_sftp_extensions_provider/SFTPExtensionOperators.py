from typing import Sequence

from airflow.providers.common.compat.sdk import AirflowException, BaseOperator

from .SFTPHookWExtension import SFTPHookWExtension


class StatvfsOperator(BaseOperator):
    """
    Use OpenSSH's statvfs extension to retrieve disk space information from
    the remote server.

    For details, see https://libssh2.org/libssh2_sftp_statvfs.html

    This operator uses `sftp_hook` to open sftp transport channel.

    :param ssh_conn_id: :ref:`ssh connection id<howto/connection:ssh>`
        from airflow Connections.
    :param sftp_hook: predefined SFTPHookWExtension to use
        Either `sftp_hook` or `ssh_conn_id` needs to be provided.
    :param remote_host: remote host to connect (templated)
        Nullable. If provided, it will replace the `remote_host` which was
        defined in `sftp_hook` or predefined in the connection of `ssh_conn_id`.
    :param remote_filepath: remote file path (templated)
    """

    template_fields: Sequence[str] = ("remote_filepath", "remote_host")

    def __init__(
        self,
        *,
        sftp_hook: SFTPHookWExtension | None = None,
        ssh_conn_id: str | None = None,
        remote_host: str | None = None,
        remote_filepath: str,
        **kwargs,
    ) -> None:

        # though not inheriting from SFTPOperator, using their argument names
        super().__init__(**kwargs)
        self.sftp_hook = sftp_hook
        self.ssh_conn_id = ssh_conn_id
        self.remote_host = remote_host
        # todo: check for string (list not - yet - supported)
        self.remote_filepath = remote_filepath

    def execute(self, context) -> dict[str, int]:

        # though not inheriting from SFTPOperator, using their connection handling
        try:
            if self.remote_host is not None:
                self.log.info(
                    "remote_host is provided explicitly. "
                    "It will replace the remote_host which was defined "
                    "in sftp_hook or predefined in connection of ssh_conn_id."
                )

            if self.ssh_conn_id:
                # todo: when SFTPHook was provided: can I upgrade this to hook with extension?
                if self.sftp_hook and isinstance(self.sftp_hook, SFTPHookWExtension):
                    self.log.info("ssh_conn_id is ignored when sftp_hook is provided.")
                else:
                    self.log.info(
                        "sftp_hook not provided or invalid. Trying ssh_conn_id to create SFTPHookWExtension."
                    )
                    self.sftp_hook = SFTPHookWExtension(
                        ssh_conn_id=self.ssh_conn_id, remote_host=self.remote_host or ""
                    )

            if not self.sftp_hook:
                raise AirflowException(
                    "Cannot operate without sftp_hook or ssh_conn_id."
                )

            with self.sftp_hook.get_managed_conn() as conn:
                self.log.info("retrieving statvfs for %s", self.remote_filepath)
                return self.sftp_hook.statvfs(self.remote_filepath)

        except Exception as e:
            raise AirflowException("statvfs failed") from e
