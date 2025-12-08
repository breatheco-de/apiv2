[
    {
        "description": "Este m\u00f3dulo se centra en la identificaci\u00f3n y mapeo de recursos de red para descubrir posibles puntos de entrada para la explotaci\u00f3n. Los estudiantes aprender\u00e1n a escanear redes utilizando herramientas como `nmap`, `netdiscover` y `arp-scan` para descubrir hosts activos y puertos abiertos, como 80 (HTTP), 22 (SSH), 21 (FTP) y 445 (SMB). Adem\u00e1s, enumerar\u00e1n servicios para detectar servidores web, endpoints SSH, servidores FTP y recursos compartidos SMB, utilizando `smbclient` para listar recursos accesibles como carpetas compartidas. Este conjunto de habilidades fundamentales, aplicado en M\u00e1quina 1, M\u00e1quina 2, M\u00e1quina 3, M\u00e1quina 4 y M\u00e1quina 5, permite a los estudiantes recopilar informaci\u00f3n cr\u00edtica sobre los sistemas objetivo, sentando las bases para una explotaci\u00f3n m\u00e1s profunda en m\u00f3dulos posteriores.",
        "icon_url": null,
        "name": "Reconocimiento y Enumeraci\u00f3n de Redes",
        "slug": "network-reconnaissance-and-enumeration"
    },
    {
        "description": "En este m\u00f3dulo, los estudiantes explotar\u00e1n vulnerabilidades en aplicaciones web para obtener acceso no autorizado a datos o sistemas sensibles. Identificar\u00e1n y eludir\u00e1n la autenticaci\u00f3n utilizando inyecci\u00f3n SQL en formularios de inicio de sesi\u00f3n con herramientas como `sqlmap`, manipular\u00e1n par\u00e1metros URL para explotar vulnerabilidades de inclusi\u00f3n de archivos locales (LFI) y descubrir\u00e1n rutas web ocultas utilizando herramientas de fuerza bruta como `gobuster`, `dirb` y `ffuf`. Adem\u00e1s, analizar\u00e1n el c\u00f3digo fuente HTML a trav\u00e9s de las herramientas de desarrollo del navegador para descubrir credenciales expuestas, aplicando estas t\u00e9cnicas en M\u00e1quina 2, M\u00e1quina 3, M\u00e1quina 5 y M\u00e1quina 6. Este m\u00f3dulo enfatiza la importancia de comprender las debilidades de las aplicaciones web para acceder a \u00e1reas restringidas o extraer informaci\u00f3n cr\u00edtica.",
        "icon_url": null,
        "name": "Explotaci\u00f3n de Aplicaciones Web",
        "slug": "web-application-exploitation"
    },
    {
        "description": "Este m\u00f3dulo se centra en comprometer credenciales a trav\u00e9s de ataques de fuerza bruta y descifrado de hashes para acceder a sistemas y servicios. Los estudiantes utilizar\u00e1n `hydra` con el diccionario `rockyou.txt` para realizar ataques de fuerza bruta en servicios FTP y SSH, dirigidos a contrase\u00f1as d\u00e9biles en M\u00e1quina 2, M\u00e1quina 4, M\u00e1quina 5, M\u00e1quina 7 y M\u00e1quina 8. Tambi\u00e9n descifrar\u00e1n hashes MD5 y NTLM utilizando herramientas como `john`, `hashcat` y `crackstation`, y extraer\u00e1n hashes de metadatos de im\u00e1genes con `exiftool`, permitiendo inicios de sesi\u00f3n simulados con credenciales recuperadas. Este m\u00f3dulo destaca los riesgos de las malas pr\u00e1cticas de contrase\u00f1as y equipa a los estudiantes con t\u00e9cnicas para explotarlas sistem\u00e1ticamente.",
        "icon_url": null,
        "name": "Ataques de Contrase\u00f1as",
        "slug": "password-attacks"
    },
    {
        "description": "El m\u00f3dulo de escalada de privilegios ense\u00f1a a los estudiantes c\u00f3mo elevar su acceso desde cuentas de usuario limitadas a privilegios de root o Administrador en sistemas comprometidos. En M\u00e1quina 4, M\u00e1quina 7, M\u00e1quina 8 y M\u00e1quina 9, los estudiantes aprovechar\u00e1n los permisos `sudo` para ejecutar comandos como root en sistemas Linux, explotar\u00e1n binarios SUID usando `find` y `ssh` para obtener shells de root, y escalar\u00e1n privilegios en sistemas Windows para lograr acceso de Administrador. Este m\u00f3dulo subraya el impacto de permisos y binarios mal configurados, permitiendo a los estudiantes navegar por los internos del sistema y acceder a recursos restringidos como banderas protegidas.",
        "icon_url": null,
        "name": "Escalada de Privilegios",
        "slug": "privilege-escalation"
    },
    {
        "description": "Este m\u00f3dulo explora la explotaci\u00f3n de servicios de red para obtener acceso a sistemas y datos sensibles. Los estudiantes se conectar\u00e1n a servidores FTP mal configurados con acceso an\u00f3nimo usando `ftp` para recuperar archivos, enumerar\u00e1n y acceder\u00e1n a recursos compartidos SMB con `smbclient` para extraer elementos como hashes NTLM, y realizar\u00e1n ataques pass-the-hash con `evil-winrm` para autenticarse como usuarios privilegiados en M\u00e1quina 1, M\u00e1quina 4 y M\u00e1quina 10. Tambi\u00e9n usar\u00e1n `ssh` para iniciar sesi\u00f3n en sistemas con credenciales descubiertas y `unzip` para extraer archivos comprimidos que contienen informaci\u00f3n sensible. Este m\u00f3dulo demuestra c\u00f3mo los servicios de red inseguros pueden servir como puntos de entrada para un compromiso m\u00e1s profundo del sistema.",
        "icon_url": null,
        "name": "Explotaci\u00f3n de Servicios de Red",
        "slug": "network-service-exploitation"
    },
    {
        "description": "En este m\u00f3dulo, los estudiantes combinar\u00e1n habilidades t\u00e9cnicas con deducci\u00f3n l\u00f3gica para extraer banderas y resolver desaf\u00edos narrativos. Analizar\u00e1n paneles de usuario y mensajes en interfaces web usando un navegador para deducir informaci\u00f3n cr\u00edtica, como identificar a un saboteador, y recuperar\u00e1n banderas de directorios restringidos o paneles de control web en M\u00e1quina 1, M\u00e1quina 3, M\u00e1quina 5 y M\u00e1quina 10. Adem\u00e1s, utilizar\u00e1n `exiftool` para extraer datos sensibles de metadatos de im\u00e1genes, `cat` para leer archivos Linux y `type` en PowerShell para acceder a archivos Windows. Este m\u00f3dulo enfatiza la importancia de combinar la explotaci\u00f3n t\u00e9cnica con el razonamiento anal\u00edtico para lograr los objetivos del desaf\u00edo.",
        "icon_url": null,
        "name": "An\u00e1lisis L\u00f3gico y Recuperaci\u00f3n de Banderas",
        "slug": "logical-analysis-and-flag-retrieval"
    }
]