from paramiko import SFTPClient
from paramiko.common import DEBUG
from paramiko.sftp import (
    _VERSION,
    CMD_EXTENDED,
    CMD_EXTENDED_REPLY,
    CMD_INIT,
    CMD_NAME,
    CMD_VERSION,
    Message,
    SFTPError,
)

STATVFS_FIELDS = [
    "bsize",
    "frsize",
    "blocks",
    "bfree",
    "bavail",
    "files",
    "ffree",
    "favail",
    "fsid",
    "flag",
    "namemax",
]

# extensions implemented...
CMD_EXT_STATVFS = "statvfs@openssh.com"  # the command
EXT_PROV_STATVFS = "statvfs@openssh.com"  # provided by extension

EXT_PROV_HOMEDIRECTORY = "home-directory"
CMD_EXT_HOMEDIRECTORY = "home-directory"

EXT_PROV_USERSGROUPSBYID = "users-groups-by-id@openssh.com"
CMD_EXT_USERSGROUPSBYID = "users-groups-by-id@openssh.com"

EXT_PROV_LIMITS = "limits@openssh.com"
CMD_EXT_LIMITS = "limits@openssh.com"

EXT_PROV_EXPANDPATH = "expand-path@openssh.com"
CMD_EXT_EXPANDPATH = "expand-path@openssh.com"


