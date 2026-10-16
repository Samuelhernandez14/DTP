from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from citologia.domain.errors import ConfigurationError


@dataclass(frozen=True)
class ConexionBD:
    host: str
    port: int
    name: str
    user: str
    password: str


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # MySQL de Conexiones: SOLO LECTURA sobre aseg_afiliados
    database_host: str
    database_port: int = 3306
    database_name: str
    database_user: str
    database_password: SecretStr

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: SecretStr = SecretStr("")
    email_from: str = ""
    prestador_email_to: str = ""          # varios separados por coma
    email_asunto_prefijo: str = "[DTP]"
    email_dry_run: bool = True
    outbox_dir: Path = Path("data/outbox")

    # Estado local (anti-duplicados)
    estado_db_path: Path = Path("data/estado.db")
    notificacion_max_intentos: int = 3

    @property
    def db(self) -> ConexionBD:
        return ConexionBD(self.database_host, self.database_port, self.database_name,
                          self.database_user, self.database_password.get_secret_value())

    @property
    def destinatarios(self) -> list[str]:
        return [d.strip() for d in self.prestador_email_to.split(",") if d.strip()]


@lru_cache
def get_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as e:
        faltantes = ", ".join(str(err["loc"][0]).upper() for err in e.errors())
        raise ConfigurationError(f"Configuración inválida o incompleta: {faltantes}") from None