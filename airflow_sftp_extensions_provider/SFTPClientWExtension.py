from paramiko import SFTPClient
from paramiko.sftp import CMD_EXTENDED, CMD_EXTENDED_REPLY, SFTPError
from paramiko.sftp import Message, _VERSION, CMD_INIT, CMD_VERSION, SFTPError
from paramiko.common import DEBUG

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

# statvfs
CMD_EXT_STATVFS = "statvfs@openssh.com"  # the command
EXT_PROV_STATVFS = "statvfs@openssh.com"  # provided by extension


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
        Returns True when extension is present (and advertised)
        
        :param ext_name: name of the extension
        :type ext_name: str
        :return: extension is present
        :rtype: bool
        """
        return any(name == ext_name for name, _ in self.server_extensions)

    def statvfs(self, path: str) -> dict[str, int]:
        if not self.has_server_extension(EXT_PROV_STATVFS):
            raise SFTPError(f"extension {EXT_PROV_STATVFS} not present")
        self._log(DEBUG, "statvfs({!r})".format(path))

        status, msg = self._request(CMD_EXTENDED, CMD_EXT_STATVFS, path)
        if status != CMD_EXTENDED_REPLY:
            raise SFTPError(f"remote server unexpectedly returned status: {status}")

        # read 11 uint 64, that's 88 byte
        stats_dict = {stats_field: msg.get_int64() for stats_field in STATVFS_FIELDS}
        if msg.get_remainder():
            raise SFTPError("Unexpected remainder in response message")
        return stats_dict