class SFTPClientWExtension(SFTPClient):
    """
    This version of the SFTPClient stores the extensions in `server_extensions` and
    provides some known extension implementations.
    """

    def _send_version(self):
        m = Message()
        m.add_int(_VERSION)
        self._send_packet(CMD_INIT, m)
        t, data = self._read_packet()
        if t != CMD_VERSION:
            raise SFTPError("Incompatible sftp protocol")
        # adopted from https://github.com/paramiko/paramiko/pull/1849
        m = Message(data)
        version, extensions = m.get_int(), []
        #        if version != _VERSION:
        #            raise SFTPError('Incompatible sftp protocol')
        while m.packet.tell() < len(data):
            ext_name = m.get_text()
            ext_data = m.get_text()
            extensions.append((ext_name, ext_data))
        self.server_version = version
        self._log(DEBUG, "server extensions %s", str(extensions))
        self.server_extensions = extensions
        return version

    def extension_supported(self, ext_name: str, ext_data: str) -> bool:
        """
        Returns True if extension `ext_name` with version `ext_data` is supported
        (matches the libssh function).

        :param ext_name: extension name
        :type ext_name: str
        :param ext_data: extension version
        :type ext_data: str
        :return: True if supported, otherwise False
        :rtype: bool
        """
        return (ext_name, ext_data) in self.server_extensions

    def extension_versions(self, ext_name: str) -> list[str]:
        """
        Returns the versions (if any) of the extension named.

        :param ext_name: name of the extension
        :type ext_name: str
        :return: version number/s (there could be multiple)
        :rtype: list[str]
        """
        return [data for name, data in self.server_extensions if name == ext_name]

    def has_server_extension(self, ext_name: str) -> bool:
        """
        Returns True when extension is present (and advertised).
        Does not chex the extension version.

        :param ext_name: name of the extension
        :type ext_name: str
        :return: extension is present
        :rtype: bool
        """
        return any(name == ext_name for name, _ in self.server_extensions)

    def statvfs(self, path: str) -> dict[str, int]:
        if not self.has_server_extension(EXT_PROV_STATVFS):
            raise SFTPError(f"extension {EXT_PROV_STATVFS} not supported")
        self._log(DEBUG, "statvfs({!r})".format(path))

        status, msg = self._request(CMD_EXTENDED, CMD_EXT_STATVFS, path)
        if status != CMD_EXTENDED_REPLY:
            raise SFTPError(f"remote server unexpectedly returned status: {status}")

        # read 11 uint 64, that's 88 byte
        stats_dict = {stats_field: msg.get_int64() for stats_field in STATVFS_FIELDS}
        return stats_dict

    def homedirectory(self, username: str = None) -> str:
        # get home directory
        # openssh9.6 always returns the current users homedirectory
        # "" should result in current user's home dir, but doesn't seem to work on OpenSSH?
        if not self.has_server_extension(EXT_PROV_HOMEDIRECTORY):
            raise SFTPError(f"extension {EXT_PROV_HOMEDIRECTORY} not supported")
        self._log(DEBUG, "homedirectory({!r})".format(username))

        if username is None:
            username = ""

        status, msg = self._request(CMD_EXTENDED, CMD_EXT_HOMEDIRECTORY, username)

        if status not in [CMD_NAME, CMD_EXTENDED_REPLY]:
            raise SFTPError(f"remote server unexpectedly returned status: {status}")

        count = msg.get_int()
        if count == 0:
            return None
        if count != 1:
            raise SFTPError("Homedirectory returned {} results".format(count))

        homedirectory = msg.get_text()
        # openssh does return more but redundant information, so ignore
        # remainder = msg.get_remainder()
        # if remainder:
        #     longname = msg.get_text()
        #     from paramiko.sftp_attr import SFTPAttributes
        #     SFTPAttributes._from_msg(msg, homedirectory, longname)
        #     if msg.get_remainder():
        #         raise SFTPError(f"Unexpected remainder in response message `{remainder}`")
        return homedirectory

    def users_groups_by_id(self, uids=None, gids=None) -> tuple[list[str], list[str]]:

        if not self.has_server_extension(EXT_PROV_USERSGROUPSBYID):
            raise SFTPError(f"extension {EXT_PROV_USERSGROUPSBYID} not supported")
        self._log(DEBUG, "users-groups-by-id({!r}, {!r})".format(uids, gids))

        if uids is None:
            uids = ()
        if gids is None:
            gids = ()

        status, msg = self._request(
            CMD_EXTENDED,
            CMD_EXT_USERSGROUPSBYID,
            len(uids) * 4,
            *map(int, uids),
            len(gids) * 4,
            *map(int, gids),
        )
        if status != CMD_EXTENDED_REPLY:
            raise SFTPError(f"remote server unexpectedly returned status: {status}")

        # unpack the nested text messages

        usernames_msg = Message(msg.get_string())
        usernames = [usernames_msg.get_text() for _ in uids]

        groupnames_msg = Message(msg.get_string())
        groupnames = [groupnames_msg.get_text() for _ in gids]

        return usernames, groupnames

    def expandpath(self, path: str, adjust_cw=None) -> str:
        """
        Expands path like normalize, but also resolves the `~` (home dir) expansion.

        By default the path is prefixed by the remote `cwd` as emulated by
        paramiko except it starts with ~ or is absolute (or `cwd` is not set via `chdir`).

        :param path: Description
        :type path: str
        :param adjust_cw: if set to True/False, forces the adjustment with the `cwd`.
        :return: Description
        :rtype: str
        """
        if not self.has_server_extension(EXT_PROV_EXPANDPATH):
            raise SFTPError(f"extension {EXT_PROV_EXPANDPATH} not supported")

        if adjust_cw or (adjust_cw is None and path[0] != "~"):
            path = self._adjust_cwd(path)

        self._log(DEBUG, "expandpath({!r})".format(path))

        status, msg = self._request(CMD_EXTENDED, CMD_EXT_EXPANDPATH, path)

        if status not in [CMD_NAME, CMD_EXTENDED_REPLY]:
            raise SFTPError(f"remote server unexpectedly returned status: {status}")

        count = msg.get_int()
        if count == 0:
            return None
        if count != 1:
            raise SFTPError("Expandpath returned {} results".format(count))

        expandedpath = msg.get_text()
        # openssh does return more but redundant information, so ignore
        # remainder = msg.get_remainder()
        # if remainder:
        #     longname = msg.get_text()
        #     from paramiko.sftp_attr import SFTPAttributes
        #     SFTPAttributes._from_msg(msg, expandedpath, longname)
        #     if msg.get_remainder():
        #         raise SFTPError(f"Unexpected remainder in response message `{remainder}`")
        return expandedpath

    def limits(self) -> dict[str, int]:
        if not self.has_server_extension(EXT_PROV_LIMITS):
            raise SFTPError(f"extension {EXT_PROV_LIMITS} not supported")
        self._log(DEBUG, "limits()")

        status, msg = self._request(CMD_EXTENDED, CMD_EXT_LIMITS)

        if status != CMD_EXTENDED_REPLY:
            raise SFTPError(f"remote server unexpectedly returned status: {status}")

        return {
            k: msg.get_int64()
            for k in [
                "max-packet-length",
                "max-read-length",
                "max-write-length",
                "max-open-handles",
            ]
        }
