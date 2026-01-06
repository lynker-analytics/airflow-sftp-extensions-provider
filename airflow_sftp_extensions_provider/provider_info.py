def get_provider_info():
    return {
        "package-name": "airflow-sftp-extensions-provider",
        "name": "sftp_extensions",
        "description": "SFTP server extension operators",
        "operators": [
            {
                "python-modules": [
                    "airflow_sftp_extensions_provider.SFTPExtensionOperators"
                ]
            }
        ],
        "hooks": [
            {
                "python-modules": [
                    "airflow_sftp_extensions_provider.SFTPHookWExtension"
                ],
            }
        ],
        # todo: add integrations?
    }
