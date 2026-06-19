from typing import Any


def mascarar_email(email: str) -> str:
    local, separador, dominio = email.partition("@")
    if not separador:
        return "<e-mail omitido>"
    prefixo = local[:2] if len(local) > 2 else local[:1]
    return f"{prefixo}***@{dominio}"


def mascarar_parametros(tipo: str, parametros: dict[str, Any]) -> dict[str, Any]:
    seguros = parametros.copy()

    imagem_base64 = seguros.get("imagem_base64")
    if isinstance(imagem_base64, str):
        seguros["imagem_base64"] = f"<base64 omitido: {len(imagem_base64)} caracteres>"

    if tipo == "enviar_email":
        destinatario = seguros.get("destinatario")
        if isinstance(destinatario, str):
            seguros["destinatario"] = mascarar_email(destinatario)
        corpo = seguros.get("corpo")
        if isinstance(corpo, str):
            seguros["corpo"] = f"<conteúdo omitido: {len(corpo)} caracteres>"

    return seguros


def mascarar_resultado(tipo: str, resultado: Any) -> Any:
    if tipo != "enviar_email" or not isinstance(resultado, dict):
        return resultado

    seguro = resultado.copy()
    destinatario = seguro.get("destinatario")
    if isinstance(destinatario, str):
        seguro["destinatario"] = mascarar_email(destinatario)
    seguro.pop("corpo", None)
    return seguro
