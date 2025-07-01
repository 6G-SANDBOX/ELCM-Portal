import yaml
import logging
from typing import Dict, List, Optional, Tuple, Union
from shutil import copy
from os.path import exists, abspath


class hostPort:
    def __init__(self, data: Dict, key: str):
        self.data = data.get(key, {})

    @property
    def Host(self):
        return self.data['Host']

    @property
    def Port(self):
        return self.data['Port']

    @property
    def Url(self):
        return f"{self.Host}:{self.Port}/"


class possiblyEnabled:
    def __init__(self, data: Dict, key: str):
        self.data = data[key]

    @property
    def Enabled(self) -> bool:
        return self.data.get("Enabled", False)


class ELCM(hostPort):
    def __init__(self, data: Dict):
        super().__init__(data, 'ELCM')


class Logging:
    def __init__(self, data: Dict):
        self.data = data['Logging']

    @staticmethod
    def toLogLevel(level: str) -> int:
        if level.lower() == 'critical': return logging.CRITICAL
        if level.lower() == 'error': return logging.ERROR
        if level.lower() == 'warning': return logging.WARNING
        if level.lower() == 'info': return logging.INFO
        return logging.DEBUG

    @property
    def Folder(self):
        return abspath(self.data['Folder'])

    @property
    def AppLevel(self):
        return self.toLogLevel(self.data['AppLevel'])

    @property
    def LogLevel(self):
        return self.toLogLevel(self.data['LogLevel'])


class Branding:
    def __init__(self, data: Dict):
        self.data = data['Branding']

    @property
    def Platform(self):
        return self.data.get('Platform', 'Untitled')

    @property
    def Description(self):
        return self.data.get('Description', 'Untitled ELCM Portal')

    @property
    def DescriptionPage(self):
        return self.data.get('DescriptionPage', 'platform.html')

    @property
    def FavIcon(self):
        return self.data.get('FavIcon', 'logo.png')

    @property
    def Header(self):
        return self.data.get('Header', 'header.png')

    @property
    def Logo(self):
        return self.data.get('Logo', 'logo.png')


class EastWest(possiblyEnabled):
    def __init__(self, data: Dict):
        super().__init__(data, 'EastWest')

    @property
    def Remotes(self) -> Dict[str, Dict[str, Union[int, str]]]:
        return self.data.get('Remotes', {})

    @property
    def RemoteNames(self) -> List[str]:
        return list(self.Remotes.keys())

    def RemoteData(self, name: str) -> Tuple[Optional[str], Optional[int]]:
        try:
            remote = self.Remotes[name]
            return remote['Host'], remote['Port']
        except Exception:
            return None, None

    def RemoteApi(self, name: str):
        host, port = self.RemoteData(name)
        if host is not None and port is not None:
            from REST import RemoteApi
            return RemoteApi(host, port)
        return None


class Analytics(possiblyEnabled):
    def __init__(self, data: Dict):
        super().__init__(data, 'Analytics')

    @property
    def Url(self) -> Optional[str]:
        return self.data.get("URL", None)

    @property
    def Secret(self) -> Optional[str]:
        return self.data.get("Secret", None)
    
class EmailApi:
    def __init__(self, data: Dict):
        self.data = data.get('EmailApi', {
            'User': 'user',
            'Password': 'password',
            'Port': 587,
            'Server': 'server',
            'TLS': True,
            'SSL': False
        })

    @property
    def User(self):
        return self.data.get('User', '')

    @property
    def Password(self):
        return self.data.get('Password', '')

    @property
    def Port(self):
        return self.data.get('Port', 587)

    @property
    def Server(self):
        return self.data.get('Server', '')
    @property
    def TLS(self):
        return self.data.get('TLS', True)
    @property
    def SSL(self):
        return self.data.get('SSL', False)

class MinIOConfig:
    def __init__(self, data: Dict):
        self.data = data.get('MinIO', {
            'Host': 'localhost',
            'Port': 9000,
            'AccessKey': 'admin',
            'SecretKey': 'password123',
            'Secure': False,
            'Bucket': 'executions'
        })

    @property
    def Host(self):
        return self.data.get('Host', 'localhost')

    @property
    def Port(self):
        return self.data.get('Port', 9000)

    @property
    def AccessKey(self):
        return self.data.get('AccessKey', 'admin')

    @property
    def SecretKey(self):
        return self.data.get('SecretKey', 'password123')

    @property
    def Secure(self) -> bool:
        return self.data.get('Secure', False)

    @property
    def Bucket(self):
        return self.data.get('Bucket', 'executions')

    @property
    def Endpoint(self):
        return f"{self.Host}:{self.Port}"


class Config:
    FILENAME = 'config.yml'
    FILENAME_NOTICES = 'notices.yml'
    data = None

    def __init__(self):
        if self.data is None:
            self.Reload()

    def Reload(self):
        if not exists(self.FILENAME):
            copy('Helper/defaultConfig', self.FILENAME)

        with open(self.FILENAME, 'r', encoding='utf-8') as file:
            self.data = yaml.safe_load(file)

            description = "No 'PlatformDescriptionPage' value set on config.yml"
            htmlFile = self.data.get("PlatformDescriptionPage", None)
            if htmlFile is not None:
                try:
                    with open(abspath(htmlFile), 'r', encoding="utf8") as stream:
                         description = stream.read()
                except Exception as e:
                    description = f"Exception while reading description html from {htmlFile}: {e}"
            self.data["PlatformDescriptionHtml"] = description

    @property
    def Notices(self) -> List[str]:
        if not exists(self.FILENAME_NOTICES):
            return []

        with open(self.FILENAME_NOTICES, 'r', encoding='utf-8') as file:
            notices = yaml.safe_load(file)
            return notices['Notices']

    @property
    def ELCM(self) -> ELCM:
        return ELCM(self.data)

    @property
    def Branding(self) -> Branding:
        return Branding(self.data)

    @property
    def GrafanaUrl(self):
        return self.data['Grafana URL']

    @property
    def Logging(self) -> Logging:
        return Logging(self.data)

    @property
    def EastWest(self) -> EastWest:
        return EastWest(self.data)

    @property
    def Analytics(self) -> Analytics:
        return Analytics(self.data)
    
    @property
    def EmailApi(self) -> EmailApi:
        return EmailApi(self.data)
    
    @property
    def MinIO(self) -> MinIOConfig:
        return MinIOConfig(self.data)