
def get_provider_info():
    return {
        "package-name": "airflow-sftp-extensions-provider",
        "name": "sftp_extensions",
        "description": "SFTP server extension operators",
        "operators": ["airflow_sftp_extensions_provider.StatvfsOperator"],
        "hooks": ["airflow_sftp_extensions_provider.SFTPHookWExtension.SFTPHookWExtension"]
        # todo: add integrations?
    }
