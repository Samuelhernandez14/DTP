import sys
from email.message import EmailMessage

from citologia.config import get_settings
from citologia.db.afiliados import MySQLAfiliadoRepository
from citologia.notifications.sender import SmtpSender


def main() -> None:
    s = get_settings()
    modo = sys.argv[1] if len(sys.argv) > 1 else ""
    if modo == "db" and len(sys.argv) == 4:
        filas = MySQLAfiliadoRepository(s.db).buscar(sys.argv[2].upper(), sys.argv[3])
        print(f"Conexión OK. Filas encontradas: {len(filas)}")
    elif modo == "smtp" and len(sys.argv) == 3:
        msg = EmailMessage()
        msg["Subject"] = f"{s.email_asunto_prefijo} Prueba de SMTP"
        msg["From"], msg["To"] = s.email_from, sys.argv[2]
        msg.set_content("Prueba sin datos de pacientes.")
        SmtpSender(s.smtp_host, s.smtp_port, s.smtp_user,
                   s.smtp_password.get_secret_value()).enviar(msg)
        print("Correo de prueba enviado.")
    else:
        print("Uso:\n  python scripts/probar_conexiones.py db <TIPO> <NUMERO>\n"
              "  python scripts/probar_conexiones.py smtp <tu_correo>")


if __name__ == "__main__":
    main()